import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from email.utils import formatdate
from urllib.parse import unquote, urlparse
import re
import sys
import requests
from utils import format_score

LOCAL_OFFSET_HOURS = 0

# -----------------------------
# GET FILE SIZE
# -----------------------------
def get_file_size(url: str) -> str:
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        size = r.headers.get("Content-Length")
        return size if size else "0"
    except Exception:
        return "0"


# -----------------------------
# PARSE GWASI LINK
# -----------------------------
def parse_gwasi_link(link: str):
    parsed = urlparse(link)
    fragment = unquote(parsed.fragment)

    user_match = re.search(r"u:(\S+)", fragment)
    score_match = re.search(r"score:>(\d+)", fragment)

    username = user_match.group(1) if user_match else "Unknown"
    min_score = int(score_match.group(1)) if score_match else 0

    return username, min_score


# -----------------------------
# PARSE DATE TO RFC 2822
# -----------------------------
def parse_rfc2822_date(date_str: str):
    if not date_str:
        return formatdate()

    try:
        dt = datetime.fromisoformat(date_str)
        dt += timedelta(hours=LOCAL_OFFSET_HOURS)
        return formatdate(dt.timestamp())
    except Exception:
        return formatdate()


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def main():
    project_folder = Path(__file__).parent

    if len(sys.argv) < 2:
        print("Usage: python rss_builder.py <gwasi_url_or_json>")
        sys.exit(1)

    arg = sys.argv[1]

    # Determine input file
    if Path(arg).is_file():
        input_file = Path(arg)
        username = "GWA"
        min_score = 3000
    else:
        input_file = project_folder / "final.json"
        username, min_score = parse_gwasi_link(arg)

    output_file = project_folder / "GWA.xml"

    print(f"ℹ️ Feed: GWA | 3000+ upvotes")
    print(f"💾 Output: {output_file}")

    # Load input JSON
    with open(input_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    # -----------------------------
    # CREATE RSS XML
    # -----------------------------
    rss = ET.Element(
        "rss",
        version="2.0",
        attrib={
            "xmlns:itunes":
            "http://www.itunes.com/dtds/podcast-1.0.dtd"
        }
    )

    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "GWA"

    ET.SubElement(channel, "description").text = (
        "Feed with posts over 3000 upvotes"
    )

    ET.SubElement(
        channel,
        "{http://www.itunes.com/dtds/podcast-1.0.dtd}image",
        {"href": "https://raw.githubusercontent.com/drehfrejbfhjerfr/M/refs/heads/main/Project/photo.jpg"}
    )

    # -----------------------------
    # LOOP THROUGH POSTS
    # -----------------------------
    for ep in items:

        title = ep.get("title", "No title")
        score = ep.get("score", 0)
        author = ep.get("author", "Unknown")

        audios = ep.get("audio")

        if not audios:
            continue

        if isinstance(audios, str):
            audios = [audios]

        if isinstance(audios, dict):
            audios = [audios]

        pub_date = parse_rfc2822_date(ep.get("date"))

        score_text = format_score(score) or "0"

        for idx, audio_obj in enumerate(audios, 1):

            audio_url = (
                audio_obj.get("url")
                if isinstance(audio_obj, dict)
                else audio_obj
            )

            duration = (
                audio_obj.get("duration")
                if isinstance(audio_obj, dict)
                else None
            )

            if not audio_url:
                continue

            file_size = get_file_size(audio_url)

            item = ET.SubElement(channel, "item")

            # Episode title
            if len(audios) > 1:
                episode_title = (
                    f"{score_text} - ({idx}/{len(audios)}) {title}"
                )
            else:
                episode_title = (
                    f"{score_text} - {title}"
                )

            ET.SubElement(item, "title").text = episode_title

            # Description
            ET.SubElement(
                item,
                "description"
            ).text = f"Author: {author}"

            # Podcast apps often display this nicely
            ET.SubElement(
                item,
                "{http://www.itunes.com/dtds/podcast-1.0.dtd}author"
            ).text = author

            ET.SubElement(item, "pubDate").text = pub_date

            ET.SubElement(
                item,
                "enclosure",
                {
                    "url": audio_url,
                    "length": str(file_size),
                    "type": "audio/x-m4a"
                }
            )

            ET.SubElement(
                item,
                "guid",
                {"isPermaLink": "false"}
            ).text = audio_url.split("/")[-1]

            if duration:
                ET.SubElement(
                    item,
                    "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration"
                ).text = duration

    # -----------------------------
    # WRITE XML
    # -----------------------------
    tree = ET.ElementTree(rss)

    ET.indent(tree, space="  ")

    tree.write(
        output_file,
        encoding="utf-8",
        xml_declaration=True
    )

    print(f"✅ RSS generated: {output_file}")


if __name__ == "__main__":
    main()