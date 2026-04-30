# ClashFinderPlus

A small, local-first festival clashfinder built from Clashfinder schedule data.

## Getting Started

Create or refresh the schedule JSON:

```sh
.venv/bin/python scrape_lineup.py -o schedule.json
```

Create or refresh artist genre metadata:

```sh
.venv/bin/python enrich_genres.py -o artist_genres.json
```

The genre enricher uses MusicBrainz IDs from the schedule first, then Wikidata/Wikipedia links when it can do so without guessing. Spotify can be added with `--spotify` if `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are set.

Build the ListenBrainz similarity graph:

```sh
.venv/bin/python build_similarity.py -o similarity_graph.json
```

This fetches up to 100 similar artists per festival artist with a MusicBrainz ID, caches the raw ListenBrainz responses in `listenbrainz_cache.json`, and writes festival-to-festival similarity edges to `similarity_graph.json`.

Expand the wider similar-artist web:

```sh
.venv/bin/python build_similarity_web.py -o similar_artist_web.json
```

This counts every non-festival artist directly mentioned as similar to a festival act, fetches those artists' own ListenBrainz neighbourhoods, and writes a larger artist web to `similar_artist_web.json`. Use `--external-limit 100` for a faster sample run.

Run the local website:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open <http://127.0.0.1:8000/>.

## Usage

The page includes day tabs, stage filtering, act search, local must-see starring, and a simple starred clash counter.

## License

[Add license information here]
