import argparse
import base64
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests


SCHEDULE_FILE = "schedule.json"
OUTPUT_FILE = "artist_genres.json"
CACHE_FILE = "genre_cache.json"
APP_NAME = "ClashFinderPlus/0.1 ( https://github.com/local/clashfinderplus )"


def normalise_name(name):
    return re.sub(r"\s+", " ", name).strip()


def artist_key(name):
    return normalise_name(name).casefold()


def load_json(path, default):
    file_path = Path(path)
    if not file_path.exists():
        return default
    return json.loads(file_path.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def request_json(url, headers=None, params=None, method="get", data=None, timeout=30):
    response = requests.request(method, url, headers=headers, params=params, data=data, timeout=timeout)
    response.raise_for_status()
    return response.json()


class GenreEnricher:
    def __init__(self, cache, use_spotify=False, guess_names=False):
        self.cache = cache
        self.use_spotify = use_spotify
        self.guess_names = guess_names
        self.spotify_token = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": APP_NAME})

    def enrich_artist(self, artist):
        name = artist["name"]
        mbid = artist.get("musicBrainzId")

        genres = Counter()
        sources = []
        wikidata_id = None
        wikipedia_url = None
        spotify_id = None

        if mbid:
            musicbrainz = self.musicbrainz_lookup(mbid)
            wikidata_id = musicbrainz.get("wikidataId")
            add_weighted(genres, musicbrainz.get("genres", []), 4)
            add_weighted(genres, musicbrainz.get("tags", []), 1)
            if musicbrainz.get("genres") or musicbrainz.get("tags"):
                sources.append("musicbrainz")

        if mbid or wikidata_id or self.guess_names:
            wikidata = self.wikidata_lookup(name, mbid, wikidata_id)
            add_weighted(genres, wikidata.get("genres", []), 5)
            wikidata_id = wikidata.get("wikidataId") or wikidata_id
            wikipedia_url = wikidata.get("wikipediaUrl")
            if wikidata.get("genres"):
                sources.append("wikidata")
            if wikipedia_url:
                sources.append("wikipedia")

        if self.use_spotify:
            spotify = self.spotify_lookup(name)
            spotify_id = spotify.get("spotifyId")
            add_weighted(genres, spotify.get("genres", []), 3)
            if spotify.get("genres"):
                sources.append("spotify")

        ranked_genres = [genre for genre, _ in genres.most_common(8)]
        return {
            "name": name,
            "musicBrainzId": mbid,
            "wikidataId": wikidata_id,
            "wikipediaUrl": wikipedia_url,
            "spotifyId": spotify_id,
            "genres": ranked_genres,
            "sources": sorted(set(sources)),
        }

    def musicbrainz_lookup(self, mbid):
        cache_key = f"musicbrainz:{mbid}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        url = f"https://musicbrainz.org/ws/2/artist/{quote(mbid)}"
        data = request_json(url, params={"inc": "genres+tags+url-rels", "fmt": "json"})
        time.sleep(1.05)

        genres = extract_weighted_names(data.get("genres", []))
        tags = extract_weighted_names(data.get("tags", []), minimum_count=2)
        wikidata_id = None
        for relation in data.get("relations", []):
            resource = relation.get("url", {}).get("resource", "")
            if "wikidata.org/wiki/" in resource:
                wikidata_id = resource.rsplit("/", 1)[-1]
                break

        result = {
            "genres": genres,
            "tags": tags,
            "wikidataId": wikidata_id,
        }
        self.cache[cache_key] = result
        return result

    def wikidata_lookup(self, name, mbid=None, wikidata_id=None):
        cache_key = f"wikidata:{wikidata_id or mbid or artist_key(name)}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if wikidata_id:
            values = f"VALUES ?artist {{ wd:{wikidata_id} }}"
        elif mbid:
            values = f'?artist wdt:P434 "{mbid}" .'
        else:
            safe_name = name.replace('"', '\\"')
            values = f"""
            ?artist rdfs:label "{safe_name}"@en .
            {{
              ?artist wdt:P31/wdt:P279* wd:Q215380 .
            }} UNION {{
              ?artist wdt:P106/wdt:P279* wd:Q639669 .
            }}
            """

        query = f"""
        SELECT ?artist ?artistLabel ?genreLabel ?article WHERE {{
          {values}
          OPTIONAL {{ ?artist wdt:P136 ?genre. }}
          OPTIONAL {{
            ?article schema:about ?artist;
                     schema:isPartOf <https://en.wikipedia.org/>.
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 20
        """
        data = request_json(
            "https://query.wikidata.org/sparql",
            headers={"Accept": "application/sparql-results+json", "User-Agent": APP_NAME},
            params={"query": query, "format": "json"},
        )
        time.sleep(0.2)

        genres = []
        wikipedia_url = None
        found_wikidata_id = wikidata_id
        for row in data.get("results", {}).get("bindings", []):
            artist_url = row.get("artist", {}).get("value", "")
            if artist_url:
                found_wikidata_id = artist_url.rsplit("/", 1)[-1]
            genre = row.get("genreLabel", {}).get("value")
            if genre:
                genres.append(genre)
            wikipedia_url = wikipedia_url or row.get("article", {}).get("value")

        result = {
            "genres": unique(genres),
            "wikidataId": found_wikidata_id,
            "wikipediaUrl": wikipedia_url,
        }
        self.cache[cache_key] = result
        return result

    def spotify_lookup(self, name):
        cache_key = f"spotify:{artist_key(name)}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        token = self.get_spotify_token()
        if not token:
            return {"genres": [], "spotifyId": None}

        search = request_json(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": name, "type": "artist", "limit": 1},
        )
        items = search.get("artists", {}).get("items", [])
        if not items:
            result = {"genres": [], "spotifyId": None}
        else:
            artist = items[0]
            result = {
                "genres": unique(artist.get("genres", [])),
                "spotifyId": artist.get("id"),
            }

        self.cache[cache_key] = result
        return result

    def get_spotify_token(self):
        if self.spotify_token:
            return self.spotify_token

        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            return None

        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        data = request_json(
            "https://accounts.spotify.com/api/token",
            method="post",
            data={"grant_type": "client_credentials"},
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": APP_NAME,
            },
            timeout=15,
        )
        self.spotify_token = data.get("access_token")
        return self.spotify_token


