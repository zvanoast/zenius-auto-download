import argparse
import json
import shutil
import time
from pathlib import Path

import requests

from .downloader import download_and_extract
from .scraper import get_simfiles
from .state import load_state, save_state

CONFIG_FILE = Path("config.json")
CONFIG_EXAMPLE = Path(__file__).parent.parent / "config.example.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        if CONFIG_EXAMPLE.exists():
            shutil.copy(CONFIG_EXAMPLE, CONFIG_FILE)
            print(f"Created config.json from config.example.json.")
        else:
            CONFIG_FILE.write_text(json.dumps({
                "category_urls": [
                    "https://zenius-i-vanisher.com/v5.2/viewsimfilecategory.php?categoryid=1709"
                ],
                "download_dir": "",
                "delay_seconds": 2.0,
            }, indent=2))
        print("Edit config.json to set your 'download_dir', then re-run.")
        raise SystemExit(0)

    with CONFIG_FILE.open() as f:
        return json.load(f)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    return session


def collect_simfiles(config: dict, session: requests.Session) -> list[tuple[str, str]]:
    seen: set[str] = set()
    results: list[tuple[str, str]] = []
    for url in config.get("category_urls", []):
        for sid, name in get_simfiles(url, session):
            if sid not in seen:
                seen.add(sid)
                results.append((sid, name))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="zenius-update",
        description="Sync new DDR simfiles from Zenius-I-Vanisher to your Stepmania Songs folder.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without downloading anything")
    parser.add_argument("--list", action="store_true",
                        help="List all simfiles found on the site with their download status")
    parser.add_argument("--force-id", metavar="ID",
                        help="Force re-download a specific simfile ID (ignores state)")
    args = parser.parse_args()

    config = load_config()

    download_dir_str = config.get("download_dir", "").strip()
    if not download_dir_str:
        print("ERROR: Set 'download_dir' in config.json to your Stepmania Songs folder path.")
        raise SystemExit(1)

    download_dir = Path(download_dir_str)
    download_dir.mkdir(parents=True, exist_ok=True)

    state = load_state()
    downloaded: dict = state.setdefault("downloaded", {})
    session = build_session()
    delay: float = config.get("delay_seconds", 2.0)

    # --force-id: bypass state and download a single specific simfile
    if args.force_id:
        simfile_id = args.force_id.strip()
        print(f"Force-downloading simfile ID {simfile_id}...")
        ok = download_and_extract(simfile_id, f"simfile_{simfile_id}", download_dir, session, delay)
        if ok:
            downloaded[simfile_id] = {
                "name": f"simfile_{simfile_id}",
                "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_state(state)
        raise SystemExit(0 if ok else 1)

    all_simfiles = collect_simfiles(config, session)

    if args.list:
        print(f"\n{'ID':<10} {'Status':<14} Song")
        print("-" * 60)
        for sid, name in all_simfiles:
            status = "downloaded" if sid in downloaded else "NEW"
            print(f"{sid:<10} {status:<14} {name}")
        print(f"\nTotal: {len(all_simfiles)}  |  Downloaded: {len(downloaded)}  |  New: {sum(1 for s, _ in all_simfiles if s not in downloaded)}")
        return

    new_simfiles = [(sid, name) for sid, name in all_simfiles if sid not in downloaded]

    print(f"\nOn site   : {len(all_simfiles)}")
    print(f"Have      : {len(downloaded)}")
    print(f"New       : {len(new_simfiles)}")

    if not new_simfiles:
        print("\nAll up to date.")
        return

    if args.dry_run:
        print("\nDry run — would download:")
        for sid, name in new_simfiles:
            print(f"  [{sid}] {name}")
        return

    print(f"\nDownloading {len(new_simfiles)} new simfile(s)...\n")

    success = 0
    failed = 0
    for simfile_id, song_name in new_simfiles:
        ok = download_and_extract(simfile_id, song_name, download_dir, session, delay)
        if ok:
            downloaded[simfile_id] = {
                "name": song_name,
                "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_state(state)
            success += 1
        else:
            failed += 1

    print(f"\nDone. {success} downloaded, {failed} failed.")
    if failed:
        print("Tip: some files may require a Zenius account login. Login support can be added in a future version.")
