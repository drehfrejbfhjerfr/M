import sys
import json
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from utils import scroll
import re

# =========================
# PERSISTENT PROFILE
# =========================

FIREFOX_PROFILE_DIR = Path("./firefox_profile")


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    import re

    for a in soup.find_all("a", href=True):

        if "/r/gonewildaudio/comments/" not in a["href"]:
            continue

        # 🔥 THIS is the real container in your HTML
        li = a.find("li")
        if not li:
            continue

        text = li.get_text(" ", strip=True)

        # --------------------
        # DATE
        # --------------------
        date = None
        d = re.search(r"\d{4}-\d{2}-\d{2}", text)
        if d:
            date = d.group(0)

        # --------------------
        # SCORE
        # --------------------
        score = None
        s = re.search(r"GWA\s+(\d+)", text)
        if s:
            score = int(s.group(1))

        results.append({
            "url": a["href"],
            "date": date,
            "score": score
        })

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: script <gwasi_url>")
        return

    url = sys.argv[1]

    with sync_playwright() as p:

        print("\n🚀 Starting Firefox (persistent profile)...")

        context = p.firefox.launch_persistent_context(
            user_data_dir=str(FIREFOX_PROFILE_DIR),
            headless=False
        )

        page = context.pages[0] if context.pages else context.new_page()

        print(f"🔎 Loading gwasi page:\n{url}")
        page.goto(url, wait_until="networkidle")

        print("📜 Scrolling to load more posts...")
        scroll(page)

        print("🧠 Parsing page content...")
        data = parse(page.content())

        print(f"📌 Found {len(data)} entries")

        for i, item in enumerate(data[:10], 1):
            print("\n------------------------------")
            print(f"[{i}] {item['url']}")
            print(f"📅 {item['date']}")
            print(f"📊 {item['score']}")

        context.close()

        project_folder = Path(__file__).parent
        output_file = project_folder / "gwasi.json"

        print(f"\n💾 Saving to {output_file} ...")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print("✅ Done!")


if __name__ == "__main__":
    main()