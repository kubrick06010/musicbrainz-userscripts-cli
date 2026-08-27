#!/usr/bin/env python3
"""Generate a local HTML form that seeds the MusicBrainz Add Release editor.

This tool does not submit MusicBrainz edits. It resolves track artists conservatively
against MusicBrainz, then POSTs candidate fields into MusicBrainz's documented
release-editor seeding endpoint so the user can review and submit from the normal UI.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

CANDIDATE_SCHEMA = "nts-guide-candidate/v1"
SEED_ACTION = "https://musicbrainz.org/release/add"
MB_WS = "https://musicbrainz.org/ws/2"
UA = "musicbrainz-userscripts-cli/nts-guide-seed (https://github.com/kubrick06010/musicbrainz-userscripts-cli)"
TRANSIENT_HTTP = {429, 500, 502, 503, 504}


def _progress(enabled: bool, message: str) -> None:
    if enabled:
        print(message, file=sys.stderr, flush=True)


def _field(name: str, value: Any) -> tuple[str, str] | None:
    if value is None or value == "":
        return None
    return name, str(value)


def _get_json(url: str, progress: bool = False) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in TRANSIENT_HTTP or attempt == 3:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            _progress(progress, f"[MB] HTTP {exc.code} — retry {attempt + 2}/4 in {min(delay, 30):g}s")
            time.sleep(min(delay, 30))
    raise RuntimeError("unreachable")


def _mb_search(entity: str, query: str, limit: int = 10, progress: bool = False) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"query": query, "fmt": "json", "limit": limit})
    data = _get_json(f"{MB_WS}/{entity}/?{params}", progress=progress)
    time.sleep(1.05)
    return data.get(entity + "s", [])


def _exact_artist_hits(name: str, progress: bool = False) -> list[dict[str, Any]]:
    hits = _mb_search("artist", f'artist:"{name}"', progress=progress)
    return [hit for hit in hits if (hit.get("name") or "").casefold() == name.casefold() and int(hit.get("score", 0)) >= 95]


def resolve_track_artist(name: str, track_title: str | None = None, progress: bool = False) -> dict[str, Any]:
    """Resolve a track artist only when the MusicBrainz match is deterministic.

    1) A single high-confidence exact artist-name hit is accepted.
    2) If several exact-name artists exist, use recording title + artist name to
       disambiguate only when that points to exactly one of those artist MBIDs.
    """
    exact = _exact_artist_hits(name, progress=progress)
    if len(exact) == 1:
        hit = exact[0]
        return {"status": "resolved", "name": hit.get("name") or name, "mbid": hit.get("id"), "basis": "unique exact artist name"}
    if not exact:
        return {"status": "unresolved", "name": name, "mbid": None, "basis": "no high-confidence exact artist name"}

    if track_title:
        recordings = _mb_search("recording", f'recording:"{track_title}" AND artist:"{name}"', progress=progress)
        allowed = {hit.get("id") for hit in exact if hit.get("id")}
        matched: dict[str, str] = {}
        for recording in recordings:
            for credit in recording.get("artist-credit") or []:
                artist = credit.get("artist") if isinstance(credit, dict) else None
                if not artist:
                    continue
                mbid = artist.get("id")
                artist_name = artist.get("name") or credit.get("name")
                if mbid in allowed and (artist_name or "").casefold() == name.casefold():
                    matched[mbid] = artist_name or name
        if len(matched) == 1:
            mbid, resolved_name = next(iter(matched.items()))
            return {"status": "resolved", "name": resolved_name, "mbid": mbid, "basis": "recording title + artist disambiguation"}

    return {"status": "unresolved", "name": name, "mbid": None, "basis": f"ambiguous exact artist name ({len(exact)} candidates)"}


def resolve_track_artists(candidate: dict[str, Any], progress: bool = True) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    release = candidate.get("release") or {}
    medium = release.get("medium") or {}
    tracks = medium.get("tracks") or []
    cache: dict[tuple[str, str | None], dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []

    _progress(progress, f"[MB] resolving track artists for {len(tracks)} tracks")
    for track_index, track in enumerate(tracks):
        title = track.get("title")
        resolved_artists = []
        for artist_name in track.get("artist_names") or []:
            key = (artist_name, title)
            if key not in cache:
                _progress(progress, f"[{track_index + 1:>2}/{len(tracks)}] resolve {artist_name} — {title or '[untitled]'}")
                cache[key] = resolve_track_artist(artist_name, title, progress=progress)
            resolution = cache[key]
            resolved_artists.append({
                "name": artist_name,
                "mbid": resolution.get("mbid"),
                "status": resolution.get("status"),
                "basis": resolution.get("basis"),
            })
            if resolution.get("status") != "resolved" or not resolution.get("mbid"):
                unresolved.append({"track": track_index + 1, "title": title, "artist": artist_name, "reason": resolution.get("basis")})
        track["artist_resolutions"] = resolved_artists

    _progress(progress, f"[MB] track artists: {sum(1 for t in tracks for a in t.get('artist_resolutions') or [] if a.get('mbid'))} resolved; {len(unresolved)} unresolved")
    return candidate, unresolved


def build_seed_fields(candidate: dict[str, Any], require_resolved_track_artists: bool = True) -> list[tuple[str, str]]:
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise ValueError(f"expected {CANDIDATE_SCHEMA}")
    if not candidate.get("submission_ready"):
        unresolved = ", ".join(item.get("field", "unknown") for item in candidate.get("required_unresolved") or [])
        raise ValueError(f"candidate is not submission-ready: {unresolved or 'required fields unresolved'}")

    release = candidate.get("release") or {}
    release_group = candidate.get("release_group") or {}
    artist_credit = candidate.get("artist_credit") or {}
    medium = release.get("medium") or {}
    source = candidate.get("source") or {}

    if require_resolved_track_artists:
        missing = []
        for track_index, track in enumerate(medium.get("tracks") or []):
            resolutions = track.get("artist_resolutions") or []
            for artist_index, artist_name in enumerate(track.get("artist_names") or []):
                resolution = resolutions[artist_index] if artist_index < len(resolutions) else None
                if not resolution or not resolution.get("mbid"):
                    missing.append(f"track {track_index + 1}: {artist_name}")
        if missing:
            preview = "; ".join(missing[:8])
            suffix = f"; +{len(missing) - 8} more" if len(missing) > 8 else ""
            raise ValueError(f"track artists are not fully resolved: {preview}{suffix}")

    fields: list[tuple[str, str]] = []

    def add(name: str, value: Any) -> None:
        item = _field(name, value)
        if item:
            fields.append(item)

    add("name", release.get("title"))
    add("status", (release.get("status") or "").lower())
    add("type", release_group.get("primary_type"))
    for secondary in release_group.get("secondary_types") or []:
        add("type", secondary)

    date = release.get("date")
    if date:
        parts = date.split("-")
        if len(parts) >= 1:
            add("events.0.date.year", parts[0])
        if len(parts) >= 2:
            add("events.0.date.month", parts[1])
        if len(parts) >= 3:
            add("events.0.date.day", parts[2])
    add("events.0.country", release.get("country"))

    label = release.get("label") or {}
    add("labels.0.mbid", label.get("mbid"))
    add("labels.0.name", label.get("name"))
    add("labels.0.catalog_number", release.get("catalog_number"))
    add("barcode", release.get("barcode"))

    artists = artist_credit.get("artists") or []
    for index, artist in enumerate(artists):
        add(f"artist_credit.names.{index}.mbid", artist.get("mbid"))
        credited_as = artist.get("credited_as") or artist.get("name")
        add(f"artist_credit.names.{index}.name", credited_as)
        add(f"artist_credit.names.{index}.artist.name", artist.get("name"))
        if index < len(artists) - 1:
            add(f"artist_credit.names.{index}.join_phrase", ", ")

    add("mediums.0.format", medium.get("format"))
    for track_index, track in enumerate(medium.get("tracks") or []):
        add(f"mediums.0.track.{track_index}.name", track.get("title"))
        add(f"mediums.0.track.{track_index}.number", track.get("position"))
        if track.get("recording_mbid"):
            add(f"mediums.0.track.{track_index}.recording", track.get("recording_mbid"))

        track_artists = track.get("artist_names") or []
        resolutions = track.get("artist_resolutions") or []
        for artist_index, artist_name in enumerate(track_artists):
            resolution = resolutions[artist_index] if artist_index < len(resolutions) else {}
            add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.mbid", resolution.get("mbid"))
            add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.name", artist_name)
            add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.artist.name", resolution.get("name") or artist_name)
            if artist_index < len(track_artists) - 1:
                add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.join_phrase", ", ")

    urls = candidate.get("urls") or []
    for index, url in enumerate(urls):
        add(f"urls.{index}.url", url.get("url"))

    source_url = source.get("url")
    edit_note = (
        "Seeded from the official NTS episode page using musicbrainz-userscripts-cli.\n"
        f"Source: {source_url}\n"
        "Track artists were resolved conservatively against MusicBrainz before seeding.\n"
        "Please review all fields, relationships, and track credits before submitting."
    )
    add("edit_note", edit_note)
    return fields


def render_html(candidate: dict[str, Any]) -> str:
    fields = build_seed_fields(candidate)
    title = candidate.get("release", {}).get("title") or "MusicBrainz release"
    inputs = "\n".join(
        f'<input type="hidden" name="{html.escape(name, quote=True)}" value="{html.escape(value, quote=True)}">'
        for name, value in fields
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Seed MusicBrainz — {html.escape(title)}</title>
<style>body{{font:16px system-ui;max-width:760px;margin:3rem auto;padding:0 1rem}}button{{font-size:1rem;padding:.7rem 1rem}}code{{word-break:break-all}}</style>
</head>
<body>
<h1>MusicBrainz release-editor seed</h1>
<p><strong>{html.escape(title)}</strong></p>
<p>This page does not submit an edit. It only opens MusicBrainz's Add Release editor with the candidate fields prefilled.</p>
<form action="{SEED_ACTION}" method="post" accept-charset="UTF-8">
{inputs}
<button type="submit">Open prefilled MusicBrainz editor</button>
</form>
<p>Source: <code>{html.escape(candidate.get('source', {}).get('url') or '')}</code></p>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a MusicBrainz Add Release seed from an NTS Guide candidate")
    parser.add_argument("candidate", help="nts-guide-candidate/v1 JSON file")
    parser.add_argument("-o", "--output", help="HTML output path")
    parser.add_argument("--open", action="store_true", help="Open the generated local HTML form in the default browser")
    parser.add_argument("--quiet", action="store_true", help="Suppress MusicBrainz track-artist resolution progress")
    parser.add_argument("--allow-unresolved-track-artists", action="store_true", help="Generate the seed even if some track artists could not be resolved; those fields will require manual matching")
    args = parser.parse_args()

    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    progress = not args.quiet
    try:
        candidate, unresolved = resolve_track_artists(candidate, progress=progress)
        if unresolved and not args.allow_unresolved_track_artists:
            preview = "\n".join(f"  track {item['track']}: {item['artist']} — {item['reason']}" for item in unresolved[:12])
            suffix = f"\n  ... +{len(unresolved) - 12} more" if len(unresolved) > 12 else ""
            raise ValueError(
                "cannot generate a fully matched MusicBrainz seed; unresolved track artists remain:\n"
                + preview + suffix
                + "\nUse --allow-unresolved-track-artists only if you intend to match those artists manually in the Release Editor."
            )
        rendered = build_seed_fields(candidate, require_resolved_track_artists=not args.allow_unresolved_track_artists)
        title = candidate.get("release", {}).get("title") or "MusicBrainz release"
        inputs = "\n".join(
            f'<input type="hidden" name="{html.escape(name, quote=True)}" value="{html.escape(value, quote=True)}">'
            for name, value in rendered
        )
        page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Seed MusicBrainz — {html.escape(title)}</title>
<style>body{{font:16px system-ui;max-width:760px;margin:3rem auto;padding:0 1rem}}button{{font-size:1rem;padding:.7rem 1rem}}code{{word-break:break-all}}</style></head>
<body><h1>MusicBrainz release-editor seed</h1><p><strong>{html.escape(title)}</strong></p>
<p>This page does not submit an edit. It only opens MusicBrainz's Add Release editor with the candidate fields prefilled.</p>
<form action="{SEED_ACTION}" method="post" accept-charset="UTF-8">{inputs}<button type="submit">Open prefilled MusicBrainz editor</button></form>
<p>Source: <code>{html.escape(candidate.get('source', {}).get('url') or '')}</code></p></body></html>"""
    except ValueError as exc:
        parser.error(str(exc))

    if args.output:
        output = Path(args.output)
        output.write_text(page, encoding="utf-8")
    else:
        handle = tempfile.NamedTemporaryFile("w", suffix="-nts-musicbrainz-seed.html", delete=False, encoding="utf-8")
        with handle:
            handle.write(page)
        output = Path(handle.name)

    print(f"seed HTML: {output}")
    print("safety: opening this file does NOT submit a MusicBrainz edit; use its button to open the prefilled editor")
    if unresolved:
        print(f"track artists requiring manual match: {len(unresolved)}")
    else:
        print("track artists: all resolved to MusicBrainz MBIDs")
    if args.open:
        webbrowser.open(output.resolve().as_uri())


if __name__ == "__main__":
    main()
