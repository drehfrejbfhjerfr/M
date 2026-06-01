import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run(step, args):
    script_path = BASE_DIR / step

    print("\n" + "=" * 60)
    print(f"🚀 Running: {script_path}")
    print("=" * 60)

    result = subprocess.run(
        ["python", str(script_path)] + args,
        text=True
    )

    if result.returncode != 0:
        print(f"\n❌ Step failed: {step}")
        sys.exit(1)

def main():
    # Use fixed query URL
    url = "https://gwasi.com/#q=score%3A%3E3000%20F4M%20"
    print(f"ℹ️ Using GWASI query URL: {url}")

    # Pass the URL as an argument to scripts that need it
    run("gwasi_scraper.py", [url])
    run("reddit_scraper.py", [])
    run("soundgasm_scraper.py", [])
    run("rss_builder.py", [url])  # Pass it here too

    print("\n🎉 PIPELINE COMPLETE → feed.xml generated")

if __name__ == "__main__":
    main()