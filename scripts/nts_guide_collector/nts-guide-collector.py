#!/usr/bin/env python3
"""Collect NTS Guide episodes into a coverage-first MusicBrainz inventory.

Read-only by design: this script never submits MusicBrainz edits.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

NTS = "https://www.nts.live"
NTS_API = NTS + "/api/v2/shows/{slug}/episodes"
MB_WS = "https://musicbrainz.org/ws/2"
UA = "musicbrainz-userscripts-cli/nts-guide-collector (https://github.com/kubrick06010/musicbrainz-userscripts-cli)"
NTS_LABEL_MBID = "2528f939-28ca-4da6-86c9-c6aab7bc4bc2"
TRANSIENT_HTTP = {429, 500, 502, 503, 504}


def load_mb_access_token(path: str) -> str | None:
    token_path = Path(path)
    if not token_path.exists():
        return None
    try:
        token = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid MusicBrainz token file: {path}") from exc
    access_token = token.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise SystemExit(f"MusicBrainz token file has no access_token: {path}")
    return access_token.strip()


def get_json(url: str, accept: str = "application/json", bearer_token: str | None = None) -> Any:
    headers = {"User-Agent": UA, "Accept": accept}
    if bearer_token and url.startswith(MB_WS):
        headers["Authorization"] = f"Bearer {bearer_token}"
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in TRANSIENT_HTTP or attempt == 3:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            time.sleep(min(delay, 30))
    raise RuntimeError("unreachable")


def nts_episode_url(alias: str) -> str:
    return f"{NTS}/shows/the-nts-guide-to/episodes/{alias}"


def _split_credit_names(name: str) -> list[str]:
    """Split only plainly plural human credits; preserve ambiguous names as one value."""
    cleaned = name.strip()
    # Restrict splitting to simple person-like text. Parentheses, slashes and featuring/of
    # phrases are kept intact for later human review rather than guessed apart.
    if re.search(r"[()/]", cleaned) or re.search(r"\b(feat(?:uring)?|of|with|vs\.?)\b", cleaned, re.I):
        return [cleaned]
    parts = re.split(r"\s+(?:and|&)\s+", cleaned, flags=re.I)
    parts = [part.strip() for part in parts if part.strip()]
    return parts if 1 < len(parts) <= 4 else [cleaned]


def extract_credits(description: str) -> list[dict[str, Any]]:
    patterns = [
        (r"selected\s+(?:and|&)\s+mixed\s+by\s+([^.;\n]+)", "dj-mixer", 0.98),
        (r"mixed\s+by\s+([^.;\n]+)", "dj-mixer", 0.95),
        (r"words\s+and\s+selections\s+by\s+([^.;\n]+)", "compiler", 0.90),
        (r"selections\s+by\s+([^.;\n]+)", "compiler", 0.88),
        (r"compiled\s+by\s+([^.;\n]+)", "compiler", 0.88),
        (r"selected\s+by\s+([^.;\n]+)", "compiler", 0.85),
        (r"curated\s+by\s+([^.;\n]+)", "compiler", 0.80),
    ]
    text = description or ""
    for pattern, role, confidence in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            raw = match.group(0).strip()
            captured = match.group(1).strip()
            return [
                {"raw": raw, "name": name, "role": role, "confidence": confidence}
                for name in _split_credit_names(captured)
            ]
    return []


def mb_search(entity: str, query: str, bearer_token: str | None, limit: int = 5) -> dict[str, Any]:
    params = urllib.parse.urlencode({"query": query, "fmt": "json", "limit": limit})
    try:
        data = get_json(f"{MB_WS}/{entity}/?{params}", bearer_token=bearer_token)
    except HTTPError as exc:
        if exc.code not in TRANSIENT_HTTP:
            raise
        return {"lookup_status": "transient_error", "http_status": exc.code, "results": []}
    time.sleep(1.05)
    return {"lookup_status": "ok", "http_status": None, "results": data.get(entity + "s", [])}


def resolve_artist(name: str, bearer_token: str | None) -> dict[str, Any]:
    search = mb_search("artist", f'artist:"{name}"', bearer_token)
    if search["lookup_status"] != "ok":
        return {
            "name": name,
            "mbid": None,
            "score": 0,
            "status": "transient_error",
            "lookup_status": search["lookup_status"],
            "http_status": search["http_status"],
            "candidates": [],
        }
    hits = search["results"]
    exact = [hit for hit in hits if hit.get("name", "").casefold() == name.casefold()]
    best = exact[0] if exact else (hits[0] if hits else None)
    if not best:
        return {"name": name, "mbid": None, "score": 0, "status": "missing", "lookup_status": "ok", "candidates": []}
    score = int(best.get("score", 0))
    status = "resolved" if exact and score >= 95 else "review"
    return {
        "name": name,
        "mbid": best.get("id"),
        "score": score,
        "status": status,
        "lookup_status": "ok",
        "candidates": [
            {
                "name": hit.get("name"),
                "mbid": hit.get("id"),
                "score": hit.get("score"),
                "disambiguation": hit.get("disambiguation"),
            }
            for hit in hits
        ],
    }


def duplicate_search(title: str, date: str | None, bearer_token: str | None) -> dict[str, Any]:
    query = f'release:"{title}"'
    if date:
        query += f" AND date:{date[:10]}"
    search = mb_search("release", query, bearer_token)
    if search["lookup_status"] != "ok":
        return {
            "lookup_status": search["lookup_status"],
            "http_status": search["http_status"],
            "found": None,
            "candidates": [],
        }
    hits = search["results"]
    return {
        "lookup_status": "ok",
        "http_status": None,
        "found": bool(hits),
        "candidates": [
            {"title": hit.get("title"), "mbid": hit.get("id"), "score": hit.get("score"), "date": hit.get("date")}
            for hit in hits
        ],
    }


def normalize_track(track: dict[str, Any], position: int) -> dict[str, Any]:
    def names(key: str) -> list[str]:
        values = []
        for value in track.get(key) or []:
            values.append(value.get("name") if isinstance(value, dict) else str(value))
        return [value for value in values if value]

    return {
        "position": position,
        "title": track.get("title"),
        "offset": track.get("offset"),
        "main_artists": names("mainArtists"),
        "featuring_artists": names("featuringArtists"),
        "remix_artists": names("remixArtists"),
    }


def episode_detail(alias: str) -> dict[str, Any]:
    return get_json(nts_episode_url(alias))


def classify(ep: dict[str, Any], do_mb: bool, bearer_token: str | None) -> dict[str, Any]:
    alias = ep.get("episode_alias") or ep.get("alias")
    detail = episode_detail(alias) if alias else ep
    description = detail.get("description") or ep.get("description") or ""
    credits = extract_credits(description)
    broadcast = detail.get("broadcast") or ep.get("broadcast")
    title = (detail.get("name") or ep.get("name") or "").strip()
    tracks = [normalize_track(track, index + 1) for index, track in enumerate(detail.get("tracklist") or [])]
    media = detail.get("media") or ep.get("media") or {}
    cover_url = media.get("picture_large") or media.get("background_large")

    creation_blockers: list[str] = []
    enrichment_pending: list[str] = []

    if not title:
        creation_blockers.append("missing_title")
    if not broadcast:
        enrichment_pending.append("missing_broadcast_date")
    if not tracks:
        enrichment_pending.append("missing_tracklist")
    if not cover_url:
        enrichment_pending.append("missing_cover_art")
    if not credits:
        enrichment_pending.append("no_explicit_mixer_credit")

    credit_resolutions = []
    if do_mb:
        for credit in credits:
            if credit["name"].casefold() == "nts":
                credit_resolutions.append({**credit, "resolution": {"name": "NTS", "status": "collective", "lookup_status": "not_needed"}})
                enrichment_pending.append("credit_is_nts_collective")
                continue
            resolution = resolve_artist(credit["name"], bearer_token)
            credit_resolutions.append({**credit, "resolution": resolution})
            if resolution["status"] == "transient_error":
                enrichment_pending.append("artist_lookup_transient")
            elif resolution["status"] != "resolved":
                enrichment_pending.append("unresolved_explicit_credit")
    else:
        credit_resolutions = [{**credit, "resolution": None} for credit in credits]
        if credits:
            enrichment_pending.append("artist_resolution_not_run")

    duplicate = None
    if do_mb and title:
        duplicate = duplicate_search(title, broadcast, bearer_token)
        if duplicate["lookup_status"] != "ok":
            creation_blockers.append("duplicate_check_transient")
        elif duplicate["found"]:
            creation_blockers.append("possible_duplicate_release")
    elif title:
        creation_blockers.append("duplicate_check_not_run")

    creation_status = "BLOCKED" if creation_blockers else "CREATABLE"
    enrichment_pending = sorted(set(enrichment_pending))
    enrichment_status = "COMPLETE" if not enrichment_pending else "PENDING"

    return {
        "nts": {
            "show": "NTS Guide to…",
            "episode_alias": alias,
            "url": nts_episode_url(alias) if alias else None,
            "title": title,
            "broadcast": broadcast,
            "location": detail.get("location_short") or ep.get("location_short"),
            "description": description,
            "genres": [genre.get("value", genre) if isinstance(genre, dict) else genre for genre in (detail.get("genres") or ep.get("genres") or [])],
            "cover_url": cover_url,
            "mixcloud": detail.get("mixcloud") or ep.get("mixcloud"),
            "audio_sources": detail.get("audio_sources") or ep.get("audio_sources") or [],
            "tracklist": tracks,
        },
        "credits": credit_resolutions,
        "musicbrainz": {
            "release_title": title,
            "release_status": "Official",
            "release_group_secondary_types": ["Broadcast", "DJ-mix"],
            "format": "Digital Media",
            "country": "XW",
            "label": {"name": "NTS Radio", "mbid": NTS_LABEL_MBID},
            "catalog_number": None,
            "barcode": None,
            "duplicate_release": duplicate,
            "external_urls": [{"url": nts_episode_url(alias), "source": "NTS"}] if alias else [],
        },
        "creation_readiness": {"status": creation_status, "blockers": creation_blockers},
        "enrichment": {"status": enrichment_status, "pending": enrichment_pending},
    }


def summarize(episodes: list[dict[str, Any]]) -> dict[str, int]:
    def count_episode(predicate) -> int:
        return sum(1 for episode in episodes if predicate(episode))

    return {
        "CREATABLE": count_episode(lambda episode: episode["creation_readiness"]["status"] == "CREATABLE"),
        "BLOCKED": count_episode(lambda episode: episode["creation_readiness"]["status"] == "BLOCKED"),
        "duplicate_blocked": count_episode(lambda episode: "possible_duplicate_release" in episode["creation_readiness"]["blockers"]),
        "duplicate_check_transient": count_episode(lambda episode: "duplicate_check_transient" in episode["creation_readiness"]["blockers"]),
        "enrichment_complete": count_episode(lambda episode: episode["enrichment"]["status"] == "COMPLETE"),
        "enrichment_pending": count_episode(lambda episode: episode["enrichment"]["status"] == "PENDING"),
        "missing_explicit_credit": count_episode(lambda episode: "no_explicit_mixer_credit" in episode["enrichment"]["pending"]),
        "unresolved_explicit_credit": count_episode(lambda episode: "unresolved_explicit_credit" in episode["enrichment"]["pending"]),
        "missing_tracklist": count_episode(lambda episode: "missing_tracklist" in episode["enrichment"]["pending"]),
        "cover_art_available": count_episode(lambda episode: bool(episode["nts"]["cover_url"])),
    }


def collect(slug: str, limit: int, do_mb: bool, bearer_token: str | None, max_episodes: int | None = None) -> dict[str, Any]:
    offset = 0
    episodes: list[dict[str, Any]] = []
    total = None
    while total is None or offset < total:
        url = NTS_API.format(slug=slug) + "?" + urllib.parse.urlencode({"offset": offset, "limit": limit})
        page = get_json(url)
        meta = page.get("metadata", {}).get("resultset", {})
        total = int(meta.get("count", 0))
        batch = page.get("results", [])
        if not batch:
            break
        if max_episodes is not None:
            batch = batch[: max_episodes - len(episodes)]
        episodes.extend(classify(ep, do_mb, bearer_token) for ep in batch)
        offset += len(batch)
        if max_episodes is not None and len(episodes) >= max_episodes:
            break

    return {
        "schema": "nts-guide-collector/v3",
        "show_slug": slug,
        "musicbrainz_auth": "bearer" if do_mb and bearer_token else ("anonymous" if do_mb else "disabled"),
        "episode_count": len(episodes),
        "coverage_counts": summarize(episodes),
        "episodes": episodes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect NTS Guide episodes into a coverage-first MusicBrainz inventory")
    parser.add_argument("--show", default="the-nts-guide-to")
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--no-musicbrainz", action="store_true", help="Skip MB artist/duplicate lookups; creation readiness will remain blocked")
    parser.add_argument("--mb-token-file", default=".mb_token.json", help="OAuth token JSON used for MusicBrainz requests")
    parser.add_argument("--max-episodes", type=int, help="Stop after this many episodes (useful for a smoke test)")
    parser.add_argument("-o", "--output", default="nts-guide-inventory.json")
    args = parser.parse_args()

    do_mb = not args.no_musicbrainz
    bearer_token = load_mb_access_token(args.mb_token_file) if do_mb else None
    if args.max_episodes is not None and args.max_episodes < 1:
        parser.error("--max-episodes must be positive")

    inventory = collect(args.show, args.page_size, do_mb, bearer_token, args.max_episodes)
    Path(args.output).write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "episodes": inventory["episode_count"], **inventory["coverage_counts"]}, indent=2))


if __name__ == "__main__":
    main()
