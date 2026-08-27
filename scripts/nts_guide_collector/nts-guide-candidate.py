#!/usr/bin/env python3
"""Build a read-only MusicBrainz submission candidate from an NTS Guide v3 inventory.

This module never submits edits. It translates one CREATABLE inventory episode into a
reviewable candidate while preserving unresolved required fields instead of guessing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "nts-guide-candidate/v1"


def _date_only(value: str | None) -> str | None:
    return value[:10] if value else None


def find_episode(inventory: dict[str, Any], selector: str) -> dict[str, Any]:
    episodes = inventory.get("episodes") or []
    matches = [
        episode for episode in episodes
        if selector in {
            episode.get("nts", {}).get("episode_alias"),
            episode.get("nts", {}).get("title"),
        }
    ]
    if not matches:
        raise ValueError(f"episode not found: {selector}")
    if len(matches) > 1:
        raise ValueError(f"episode selector is ambiguous: {selector}")
    return matches[0]


def build_candidate(episode: dict[str, Any]) -> dict[str, Any]:
    readiness = episode.get("creation_readiness") or {}
    if readiness.get("status") != "CREATABLE":
        blockers = ", ".join(readiness.get("blockers") or []) or "unknown blocker"
        raise ValueError(f"episode is not CREATABLE: {blockers}")

    nts = episode.get("nts") or {}
    mb = episode.get("musicbrainz") or {}
    credits = episode.get("credits") or []

    relationships = []
    unresolved_relationships = []
    for credit in credits:
        resolution = credit.get("resolution") or {}
        if resolution.get("status") == "resolved" and resolution.get("mbid"):
            relationships.append({
                "type": credit.get("role"),
                "artist": {
                    "name": resolution.get("name") or credit.get("name"),
                    "mbid": resolution.get("mbid"),
                },
                "credited_as": credit.get("name"),
                "source_text": credit.get("raw"),
            })
        else:
            unresolved_relationships.append({
                "type": credit.get("role"),
                "name": credit.get("name"),
                "source_text": credit.get("raw"),
                "resolution_status": resolution.get("status") if resolution else "not_resolved",
            })

    tracks = []
    for track in nts.get("tracklist") or []:
        tracks.append({
            "position": track.get("position"),
            "title": track.get("title"),
            "artist_names": track.get("main_artists") or [],
            "featuring_artist_names": track.get("featuring_artists") or [],
            "remix_artist_names": track.get("remix_artists") or [],
            "offset_seconds": track.get("offset"),
            "recording_mbid": None,
        })

    required_unresolved = []
    # MusicBrainz release/release-group creation requires an artist credit. The NTS
    # collector does not yet establish one, and DJ/compiler relationships are not a
    # safe substitute for release artist credit.
    required_unresolved.append({
        "field": "artist_credit",
        "reason": "not established by collector; do not infer from mixer/compiler credits",
    })
    # The collector currently models secondary types only. Keep primary type explicit
    # and unresolved rather than guessing Album/Other.
    required_unresolved.append({
        "field": "release_group.primary_type",
        "reason": "not established by collector",
    })

    source_url = nts.get("url")
    candidate = {
        "schema": SCHEMA,
        "submission_ready": not required_unresolved,
        "source": {
            "provider": "NTS",
            "url": source_url,
            "episode_alias": nts.get("episode_alias"),
        },
        "release_group": {
            "title": mb.get("release_title") or nts.get("title"),
            "primary_type": None,
            "secondary_types": mb.get("release_group_secondary_types") or [],
        },
        "release": {
            "title": mb.get("release_title") or nts.get("title"),
            "status": mb.get("release_status"),
            "date": _date_only(nts.get("broadcast")),
            "country": mb.get("country"),
            "label": mb.get("label"),
            "catalog_number": mb.get("catalog_number"),
            "barcode": mb.get("barcode"),
            "medium": {"format": mb.get("format"), "tracks": tracks},
        },
        "artist_credit": None,
        "relationships": relationships,
        "unresolved_relationships": unresolved_relationships,
        "urls": mb.get("external_urls") or ([{"url": source_url, "source": "NTS"}] if source_url else []),
        "cover_art": {
            "available": bool(nts.get("cover_url")),
            "source_url": nts.get("cover_url"),
        },
        "notes": {
            "description": nts.get("description"),
            "genres": nts.get("genres") or [],
            "mixcloud": nts.get("mixcloud"),
            "audio_sources": nts.get("audio_sources") or [],
            "enrichment": episode.get("enrichment") or {},
        },
        "required_unresolved": required_unresolved,
        "provenance": {
            "release.title": "nts.title",
            "release.date": "nts.broadcast",
            "release.status": "collector.musicbrainz.release_status",
            "release.country": "collector.musicbrainz.country",
            "release.label": "collector.musicbrainz.label",
            "release.medium.format": "collector.musicbrainz.format",
            "release.medium.tracks": "nts.tracklist",
            "relationships": "nts.description + MusicBrainz artist resolution",
            "urls": "nts.url",
            "cover_art.source_url": "nts.cover_url",
        },
    }
    return candidate


def render_text(candidate: dict[str, Any]) -> str:
    rg = candidate["release_group"]
    release = candidate["release"]
    lines = [
        "MUSICBRAINZ CANDIDATE (READ-ONLY)",
        f"Submission ready: {'YES' if candidate['submission_ready'] else 'NO'}",
        "",
        "RELEASE GROUP",
        f"Title: {rg.get('title') or ''}",
        f"Primary type: {rg.get('primary_type') or '[UNRESOLVED]'}",
        f"Secondary types: {', '.join(rg.get('secondary_types') or []) or '[none]'}",
        "",
        "RELEASE",
        f"Title: {release.get('title') or ''}",
        f"Artist credit: [UNRESOLVED]",
        f"Status: {release.get('status') or ''}",
        f"Date: {release.get('date') or ''}",
        f"Country: {release.get('country') or ''}",
        f"Label: {(release.get('label') or {}).get('name') or ''} [{(release.get('label') or {}).get('mbid') or ''}]",
        f"Format: {(release.get('medium') or {}).get('format') or ''}",
        "",
        "TRACKLIST",
    ]
    for track in (release.get("medium") or {}).get("tracks") or []:
        artists = ", ".join(track.get("artist_names") or []) or "[artist unresolved]"
        lines.append(f"{track.get('position', ''):>2}. {artists} — {track.get('title') or '[untitled]'}")
    lines.extend(["", "RELATIONSHIPS"])
    if candidate.get("relationships"):
        for relationship in candidate["relationships"]:
            artist = relationship["artist"]
            lines.append(f"{relationship.get('type')}: {artist.get('name')} [{artist.get('mbid')}] — source: {relationship.get('source_text')}")
    else:
        lines.append("[none resolved]")
    if candidate.get("unresolved_relationships"):
        lines.append("")
        lines.append("UNRESOLVED RELATIONSHIPS")
        for relationship in candidate["unresolved_relationships"]:
            lines.append(f"{relationship.get('type')}: {relationship.get('name')} ({relationship.get('resolution_status')})")
    lines.extend(["", "URLS"])
    for url in candidate.get("urls") or []:
        lines.append(url.get("url") or "")
    lines.extend(["", "COVER ART", f"Source: {candidate.get('cover_art', {}).get('source_url') or '[none]'}"])
    lines.extend(["", "REQUIRED UNRESOLVED"])
    for item in candidate.get("required_unresolved") or []:
        lines.append(f"- {item['field']}: {item['reason']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a read-only MusicBrainz candidate from an NTS Guide v3 inventory")
    parser.add_argument("inventory")
    parser.add_argument("--episode", required=True, help="Exact episode alias or title")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    if inventory.get("schema") != "nts-guide-collector/v3":
        parser.error("candidate builder requires nts-guide-collector/v3 input")
    try:
        candidate = build_candidate(find_episode(inventory, args.episode))
    except ValueError as exc:
        parser.error(str(exc))

    rendered = json.dumps(candidate, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_text(candidate)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
