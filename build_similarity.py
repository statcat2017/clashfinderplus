import argparse
import time
from collections import Counter
from datetime import datetime, timezone

import requests

from schedule_utils import artist_key, artists_from_schedule, load_json, save_json


SCHEDULE_FILE = "schedule.json"
GENRES_FILE = "artist_genres.json"
WEB_FILE = "similar_artist_web.json"
OUTPUT_FILE = "similarity_graph.json"
CACHE_FILE = "listenbrainz_cache.json"
APP_NAME = "ClashFinderPlus/0.1 ( https://github.com/local/clashfinderplus )"


def fetch_json(url, params):
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, headers={"User-Agent": APP_NAME}, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            last_error = error
            if attempt < 2:
                time.sleep(1 + attempt)
    raise last_error


def get_similar_artists(artist, cache, max_similar_artists):
    mbid = artist.get("musicBrainzId")
    if not mbid:
        return []

    cache_key = f"lb-radio:{mbid}:easy:{max_similar_artists}:1:0:100"
    if cache_key not in cache:
        data = fetch_json(
            f"https://api.listenbrainz.org/1/lb-radio/artist/{mbid}",
            {
                "mode": "easy",
                "max_similar_artists": max_similar_artists,
                "max_recordings_per_artist": 1,
                "pop_begin": 0,
                "pop_end": 100,
            },
        )
        cache[cache_key] = data
        time.sleep(0.2)

    similar = []
    for similar_mbid, rows in cache[cache_key].items():
        if not rows:
            continue
        row = rows[0]
        similar.append(
            {
                "mbid": similar_mbid,
                "name": row.get("similar_artist_name"),
                "listenCount": int(row.get("total_listen_count") or 0),
            }
        )
    return similar


def load_genres(path):
    data = load_json(path, {"artists": []})
    return {artist_key(artist["name"]): set(artist.get("genres", [])) for artist in data.get("artists", [])}


def jaccard(first, second):
    if not first or not second:
        return 0
    union = first | second
    if not union:
        return 0
    return len(first & second) / len(union)


def build_graph(schedule, genre_data, similar_by_key, web_data=None, artist_limit=None):
    artists = artists_from_schedule(schedule)
    if artist_limit:
        artists = artists[:artist_limit]
    by_key = {artist_key(artist["name"]): artist for artist in artists}
    mbid_to_key = {
        artist["musicBrainzId"]: key
        for key, artist in by_key.items()
        if artist.get("musicBrainzId")
    }

    listenbrainz_sets = {
        key: {item["mbid"] for item in similar if item.get("mbid")}
        for key, similar in similar_by_key.items()
    }
    direct_edges = {}
    for source_key, similar in similar_by_key.items():
        for index, item in enumerate(similar):
            target_key = mbid_to_key.get(item["mbid"])
            if not target_key or target_key == source_key:
                continue
            pair = tuple(sorted((source_key, target_key)))
            direct_edges[pair] = max(direct_edges.get(pair, 0), max(0, 1 - (index / max(len(similar), 1))))

    bridge_scores, bridge_names = external_bridge_scores(web_data or {}, by_key)

    edges = []
    for index, source in enumerate(artists):
        source_key = artist_key(source["name"])
        for target in artists[index + 1 :]:
            target_key = artist_key(target["name"])
            pair = tuple(sorted((source_key, target_key)))

            direct_score = direct_edges.get(pair, 0)
            shared_lb_score = jaccard(listenbrainz_sets.get(source_key, set()), listenbrainz_sets.get(target_key, set()))
            genre_score = jaccard(genre_data.get(source_key, set()), genre_data.get(target_key, set()))
            bridge_score = bridge_scores.get(pair, 0)
            score = (0.45 * direct_score) + (0.25 * shared_lb_score) + (0.20 * bridge_score) + (0.10 * genre_score)

            if score <= 0:
                continue

            edges.append(
                {
                    "source": source["name"],
                    "target": target["name"],
                    "sourceKey": source_key,
                    "targetKey": target_key,
                    "score": round(score, 6),
                    "signals": {
                        "directListenBrainz": round(direct_score, 6),
                        "sharedListenBrainz": round(shared_lb_score, 6),
                        "externalBridge": round(bridge_score, 6),
                        "genre": round(genre_score, 6),
                    },
                    "sharedSimilarArtists": shared_similar_names(
                        similar_by_key.get(source_key, []),
                        similar_by_key.get(target_key, []),
                    )[:12],
                    "externalBridgeArtists": bridge_names.get(pair, [])[:12],
                    "sharedGenres": sorted(genre_data.get(source_key, set()) & genre_data.get(target_key, set())),
                }
            )

    return {
        "generatedAt": datetime.now(tz=timezone.utc).isoformat(),
        "artists": [
            {
                "name": artist["name"],
                "key": artist_key(artist["name"]),
                "musicBrainzId": artist.get("musicBrainzId"),
                "actIds": artist["actIds"],
                "genres": sorted(genre_data.get(artist_key(artist["name"]), set())),
                "similarArtistCount": len(similar_by_key.get(artist_key(artist["name"]), [])),
            }
            for artist in artists
        ],
        "edges": sorted(edges, key=lambda edge: edge["score"], reverse=True),
    }


