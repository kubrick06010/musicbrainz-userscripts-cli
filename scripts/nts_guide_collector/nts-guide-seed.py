#!/usr/bin/env python3
"""Generate a local HTML form that seeds the MusicBrainz Add Release editor.

This tool does not submit MusicBrainz edits. It only POSTs candidate fields into
MusicBrainz's documented release-editor seeding endpoint so the user can review
and submit from the normal MusicBrainz UI.
"""
from __future__ import annotations

import argparse
import html
import json
import tempfile
import webbrowser
from pathlib import Path
from typing import Any

CANDIDATE_SCHEMA = "nts-guide-candidate/v1"
SEED_ACTION = "https://musicbrainz.org/release/add"


def _field(name: str, value: Any) -> tuple[str, str] | None:
    if value is None or value == "":
        return None
    return name, str(value)


def build_seed_fields(candidate: dict[str, Any]) -> list[tuple[str, str]]:
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
    # Do not seed a missing barcode as "none": absence from NTS is not proof that
    # the release has no barcode.
    add("barcode", release.get("barcode"))

    artists = artist_credit.get("artists") or []
    for index, artist in enumerate(artists):
        add(f"artist_credit.names.{index}.mbid", artist.get("mbid"))
        credited_as = artist.get("credited_as") or artist.get("name")
        add(f"artist_credit.names.{index}.name", credited_as)
        add(f"artist_credit.names.{index}.artist.name", artist.get("name"))
        if index < len(artists) - 1:
            # Candidate v1 does not yet preserve an explicit release-credit join
            # phrase, so use a neutral comma separator rather than inventing source wording.
            add(f"artist_credit.names.{index}.join_phrase", ", ")

    add("mediums.0.format", medium.get("format"))
    for track_index, track in enumerate(medium.get("tracks") or []):
        add(f"mediums.0.track.{track_index}.name", track.get("title"))
        add(f"mediums.0.track.{track_index}.number", track.get("position"))
        if track.get("recording_mbid"):
            add(f"mediums.0.track.{track_index}.recording", track.get("recording_mbid"))

        # Seed only NTS main-artist names. Featuring/remix arrays are preserved in
        # the candidate but are not promoted to artist-credit structure without an
        # explicit mapping rule.
        track_artists = track.get("artist_names") or []
        for artist_index, artist_name in enumerate(track_artists):
            add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.name", artist_name)
            add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.artist.name", artist_name)
            if artist_index < len(track_artists) - 1:
                add(f"mediums.0.track.{track_index}.artist_credit.names.{artist_index}.join_phrase", ", ")

    urls = candidate.get("urls") or []
    for index, url in enumerate(urls):
        add(f"urls.{index}.url", url.get("url"))
        # Intentionally leave link_type unset for review in the release editor.

    source_url = source.get("url")
    edit_note = (
        "Seeded from the official NTS episode page using musicbrainz-userscripts-cli.\n"
        f"Source: {source_url}\n"
        "Please review all fields, artist matches, relationships, and track credits before submitting."
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
    args = parser.parse_args()

    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    try:
        rendered = render_html(candidate)
    except ValueError as exc:
        parser.error(str(exc))

    if args.output:
        output = Path(args.output)
        output.write_text(rendered, encoding="utf-8")
    else:
        handle = tempfile.NamedTemporaryFile("w", suffix="-nts-musicbrainz-seed.html", delete=False, encoding="utf-8")
        with handle:
            handle.write(rendered)
        output = Path(handle.name)

    print(f"seed HTML: {output}")
    print("safety: opening this file does NOT submit a MusicBrainz edit; use its button to open the prefilled editor")
    if args.open:
        webbrowser.open(output.resolve().as_uri())


if __name__ == "__main__":
    main()
