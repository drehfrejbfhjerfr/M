# Usage: python make_feed_from_soundgasm.py "https://soundgasm.net/u/Iris1891" feed.xml
# Requires: pip install requests beautifulsoup4 lxml

import sys, time, re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
from email.utils import format_datetime
import xml.sax.saxutils as sax
import mimetypes

HEADERS = {"User-Agent": "rss-extractor/1.0"}

def get_filesize_and_type(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=10, headers=HEADERS)
        ct = r.headers.get("Content-Type")
        cl = r.headers.get("Content-Length")
        cl = str(int(cl)) if cl and cl.isdigit() else None
        return cl, ct
    except Exception:
        return None, None

def guess_mime(url, ct_header):
    if ct_header:
        return ct_header.split(";")[0]
    mt, _ = mimetypes.guess_type(url)
    return mt or "application/octet-stream"

def find_episode_links(listing_url):
    r = requests.get(listing_url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "lxml")
    links = []
    for a in soup.select(".sound-details a[href]"):
        href = a["href"]
        full = urljoin(listing_url, href)
        if "/u/" in urlparse(full).path:
            links.append(full)
    # dedupe preserving order then reverse (bottom-to-top)
    seen = set(); out = []
    for l in links:
        if l not in seen:
            seen.add(l); out.append(l)
    out.reverse()
    return out

def extract_from_page(page_url):
    r = requests.get(page_url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "lxml")

    title_el = soup.select_one(".sound-details a") or soup.select_one(".jp-title") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else "Untitled"

    desc_el = soup.select_one(".soundDescription") or soup.select_one(".jp-description p") or soup.select_one(".jp-description")
    description = desc_el.get_text(separator="\n", strip=True) if desc_el else ""

    audio_url = None
    for script in soup.find_all("script"):
        txt = script.string or ""
        m = re.search(r'(?:m4a|mp3|ogg|wav|aac)\s*:\s*["\']([^"\']+)["\']', txt, re.I)
        if m:
            audio_url = urljoin(page_url, m.group(1).strip()); break
    if not audio_url:
        a_tag = soup.find("audio")
        if a_tag and a_tag.get("src"):
            audio_url = urljoin(page_url, a_tag["src"])
    if not audio_url:
        meta = soup.find("meta", property="og:audio")
        if meta and meta.get("content"):
            audio_url = urljoin(page_url, meta["content"])
    if not audio_url:
        for ext in (".mp3", ".m4a", ".ogg", ".wav", ".aac"):
            link = soup.find("a", href=re.compile(re.escape(ext) + r"($|\?)", re.I))
            if link and link.get("href"):
                audio_url = urljoin(page_url, link["href"]); break

    if not audio_url:
        raise RuntimeError(f"No audio URL found on {page_url}")

    length, ct = get_filesize_and_type(audio_url)
    length = length or "0"
    mime = guess_mime(audio_url, ct)

    dur_el = soup.select_one(".jp-duration")
    duration = None
    if dur_el:
        d = dur_el.get_text(strip=True).lstrip("-").strip()
        if d:
            duration = d

    parsed = urlparse(audio_url)
    guid = sax.escape(parsed.path.split("/")[-1] or f"ep{int(datetime.utcnow().timestamp())}")

    return {
        "title": title,
        "description": description,
        "audio_url": audio_url,
        "length": length,
        "mime": mime,
        "guid": guid,
        "duration": duration
    }

def build_feed(channel_title, channel_link, channel_desc, items, self_url, start_date):
    title_xml = sax.escape(channel_title)
    desc_xml = sax.escape(channel_desc)
    link_xml = sax.escape(channel_link)
    self_xml = sax.escape(self_url)
    header = f'''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"
 xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
 xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{title_xml}</title>
    <link>{link_xml}</link>
    <description>{desc_xml}</description>
    <language>en-us</language>
    <atom:link href="{self_xml}" rel="self" type="application/rss+xml"/>
    <itunes:author>{title_xml}</itunes:author>
    <itunes:owner><itunes:name>{title_xml}</itunes:name></itunes:owner>
    <itunes:explicit>false</itunes:explicit>
'''
    body = ""
    # items list is now ordered bottom-to-top with index 0 = bottom-most (first date)
    for idx, it in enumerate(items):
        pub_dt = start_date + timedelta(days=idx)
        pubdate = format_datetime(pub_dt)
        t = sax.escape(it["title"])
        d = sax.escape(it["description"])
        body += "    <item>\n"
        body += f"      <title>{t}</title>\n"
        body += f"      <description>{d}</description>\n"
        body += f"      <pubDate>{pubdate}</pubDate>\n"
        body += f'      <enclosure url="{sax.escape(it["audio_url"])}" length="{it["length"]}" type="{sax.escape(it["mime"])}"/>\n'
        body += f'      <guid isPermaLink="false">{it["guid"]}</guid>\n'
        if it.get("duration"):
            body += f'      <itunes:duration>{sax.escape(it["duration"])}</itunes:duration>\n'
        body += "    </item>\n\n"
    footer = "  </channel>\n</rss>\n"
    return header + body + footer

def username_from_listing(listing_url):
    p = urlparse(listing_url).path
    m = re.match(r"/u/([^/]+)", p)
    return m.group(1) if m else None

def main():
    if len(sys.argv) < 3:
        print("Usage: python make_feed_from_soundgasm_with_dates_reversed.py \"https://soundgasm.net/u/Username\" feed.xml")
        sys.exit(1)
    listing_url = sys.argv[1].rstrip("/")
    out_file = sys.argv[2]
    user = username_from_listing(listing_url)
    if not user:
        print("Could not determine username from URL.")
        sys.exit(1)

    try:
        episode_links = find_episode_links(listing_url)
    except Exception as e:
        print("Failed to fetch listing:", e); sys.exit(1)
    if not episode_links:
        print("No episodes found."); sys.exit(1)

    items = []
    for i, link in enumerate(episode_links, 1):
        try:
            print(f"[{i}/{len(episode_links)}] Fetching {link}")
            it = extract_from_page(link)
            items.append(it)
            time.sleep(1)
        except Exception as e:
            print(f"  Skipped {link}: {e}")

    channel_title = user
    channel_link = listing_url
    channel_desc = f"Podcast feed generated from {listing_url}"
    self_url = f"https://{user}.example.com/{out_file}"

    # start date: bottom-most (first item after reverse) -> 2026-01-01
    start_date = datetime(2026, 1, 1)

    rss = build_feed(channel_title, channel_link, channel_desc, items, self_url, start_date)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(rss)
    print("Feed written to", out_file)

if __name__ == "__main__":
    main()