def extract_weighted_names(items, minimum_count=0):
    ranked = sorted(
        (
            (item.get("name"), int(item.get("count") or 0))
            for item in items
            if item.get("name") and int(item.get("count") or 0) >= minimum_count
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return [name for name, _ in ranked]


def add_weighted(counter, values, weight):
    for value in values:
        cleaned = normalise_name(value).lower()
        if cleaned:
            counter[cleaned] += weight


def unique(values):
    seen = set()
    result = []
    for value in values:
        cleaned = normalise_name(value).lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def artists_from_schedule(schedule):
    artists = {}
    for act in schedule.get("acts", []):
        name = normalise_name(act.get("name", ""))
        if not name or name.casefold() == "tbc":
            continue

        key = artist_key(name)
        current = artists.setdefault(
            key,
            {
                "name": name,
                "musicBrainzId": None,
                "actIds": [],
            },
        )
        current["actIds"].append(act.get("id"))
        current["musicBrainzId"] = current["musicBrainzId"] or act.get("musicBrainzId")
    return sorted(artists.values(), key=lambda artist: artist["name"].casefold())


def main():
    parser = argparse.ArgumentParser(description="Enrich schedule artists with genre metadata.")
    parser.add_argument("-s", "--schedule", default=SCHEDULE_FILE)
    parser.add_argument("-o", "--output", default=OUTPUT_FILE)
    parser.add_argument("--cache", default=CACHE_FILE)
    parser.add_argument("--limit", type=int, help="Limit artists processed, useful while testing")
    parser.add_argument("--spotify", action="store_true", help="Also query Spotify if credentials are present")
    parser.add_argument(
        "--guess-names",
        action="store_true",
        help="Try Wikidata exact-label lookups for artists without MusicBrainz IDs",
    )
    args = parser.parse_args()

    schedule = load_json(args.schedule, {})
    cache = load_json(args.cache, {})
    artists = artists_from_schedule(schedule)
    if args.limit:
        artists = artists[: args.limit]

    enricher = GenreEnricher(cache, use_spotify=args.spotify, guess_names=args.guess_names)
    enriched = []
    for index, artist in enumerate(artists, start=1):
        try:
            result = enricher.enrich_artist(artist)
        except requests.HTTPError as error:
            result = {
                "name": artist["name"],
                "musicBrainzId": artist.get("musicBrainzId"),
                "genres": [],
                "sources": [],
                "error": str(error),
            }
        result["actIds"] = artist["actIds"]
        enriched.append(result)
        print(f"[{index}/{len(artists)}] {result['name']}: {', '.join(result['genres']) or 'no genres'}")
        save_json(args.cache, cache)

    output = {
        "generatedAt": datetime.now(tz=timezone.utc).isoformat(),
        "schedule": args.schedule,
        "artists": enriched,
    }
    save_json(args.output, output)
    save_json(args.cache, cache)
    print(f"Wrote genre metadata for {len(enriched)} artists to {args.output}")


if __name__ == "__main__":
    main()
