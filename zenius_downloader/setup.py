import json
from pathlib import Path

import questionary
import requests

from .scraper import get_categories

CONFIG_FILE = Path("config.json")
BASE_CATEGORY_URL = "https://zenius-i-vanisher.com/v5.2/viewsimfilecategory.php?categoryid={}"


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    return session


def run_setup() -> None:
    print("\nzenius-update setup")
    print("=" * 40)

    if CONFIG_FILE.exists():
        overwrite = questionary.confirm(
            "config.json already exists. Overwrite it?",
            default=False,
        ).ask()
        if not overwrite:
            print("Setup cancelled.")
            return

    session = build_session()

    print("\nFetching official game categories from Zenius-I-Vanisher...")
    try:
        categories = get_categories(session)
    except Exception as e:
        print(f"Error fetching categories: {e}")
        raise SystemExit(1)

    if not categories:
        print("No categories found. The site may be unavailable.")
        raise SystemExit(1)

    choices = [
        questionary.Choice(title=name, value=cid)
        for cid, name in categories
    ]

    selected_ids = questionary.checkbox(
        "Which games do you want to sync? (Space to select, Enter to confirm)",
        choices=choices,
    ).ask()

    if not selected_ids:
        print("No games selected. Setup cancelled.")
        raise SystemExit(0)

    download_dir = questionary.text(
        "Path to your Stepmania Songs folder:",
        default=r"C:\Games\StepMania 5\Songs",
        validate=lambda p: len(p.strip()) > 0 or "Please enter a path.",
    ).ask()

    if download_dir is None:
        raise SystemExit(0)

    skip_videos = questionary.confirm(
        "Skip video (.avi) files when downloading?",
        default=False,
    ).ask()

    category_urls = [BASE_CATEGORY_URL.format(cid) for cid in selected_ids]

    config = {
        "category_urls": category_urls,
        "download_dir": download_dir.strip(),
        "delay_seconds": 2.0,
        "skip_videos": skip_videos,
    }

    CONFIG_FILE.write_text(json.dumps(config, indent=2))

    print(f"\nconfig.json written with {len(selected_ids)} game(s):")
    for cid, name in categories:
        if cid in selected_ids:
            print(f"  - {name}")

    print("\nRun 'zenius-update --dry-run' to preview what will be downloaded.")
    print("Run 'zenius-update' to start syncing.")
