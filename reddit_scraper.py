import json
import time
import random
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# =========================
# CONFIG
# =========================
FIREFOX_PROFILE_DIR = Path("./firefox_profile")


# =========================
# HELPERS
# =========================

def get_title(html):
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)

    t = soup.title
    return t.get_text(strip=True) if t else "No title"


def safe_goto(page, url):
    for attempt in range(1, 4):
        try:
            print(f"🌐 Loading ({attempt}/3): {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1500)
            return True
        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed: {e}")
            time.sleep(random.uniform(1.5, 3.5))

    print(f"❌ Failed: {url}")
    return False


def extract_soundgasm_links(html):
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):
        if "soundgasm.net" in a["href"]:
            links.append(a["href"])

    import re
    links += re.findall(
        r"https?://(?:www\.)?soundgasm\.net[^\s'\"<>]+",
        soup.get_text("\n")
    )

    # dedupe
    seen = set()
    return [x for x in links if not (x in seen or seen.add(x))]


# =========================
# MAIN
# =========================

def main():
    project_folder = Path(__file__).parent
    input_file = project_folder / "gwasi.json"
    output_file = project_folder / "reddit.json"

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

        print(f"📌 Total posts: {len(items)}")

        for idx, i in enumerate(items, 1):

            print("\n==============================")
            print(f"[{idx}/{len(items)}] Processing post")

            url = i["url"]

            if not safe_goto(page, url):
                continue

            title = get_title(page.content())

            # ✅ REVERTED: use gwasi date (most stable source)
            date = i.get("date")

            print(f"📝 Title: {title}")
            print(f"📅 Date (gwasi): {date}")
            print(f"📊 Score: {i.get('score')}")

            soundgasm_links = extract_soundgasm_links(page.content())

            if soundgasm_links:
                print(f"🎧 Found {len(soundgasm_links)} Soundgasm link(s):")
                for s in soundgasm_links:
                    print(f"   - {s}")
            else:
                print("❌ No Soundgasm links found")

            results.append({
                "url": url,
                "title": title,
                "date": date,   # ✅ stable again
                "score": i.get("score"),
                "soundgasm": soundgasm_links
            })

            time.sleep(random.uniform(1.5, 4.0))

        context.close()

    print(f"\n💾 Saving to: {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("✅ Done!")


if __name__ == "__main__":
    main()