#!/usr/bin/env python3
"""Collect NTS Guide episodes into a MusicBrainz-oriented preflight inventory.

Read-only by design: this script never submits MusicBrainz edits.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

NTS = "https://www.nts.live"
NTS_API = NTS + "/api/v2/shows/{slug}/episodes"
MB_WS = "https://musicbrainz.org/ws/2"
UA = "musicbrainz-userscripts-cli/nts-guide-collector (https://github.com/kubrick06010/musicbrainz-userscripts-cli)"
NTS_LABEL_MBID = "2528f939-28ca-4da6-86c9-c6aab7bc4bc2"
MB_TRANSIENT_ERRORS: list[dict[str, Any]] = []


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
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            time.sleep(min(delay, 30))
    raise RuntimeError("unreachable")


def nts_episode_url(alias: str) -> str:
    return f"{NTS}/shows/the-nts-guide-to/episodes/{alias}"


def extract_credit(description: str) -> dict[str, Any] | None:
    patterns = [
        (r"selected\s+and\s+mixed\s+by\s+([^.;\n]+)", "dj-mixer", 0.98),
        (r"mixed\s+by\s+([^.;\n]+)", "dj-mixer", 0.95),
        (r"selected\s+by\s+([^.;\n]+)", "compiler", 0.85),
        (r"curated\s+by\s+([^.;\n]+)", "compiler", 0.80),
    ]
    for pattern, role, confidence in patterns:
        m = re.search(pattern, description or "", flags=re.I)
        if m:
            return {"raw": m.group(0).strip(), "name": m.group(1).strip(), "role": role, "confidence": confidence}
    return None


def mb_search(entity: str, query: str, bearer_token: str | None, limit: int = 5) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"query": query, "fmt": "json", "limit": limit})
    try:
        data = get_json(f"{MB_WS}/{entity}/?{params}", bearer_token=bearer_token)
    except HTTPError as exc:
        if exc.code not in (429, 500, 502, 503, 504):
            raise
        MB_TRANSIENT_ERRORS.append({"entity": entity, "status": exc.code})
        return []
    time.sleep(1.05)  # respect MusicBrainz WS rate guidance
    return data.get(entity + "s", [])


def resolve_artist(name: str, bearer_token: str | None) -> dict[str, Any]:
    hits = mb_search("artist", f'artist:"{name}"', bearer_token)
    exact = [h for h in hits if h.get("name", "").casefold() == name.casefold()]
    best = exact[0] if exact else (hits[0] if hits else None)
    if not best:
        return {"name": name, "mbid": None, "score": 0, "status": "missing", "candidates": []}
    score = int(best.get("score", 0))
    status = "resolved" if exact and score >= 95 else "review"
    return {"name": name, "mbid": best.get("id"), "score": score, "status": status,
            "candidates": [{"name": h.get("name"), "mbid": h.get("id"), "score": h.get("score"), "disambiguation": h.get("disambiguation")} for h in hits]}


def duplicate_search(title: str, date: str | None, bearer_token: str | None) -> dict[str, Any]:
    q = f'release:"{title}"'
    if date:
        q += f" AND date:{date[:10]}"
    hits = mb_search("release", q, bearer_token)
    return {"found": bool(hits), "candidates": [{"title": h.get("title"), "mbid": h.get("id"), "score": h.get("score"), "date": h.get("date")} for h in hits]}


def normalize_track(track: dict[str, Any], pos: int) -> dict[str, Any]:
    def names(key: str) -> list[str]:
        out = []
        for x in track.get(key) or []:
            out.append(x.get("name") if isinstance(x, dict) else str(x))
        return [x for x in out if x]
    return {
        "position": pos,
        "title": track.get("title"),
        "offset": track.get("offset"),
        "main_artists": names("mainArtists"),
        "featuring_artists": names("featuringArtists"),
        "remix_artists": names("remixArtists"),
    }


def episode_detail(alias: str) -> dict[str, Any]:
    # NTS episode pages negotiate JSON when requested as application/json.
    return get_json(nts_episode_url(alias))


def classify(ep: dict[str, Any], do_mb: bool, bearer_token: str | None) -> dict[str, Any]:
    alias = ep.get("episode_alias") or ep.get("alias")
    detail = episode_detail(alias) if alias else ep
    description = detail.get("description") or ep.get("description") or ""
    credit = extract_credit(description)
    broadcast = detail.get("broadcast") or ep.get("broadcast")
    title = detail.get("name") or ep.get("name") or ""
    tracks = [normalize_track(t, i + 1) for i, t in enumerate(detail.get("tracklist") or [])]
    media = detail.get("media") or ep.get("media") or {}
    artist_resolution = None
    duplicate = None
    blockers: list[str] = []
    warnings: list[str] = []

    if not title:
        blockers.append("missing_title")
    if not broadcast:
        warnings.append("missing_broadcast_date")
    if not tracks:
        warnings.append("missing_tracklist")
    if credit and credit["name"].casefold() != "nts" and do_mb:
        artist_resolution = resolve_artist(credit["name"], bearer_token)
        if artist_resolution["status"] != "resolved":
            blockers.append("artist_credit_requires_review")
    elif credit and credit["name"].casefold() == "nts":
        warnings.append("credit_is_nts_collective")
    else:
        warnings.append("no_explicit_mixer_credit")

    if do_mb and title:
        duplicate = duplicate_search(title, broadcast, bearer_token)
        if duplicate["found"]:
            blockers.append("possible_duplicate_release")

    status = "BLOCKED" if blockers else ("REVIEW" if warnings else "READY")
    return {
        "nts": {
            "show": "NTS Guide to…",
            "episode_alias": alias,
            "url": nts_episode_url(alias) if alias else None,
            "title": title,
            "broadcast": broadcast,
            "location": detail.get("location_short") or ep.get("location_short"),
            "description": description,
            "genres": [g.get("value", g) if isinstance(g, dict) else g for g in (detail.get("genres") or ep.get("genres") or [])],
            "cover_url": media.get("picture_large") or media.get("background_large"),
            "mixcloud": detail.get("mixcloud") or ep.get("mixcloud"),
            "audio_sources": detail.get("audio_sources") or ep.get("audio_sources") or [],
            "tracklist": tracks,
        },
        "credits": [credit] if credit else [],
        "musicbrainz": {
            "release_title": title,
            "release_status": "Official",
            "release_group_secondary_types": ["Broadcast", "DJ-mix"],
            "format": "Digital Media",
            "country": "XW",
            "label": {"name": "NTS Radio", "mbid": NTS_LABEL_MBID},
            "catalog_number": None,
            "barcode": None,
            "artist_credit": artist_resolution,
            "duplicate_release": duplicate,
            "external_urls": [{"url": nts_episode_url(alias), "source": "NTS"}] if alias else [],
        },
        "preflight": {"status": status, "blockers": blockers, "warnings": warnings},
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
    counts = {s: sum(1 for e in episodes if e["preflight"]["status"] == s) for s in ("READY", "REVIEW", "BLOCKED")}
    return {
        "schema": "nts-guide-collector/v2",
        "show_slug": slug,
        "musicbrainz_auth": "bearer" if do_mb and bearer_token else ("anonymous" if do_mb else "disabled"),
        "musicbrainz_transient_errors": len(MB_TRANSIENT_ERRORS),
        "episode_count": len(episodes),
        "status_counts": counts,
        "episodes": episodes,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Collect NTS Guide episodes and prepare MusicBrainz preflight data")
    p.add_argument("--show", default="the-nts-guide-to")
    p.add_argument("--page-size", type=int, default=50)
    p.add_argument("--no-musicbrainz", action="store_true", help="Skip MB artist/duplicate lookups")
    p.add_argument("--mb-token-file", default=".mb_token.json", help="OAuth token JSON used for MusicBrainz requests")
    p.add_argument("--max-episodes", type=int, help="Stop after this many episodes (useful for a smoke test)")
    p.add_argument("-o", "--output", default="nts-guide-inventory.json")
    args = p.parse_args()
    do_mb = not args.no_musicbrainz
    bearer_token = load_mb_access_token(args.mb_token_file) if do_mb else None
    if args.max_episodes is not None and args.max_episodes < 1:
        p.error("--max-episodes must be positive")
    inventory = collect(args.show, args.page_size, do_mb, bearer_token, args.max_episodes)
    Path(args.output).write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "episodes": inventory["episode_count"], **inventory["status_counts"]}, indent=2))


if __name__ == "__main__":
    main()