def shared_similar_names(first, second):
    first_by_mbid = {item["mbid"]: item["name"] for item in first if item.get("mbid")}
    second_mbids = {item["mbid"] for item in second if item.get("mbid")}
    return sorted(name for mbid, name in first_by_mbid.items() if mbid in second_mbids and name)


def external_bridge_scores(web_data, festival_by_key):
    nodes = {node["id"]: node for node in web_data.get("nodes", [])}
    festival_names = {artist["name"]: key for key, artist in festival_by_key.items()}
    external_to_festival = {}

    for edge in web_data.get("edges", []):
        source = nodes.get(edge["source"])
        target = nodes.get(edge["target"])
        if not source or not target:
            continue

        if source.get("kind") == "festival" and target.get("kind") != "festival":
            festival_name = source["name"]
            external = target
        elif target.get("kind") == "festival" and source.get("kind") != "festival":
            festival_name = target["name"]
            external = source
        else:
            continue

        festival_key = festival_names.get(festival_name)
        if not festival_key:
            continue
        external_to_festival.setdefault(external["id"], []).append(
            {
                "festivalKey": festival_key,
                "externalName": external["name"],
                "score": edge.get("score", 0),
            }
        )

    raw_scores = {}
    bridge_names = {}
    for connections in external_to_festival.values():
        if len(connections) < 2:
            continue
        for index, first in enumerate(connections):
            for second in connections[index + 1 :]:
                if first["festivalKey"] == second["festivalKey"]:
                    continue
                pair = tuple(sorted((first["festivalKey"], second["festivalKey"])))
                weight = min(first["score"], second["score"])
                raw_scores[pair] = raw_scores.get(pair, 0) + weight
                bridge_names.setdefault(pair, []).append((first["externalName"], weight))

    scores = {pair: min(raw / 6, 1) for pair, raw in raw_scores.items()}
    names = {
        pair: [
            name
            for name, _ in sorted(
                dedupe_weighted_bridges(weighted_names).items(),
                key=lambda item: (-item[1], item[0].casefold()),
            )
        ]
        for pair, weighted_names in bridge_names.items()
    }
    return scores, names


def dedupe_weighted_bridges(weighted_names):
    totals = {}
    for name, weight in weighted_names:
        totals[name] = max(totals.get(name, 0), weight)
    return totals


def main():
    parser = argparse.ArgumentParser(description="Build a festival artist similarity graph.")
    parser.add_argument("-s", "--schedule", default=SCHEDULE_FILE)
    parser.add_argument("-g", "--genres", default=GENRES_FILE)
    parser.add_argument("-w", "--web", default=WEB_FILE)
    parser.add_argument("-o", "--output", default=OUTPUT_FILE)
    parser.add_argument("--cache", default=CACHE_FILE)
    parser.add_argument("--limit", type=int, help="Limit artists fetched from ListenBrainz")
    parser.add_argument("--max-similar-artists", type=int, default=100)
    parser.add_argument("--skip-fetch", action="store_true", help="Build from existing cache only")
    args = parser.parse_args()

    schedule = load_json(args.schedule, {})
    cache = load_json(args.cache, {})
    genres = load_genres(args.genres)
    web = load_json(args.web, {})
    artists = artists_from_schedule(schedule)
    fetchable = [artist for artist in artists if artist.get("musicBrainzId")]
    if args.limit:
        fetchable = fetchable[: args.limit]

    similar_by_key = {}
    for index, artist in enumerate(fetchable, start=1):
        if args.skip_fetch:
            similar = get_cached_similar_artists(artist, cache, args.max_similar_artists)
        else:
            try:
                similar = get_similar_artists(artist, cache, args.max_similar_artists)
            except requests.RequestException as error:
                print(f"[{index}/{len(fetchable)}] {artist['name']}: {error}")
                similar = []
            save_json(args.cache, cache)
        similar_by_key[artist_key(artist["name"])] = similar
        print(f"[{index}/{len(fetchable)}] {artist['name']}: {len(similar)} similar artists")

    graph = build_graph(schedule, genres, similar_by_key, web_data=web, artist_limit=args.limit)
    save_json(args.output, graph)
    save_json(args.cache, cache)
    print(f"Wrote {len(graph['edges'])} similarity edges to {args.output}")


def get_cached_similar_artists(artist, cache, max_similar_artists):
    mbid = artist.get("musicBrainzId")
    cache_key = f"lb-radio:{mbid}:easy:{max_similar_artists}:1:0:100"
    if cache_key not in cache:
        return []
    similar = []
    for similar_mbid, rows in cache[cache_key].items():
        if rows:
            similar.append(
                {
                    "mbid": similar_mbid,
                    "name": rows[0].get("similar_artist_name"),
                    "listenCount": int(rows[0].get("total_listen_count") or 0),
                }
            )
    return similar


if __name__ == "__main__":
    main()
