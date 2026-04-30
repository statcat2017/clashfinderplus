import json
import re
from pathlib import Path


def normalise_name(name):
    return re.sub(r"\s+", " ", name or "").strip()


def artist_key(name):
    return normalise_name(name).casefold()


def load_json(path, default):
    file_path = Path(path)
    if not file_path.exists():
        return default
    return json.loads(file_path.read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
