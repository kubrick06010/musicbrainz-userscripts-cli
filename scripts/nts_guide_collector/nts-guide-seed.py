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
import re
import sys
import tempfile
import time
import unicodedata
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


def _norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold().strip()
    text = re.sub(r"[‐‑‒–—−]", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _safe_query_names(name: str) -> list[tuple[str, str]]:
    """Return conservative search variants while preserving the original credit."""
    variants = [(name.strip(), "source credit")]
    aka = re.split(r"\s+aka\s+", name, maxsplit=1, flags=re.I)
    if len(aka) == 2:
        variants.extend([(aka[0].strip(), "AKA left side"), (aka[1].strip(), "AKA right side")])
    parenthetical = re.match(r"^(.+?)\s*\(([^()]*)\)\s*$", name)
    if parenthetical:
        variants.append((parenthetical.group(1).strip(), "parenthetical context stripped"))
    out = []
    seen = set()
    for value, basis in variants:
        key = _norm(value)
        if value and key not in seen:
            seen.add(key)
            out.append((value, basis))
    return out


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


def _artist_names(hit: dict[str, Any]) -> set[str]:
    names = {hit.get("name"), hit.get("sort-name")}
    for alias in hit.get("aliases") or []:
        if isinstance(alias, dict):
            names.add(alias.get("name"))
            names.add(alias.get("sort-name"))
        elif isinstance(alias, str):
            names.add(alias)
    return {_norm(name) for name in names if name}


def _matching_artist_hits(name: str, progress: bool = False) -> list[dict[str, Any]]:
    # inc=aliases is not supported on search requests, but aliases matching the query
    # are included by MusicBrainz search results. Match canonical/sort/alias names.
    hits = _mb_search("artist", f'artist:"{name}"', progress=progress)
    wanted = _norm(name)
    matched = []
    for hit in hits:
        if int(hit.get("score", 0)) < 95:
            continue
        if wanted in _artist_names(hit):
            matched.append(hit)
    return matched


def _recording_artist_mbids(track_title: str, search_name: str, progress: bool = False) -> set[str]:
    recordings = _mb_search("recording", f'recording:"{track_title}" AND artist:"{search_name}"', progress=progress)
    mbids = set()
    for recording in recordings:
        if int(recording.get("score", 0)) < 90:
            continue
        for credit in recording.get("artist-credit") or []:
            artist = credit.get("artist") if isinstance(credit, dict) else None
            if artist and artist.get("id"):
                mbids.add(artist["id"])
    return mbids


def resolve_track_artist(name: str, track_title: str | None = None, progress: bool = False) -> dict[str, Any]:
    """Resolve canonical names, aliases/transliterations and safe credit wrappers."""
    candidates: dict[str, tuple[dict[str, Any], str, str]] = {}
    for search_name, variant_basis in _safe_query_names(name):
        for hit in _matching_artist_hits(search_name, progress=progress):
            mbid = hit.get("id")
            if mbid:
                candidates[mbid] = (hit, search_name, variant_basis)

    if len(candidates) == 1:
        hit, search_name, variant_basis = next(iter(candidates.values()))
        canonical = hit.get("name") or search_name
        basis = "unique MusicBrainz canonical/alias match"
        if variant_basis != "source credit":
            basis += f" via {variant_basis}"
        return {"status": "resolved", "name": canonical, "mbid": hit.get("id"), "basis": basis}

    if candidates and track_title:
        recording_mbids = set()
        for _hit, search_name, _basis in candidates.values():
            recording_mbids |= _recording_artist_mbids(track_title, search_name, progress=progress)
        matched = [value for mbid, value in candidates.items() if mbid in recording_mbids]
        if len(matched) == 1:
            hit, search_name, variant_basis = matched[0]
            canonical = hit.get("name") or search_name
            return {
                "status": "resolved", "name": canonical, "mbid": hit.get("id"),
                "basis": f"recording title + MusicBrainz alias disambiguation via {variant_basis}",
            }

    if not candidates:
        return {"status": "unresolved", "name": name, "mbid": None, "basis": "no high-confidence canonical or alias match"}
    return {"status": "unresolved", "name": name, "mbid": None, "basis": f"ambiguous canonical/alias match ({len(candidates)} candidates)"}


def resolve_track_artists(candidate: dict[str, Any], progress: bool = True) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tracks = ((candidate.get("release") or {}).get("medium") or {}).get("tracks") or []
    cache: dict[tuple[str, str | None], dict[str, Any]] = {}
    unresolved = []
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
            resolved_artists.append({"name": artist_name, "mbid": resolution.get("mbid"), "status": resolution.get("status"), "basis": resolution.get("basis"), "canonical_name": resolution.get("name")})
            if resolution.get("status") != "resolved" or not resolution.get("mbid"):
                unresolved.append({"track": track_index + 1, "title": title, "artist": artist_name, "reason": resolution.get("basis")})
        track["artist_resolutions"] = resolved_artists
    resolved_count = sum(1 for track in tracks for artist in track.get("artist_resolutions") or [] if artist.get("mbid"))
    _progress(progress, f"[MB] track artists: {resolved_count} resolved; {len(unresolved)} unresolved")
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
        if parts: add("events.0.date.year", parts[0])
        if len(parts) >= 2: add("events.0.date.month", parts[1])
        if len(parts) >= 3: add("events.0.date.day", parts[2])
    add("events.0.country", release.get("country"))

    label = release.get("label") or {}
    add("labels.0.mbid", label.get("mbid"))
    add("labels.0.name", label.get("name"))
    add("labels.0.catalog_number", release.get("catalog_number"))
    add("barcode", release.get("barcode"))

    artists = artist_credit.get("artists") or []
    for index, artist in enumerate(artists):
        add(f"artist_credit.names.{index}.mbid", artist.get("mbid"))
        add(f"artist_credit.names.{index}.name", artist.get("credited_as") or artist.get("name"))
        add(f"artist_credit.names.{index}.artist.name", artist.get("name"))
        if index < len(artists) - 1: add(f"artist_credit.names.{index}.join_phrase", ", ")

    add("mediums.0.format", medium.get("format"))
    for track_index, track in enumerate(medium.get("tracks") or []):
        add(f"mediums.0.track.{track_index}.name", track.get("title"))
        add(f"mediums.0.track.{track_index}.number", track.get("position"))
        if track.get("recording_mbid"):
            add(f"mediums.0.track.{track_index}.recording", track.get("recording_mbid"))
        resolutions = track.get("artist_resolutions") or []
        for artist_index, artist_name in enumerate(track.get("artist_names") or []):
            resolution = resolutions[artist_index] if artist_index < len(resolutions) else {}
            add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.mbid", resolution.get("mbid"))
            add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.name", artist_name)
            add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.artist.name", resolution.get("canonical_name") or artist_name)
            if artist_index < len(track.get("artist_names") or []) - 1:
                add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.join_phrase", ", ")

    for index, url in enumerate(candidate.get("urls") or []):
        add(f"urls.{index}.url", url.get("url"))
    source_url = source.get("url")
    add("edit_note", "Seeded from the official NTS episode page using musicbrainz-userscripts-cli.\n" f"Source: {source_url}\n" "Track artists were resolved conservatively against MusicBrainz before seeding.\n" "Please review all fields, relationships, and track credits before submitting.")
    return fields


def _render_page(candidate: dict[str, Any], fields: list[tuple[str, str]]) -> str:
    title = candidate.get("release", {}).get("title") or "MusicBrainz release"
    inputs = "\n".join(f'<input type="hidden" name="{html.escape(name, quote=True)}" value="{html.escape(value, quote=True)}">' for name, value in fields)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Seed MusicBrainz — {html.escape(title)}</title><style>body{{font:16px system-ui;max-width:760px;margin:3rem auto;padding:0 1rem}}button{{font-size:1rem;padding:.7rem 1rem}}code{{word-break:break-all}}</style></head><body><h1>MusicBrainz release-editor seed</h1><p><strong>{html.escape(title)}</strong></p><p>This page does not submit an edit. It only opens MusicBrainz's Add Release editor with the candidate fields prefilled.</p><form action="{SEED_ACTION}" method="post" accept-charset="UTF-8">{inputs}<button type="submit">Open prefilled MusicBrainz editor</button></form><p>Source: <code>{html.escape(candidate.get('source', {}).get('url') or '')}</code></p></body></html>'''


def render_html(candidate: dict[str, Any]) -> str:
    return _render_page(candidate, build_seed_fields(candidate))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a MusicBrainz Add Release seed from an NTS Guide candidate")
    parser.add_argument("candidate", help="nts-guide-candidate/v1 JSON file")
    parser.add_argument("-o", "--output", help="HTML output path")
    parser.add_argument("--open", action="store_true", help="Open the generated local HTML form in the default browser")
    parser.add_argument("--quiet", action="store_true", help="Suppress MusicBrainz track-artist resolution progress")
    parser.add_argument("--allow-unresolved-track-artists", action="store_true", help="Generate the seed even if some track artists could not be resolved; those fields will require manual matching")
    args = parser.parse_args()

    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    try:
        candidate, unresolved = resolve_track_artists(candidate, progress=not args.quiet)
        if unresolved and not args.allow_unresolved_track_artists:
            preview = "\n".join(f"  track {item['track']}: {item['artist']} — {item['reason']}" for item in unresolved[:12])
            suffix = f"\n  ... +{len(unresolved) - 12} more" if len(unresolved) > 12 else ""
            raise ValueError("cannot generate a fully matched MusicBrainz seed; unresolved track artists remain:\n" + preview + suffix + "\nUse --allow-unresolved-track-artists only if you intend to match those artists manually in the Release Editor.")
        fields = build_seed_fields(candidate, require_resolved_track_artists=not args.allow_unresolved_track_artists)
        page = _render_page(candidate, fields)
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
    print(f"track artists requiring manual match: {len(unresolved)}" if unresolved else "track artists: all resolved to MusicBrainz MBIDs")
    if args.open:
        webbrowser.open(output.resolve().as_uri())


if __name__ == "__main__":
    main()
