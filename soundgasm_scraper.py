import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# =========================
# PERSISTENT PROFILE
# =========================

FIREFOX_PROFILE_DIR = Path("./firefox_profile")


def extract_audio(html):
    """Extract audio URL, duration and Soundgasm author."""
    soup = BeautifulSoup(html, "html.parser")

    # Audio URL
    m = re.search(
        r"https://media\.soundgasm\.net/sounds/[^\s'\"<>]+\.m4a",
        html
    )
    audio_url = m.group(0) if m else None

    # Duration
    duration_div = soup.find("div", class_="jp-duration")
    duration = (
        duration_div.get_text(strip=True).lstrip("-")
        if duration_div else None
    )

    # Author
    author = None

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if re.search(r"soundgasm\.net/u/[^/]+/?$", href):
            author = a.get_text(strip=True)
            break

    return audio_url, duration, author


def safe_goto(page, url):
    """Navigate safely to a URL with retry."""
    try:
        print(f"🌐 Loading Soundgasm: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)

    except Exception as e:
        print(f"⚠️ Retry needed ({e})")

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(1500)


def main():

    project_folder = Path(__file__).parent
    input_file = project_folder / "reddit.json"
    output_file = project_folder / "final.json"

    print(f"📂 Loading input: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    results = []

    print("\n🚀 Starting Firefox (persistent profile)...")

    with sync_playwright() as p:

        context = p.firefox.launch_persistent_context(
            user_data_dir=str(FIREFOX_PROFILE_DIR),
            headless=False
        )

        page = context.pages[0] if context.pages else context.new_page()

        print(f"📌 Total items: {len(items)}\n")

        for idx, i in enumerate(items, 1):

            print("\n==============================")
            print(f"[{idx}/{len(items)}] Processing item")

            soundgasm_links = i.get("soundgasm", [])

            if not soundgasm_links:
                print("❌ No soundgasm links → skipping")
                continue

            print(f"🔗 Post: {i.get('url')}")
            print(f"📝 Title: {i.get('title')}")
            print(f"📅 Date: {i.get('date')}")
            print(f"📊 Score: {i.get('score')}")
            print(f"🎧 Found {len(soundgasm_links)} soundgasm link(s)")

            # Create a single post object to group all audios
            post = {
                "url": i.get("url"),
                "title": i.get("title"),
                "date": i.get("date"),
                "score": i.get("score"),
                "author": None,
                "audio": []
            }

            for sg_idx, sg_url in enumerate(soundgasm_links, 1):

                print(f"\n   ▶ Audio source {sg_idx}/{len(soundgasm_links)}")

                safe_goto(page, sg_url)

                audio_url, duration, author = extract_audio(
                    page.content()
                )

                if author and not post["author"]:
                    post["author"] = author

                if audio_url and not any(
                    a["url"] == audio_url
                    for a in post["audio"]
                ):

                    print(
                        f"   🎧 Audio found: "
                        f"{audio_url} "
                        f"({duration})"
                    )

                    if author:
                        print(f"   👤 Author: {author}")

                    post["audio"].append({
                        "url": audio_url,
                        "duration": duration,
                        "author": author
                    })

                else:
                    print("   ❌ No audio found")

            if post["audio"]:
                results.append(post)
            else:
                print(
                    "❌ No audios found for this post "
                    "→ skipping"
                )

        context.close()

    print(f"\n💾 Saving results to: {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("✅ Done!")


if __name__ == "__main__":
    main()