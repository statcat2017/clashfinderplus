import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone

import requests

from build_similarity import get_cached_similar_artists, get_similar_artists
from schedule_utils import artist_key, artists_from_schedule, load_json, save_json


SCHEDULE_FILE = "schedule.json"
CACHE_FILE = "listenbrainz_cache.json"
OUTPUT_FILE = "similar_artist_web.json"


def mention_stats(seed_artists, similar_by_mbid, festival_mbids):
    mentions = {}
    mention_counts = Counter()
    listen_counts = Counter()
    mentioned_by = defaultdict(set)

    for seed in seed_artists:
        seed_mbid = seed["musicBrainzId"]
        for item in similar_by_mbid.get(seed_mbid, []):
            mbid = item.get("mbid")
            name = item.get("name")
            if not mbid or not name or mbid in festival_mbids:
                continue
            mentions[mbid] = {"name": name, "musicBrainzId": mbid}
            mention_counts[mbid] += 1
            listen_counts[mbid] += item.get("listenCount", 0)
            mentioned_by[mbid].add(seed["name"])

    ranked = sorted(
        mentions.values(),
        key=lambda artist: (
            -mention_counts[artist["musicBrainzId"]],
            -listen_counts[artist["musicBrainzId"]],
            artist["name"].casefold(),
        ),
    )

    for artist in ranked:
        mbid = artist["musicBrainzId"]
        artist["festivalMentionCount"] = mention_counts[mbid]
        artist["listenCountTotal"] = listen_counts[mbid]
        artist["mentionedByFestivalArtists"] = sorted(mentioned_by[mbid])
    return ranked


def build_web(festival_artists, external_artists, similar_by_mbid):
    node_by_mbid = {}
    festival_mbids = {artist["musicBrainzId"] for artist in festival_artists if artist.get("musicBrainzId")}
    expanded_mbids = {artist["musicBrainzId"] for artist in external_artists}

    for artist in festival_artists:
        mbid = artist.get("musicBrainzId")
        if not mbid:
            continue
        node_by_mbid[mbid] = {
            "id": mbid,
            "name": artist["name"],
            "key": artist_key(artist["name"]),
            "kind": "festival",
            "actIds": artist["actIds"],
        }

    for artist in external_artists:
        mbid = artist["musicBrainzId"]
        node_by_mbid.setdefault(
            mbid,
            {
                "id": mbid,
                "name": artist["name"],
                "key": artist_key(artist["name"]),
                "kind": "expanded-external",
                "festivalMentionCount": artist["festivalMentionCount"],
                "listenCountTotal": artist["listenCountTotal"],
                "mentionedByFestivalArtists": artist["mentionedByFestivalArtists"],
            },
        )

    edge_scores = {}
    edge_sources = defaultdict(set)
    for source_mbid, similar in similar_by_mbid.items():
        if source_mbid not in festival_mbids and source_mbid not in expanded_mbids:
            continue
        for rank, item in enumerate(similar):
            target_mbid = item.get("mbid")
            name = item.get("name")
            if not target_mbid or not name or target_mbid == source_mbid:
                continue

            node_by_mbid.setdefault(
                target_mbid,
                {
                    "id": target_mbid,
                    "name": name,
                    "key": artist_key(name),
                    "kind": "external",
                },
            )

            pair = tuple(sorted((source_mbid, target_mbid)))
            score = max(0, 1 - (rank / max(len(similar), 1)))
            edge_scores[pair] = max(edge_scores.get(pair, 0), score)
            edge_sources[pair].add(source_mbid)

    edges = [
        {
            "source": source,
            "target": target,
            "sourceName": node_by_mbid[source]["name"],
            "targetName": node_by_mbid[target]["name"],
            "score": round(score, 6),
            "sourceKinds": sorted({node_by_mbid[mbid]["kind"] for mbid in edge_sources[(source, target)]}),
        }
        for (source, target), score in edge_scores.items()
        if source in node_by_mbid and target in node_by_mbid
    ]

    return {
        "generatedAt": datetime.now(tz=timezone.utc).isoformat(),
        "summary": {
            "festivalArtists": len(festival_artists),
            "expandedExternalArtists": len(external_artists),
            "nodes": len(node_by_mbid),
            "edges": len(edges),
        },
        "nodes": sorted(node_by_mbid.values(), key=lambda node: (node["kind"], node["name"].casefold())),
        "edges": sorted(edges, key=lambda edge: edge["score"], reverse=True),
    }


def main():
    parser = argparse.ArgumentParser(description="Expand ListenBrainz results into a wider similar-artist web.")
    parser.add_argument("-s", "--schedule", default=SCHEDULE_FILE)
    parser.add_argument("-o", "--output", default=OUTPUT_FILE)
    parser.add_argument("--cache", default=CACHE_FILE)
    parser.add_argument("--max-similar-artists", type=int, default=100)
    parser.add_argument(
        "--external-limit",
        type=int,
        help="Limit expanded non-festival artists. Omit to expand every direct non-festival mention.",
    )
    parser.add_argument("--festival-limit", type=int)
    parser.add_argument("--skip-fetch", action="store_true")
    args = parser.parse_args()

    schedule = load_json(args.schedule, {})
    cache = load_json(args.cache, {})
    festival_artists = [artist for artist in artists_from_schedule(schedule) if artist.get("musicBrainzId")]
    if args.festival_limit:
        festival_artists = festival_artists[: args.festival_limit]

    similar_by_mbid = {}
    for index, artist in enumerate(festival_artists, start=1):
        similar = fetch_or_read_similar(artist, cache, args.max_similar_artists, args.skip_fetch)
        similar_by_mbid[artist["musicBrainzId"]] = similar
        save_json(args.cache, cache)
        print(f"[festival {index}/{len(festival_artists)}] {artist['name']}: {len(similar)} similar artists")

    festival_mbids = {artist["musicBrainzId"] for artist in festival_artists}
    external_artists = mention_stats(festival_artists, similar_by_mbid, festival_mbids)
    if args.external_limit:
        external_artists = external_artists[: args.external_limit]

    for index, artist in enumerate(external_artists, start=1):
        similar = fetch_or_read_similar(artist, cache, args.max_similar_artists, args.skip_fetch)
        similar_by_mbid[artist["musicBrainzId"]] = similar
        save_json(args.cache, cache)
        print(
            f"[external {index}/{len(external_artists)}] {artist['name']} "
            f"({artist['festivalMentionCount']} mentions): {len(similar)} similar artists"
        )

    web = build_web(festival_artists, external_artists, similar_by_mbid)
    save_json(args.output, web)
    save_json(args.cache, cache)
    print(
        f"Wrote {web['summary']['nodes']} nodes and {web['summary']['edges']} edges "
        f"to {args.output}"
    )


def fetch_or_read_similar(artist, cache, max_similar_artists, skip_fetch):
    if skip_fetch:
        return get_cached_similar_artists(artist, cache, max_similar_artists)
    try:
        return get_similar_artists(artist, cache, max_similar_artists)
    except requests.RequestException as error:
        print(f"{artist['name']}: {error}")
        return []


if __name__ == "__main__":
    main()
