import re
from bs4 import BeautifulSoup

SOUNDGASM_RE = re.compile(r"(https?://(?:www\.)?soundgasm\.net[^\s'\"<>)]*)", re.I)


def scroll(page, max_scrolls=500):
    """
    Scrolls to the bottom of the page, waiting for lazy-loaded content.

    Args:
        page: Playwright page object
        pause: Seconds to wait after each scroll
        max_scrolls: Maximum number of scroll attempts
    """
    last_height = 0
    for i in range(max_scrolls):
        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(100)

        # Get new height
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            print(f"🛑 Reached bottom after {i+1} scrolls")
            break
        last_height = new_height
    else:
        print(f"⚠️ Max scrolls ({max_scrolls}) reached")


def format_score(n):
    if not n:
        return None
    if n >= 10000:
        return f"{n//1000}K"
    if n >= 1000:
        return f"{n/1000:.1f}K".replace(".0K", "K")
    return str(n)


def extract_soundgasm_link(html):
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        if "soundgasm.net" in a["href"]:
            return a["href"]

    m = SOUNDGASM_RE.search(soup.get_text(" "))
    return m.group(1) if m else None