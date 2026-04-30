import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup as bs


DEFAULT_URL = "https://clashfinder.com/m/2ktrees2026/"
DEFAULT_OUTPUT = "schedule.json"


def clean_text(value):
    return re.sub(r"\s+", " ", value.replace("\u200b", "")).strip()


def load_html(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def parse_timestamp_ms(value):
    if not value:
        return None
    return int(value)


def iso_from_ms(value):
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def parse_clashfinder(html, source_url=DEFAULT_URL):
    soup = bs(html, "html.parser")
    full_list = soup.find(id="fullList")
    if full_list is None:
        raise ValueError("Could not find #fullList in the Clashfinder HTML")

    title = clean_text(soup.find("h1").get_text(" ", strip=True)) if soup.find("h1") else "Clashfinder"
    edit_match = re.search(r"Clashfinder edit date:\s*([0-9: -]+)", soup.get_text(" ", strip=True))

    days = {}
    stages = []
    acts = []

    for stage_index, stage_el in enumerate(full_list.select(".stage")):
        stage_name_el = stage_el.find(class_="stageName")
        if not stage_name_el:
            continue

        stage_id = f"stage-{stage_index + 1}"
        stage = {
            "id": stage_id,
            "name": clean_text(stage_name_el.get_text(" ", strip=True)),
            "order": stage_index,
        }
        stages.append(stage)

        for day_el in stage_el.select(".day"):
            day_name_el = day_el.find(class_="dayName")
            if not day_name_el:
                continue

            day_name = clean_text(day_name_el.get_text(" ", strip=True))
            day_id = re.sub(r"[^a-z0-9]+", "-", day_name.lower()).strip("-")
            if day_id not in days:
                days[day_id] = {
                    "id": day_id,
                    "name": day_name,
                    "date": int(day_el.get("data-date", "0") or 0),
                    "firstStart": int(day_el.get("data-first-start", "0") or 0),
                    "lastStop": int(day_el.get("data-last-stop", "0") or 0),
                }

            for act_el in day_el.select(".act"):
                time_el = act_el.find(class_="actTime")
                name_el = act_el.find(class_="actNm")
                if not time_el or not name_el:
                    continue

                start_ms = parse_timestamp_ms(act_el.get("data-start-time"))
                end_ms = parse_timestamp_ms(act_el.get("data-end-time"))
                act_id = act_el.get("data-id") or f"act-{len(acts) + 1}"

                acts.append(
                    {
                        "id": act_id,
                        "name": clean_text(name_el.get_text(" ", strip=True)),
                        "time": clean_text(time_el.get_text(" ", strip=True)),
                        "stageId": stage_id,
                        "stageName": stage["name"],
                        "dayId": day_id,
                        "dayName": day_name,
                        "startMs": start_ms,
                        "endMs": end_ms,
                        "startIso": iso_from_ms(start_ms),
                        "endIso": iso_from_ms(end_ms),
                        "musicBrainzId": act_el.get("data-mbid"),
                    }
                )

    return {
        "title": title,
        "sourceUrl": source_url,
        "scrapedAt": datetime.now(tz=timezone.utc).isoformat(),
        "editDate": edit_match.group(1) if edit_match else None,
        "days": sorted(days.values(), key=lambda day: day["date"]),
        "stages": stages,
        "acts": acts,
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape a Clashfinder page into schedule JSON.")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL)
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--source-file", help="Parse a saved Clashfinder HTML/text file instead of fetching")
    args = parser.parse_args()

    html = Path(args.source_file).read_text(encoding="utf-8") if args.source_file else load_html(args.url)
    schedule = parse_clashfinder(html, args.url)

    output = Path(args.output)
    output.write_text(json.dumps(schedule, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(schedule['acts'])} acts across {len(schedule['stages'])} stages to {output}")


if __name__ == "__main__":
    main()
