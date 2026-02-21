import argparse
import json
import shutil
import time
from pathlib import Path

import requests

from .downloader import download_and_extract, sanitize
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


def reconcile_state(state: dict, download_dir: Path) -> int:
    """Remove state entries whose song folders no longer exist on disk.

    Uses per-category directory snapshots so only categories whose folder
    listing has changed are fully checked — repeated runs with no deletions
    cost one os.listdir() per game folder and nothing more.

    Returns the number of stale entries removed.
    """
    downloaded = state.setdefault("downloaded", {})
    snapshots = state.setdefault("dir_snapshots", {})

    cats = {entry.get("category", "") for entry in downloaded.values()}

    # Build the current directory listing for each category
    current: dict[str, set[str]] = {}
    for cat in cats:
        game_dir = download_dir / sanitize(cat) if cat else download_dir
        current[cat] = (
            {p.name for p in game_dir.iterdir() if p.is_dir()}
            if game_dir.is_dir() else set()
        )

    # Find categories whose listing differs from the stored snapshot.
    # Categories with no snapshot yet are always treated as changed so that
    # the first run after upgrading (or after deleting songs) fully reconciles.
    changed = {
        cat for cat, dirs in current.items()
        if cat not in snapshots or set(snapshots[cat]) != dirs
    }

    # Always update snapshots to reflect current disk state
    for cat, dirs in current.items():
        snapshots[cat] = sorted(dirs)

    if not changed:
        return 0

    stale = [
        sid for sid, entry in downloaded.items()
        if entry.get("category", "") in changed
        and (entry.get("folder") or sanitize(entry.get("name", "")))
        not in current.get(entry.get("category", ""), set())
    ]
    for sid in stale:
        del downloaded[sid]
    return len(stale)


def _update_snapshot(state: dict, category_name: str, folder: str) -> None:
    """Add a folder to the stored snapshot for a category."""
    snap = state.setdefault("dir_snapshots", {})
    snap_set = set(snap.get(category_name, []))
    snap_set.add(folder)
    snap[category_name] = sorted(snap_set)


def collect_simfiles(config: dict, session: requests.Session) -> list[tuple[str, str, str]]:
    seen: set[str] = set()
    results: list[tuple[str, str, str]] = []
    for url in config.get("category_urls", []):
        category_name, simfiles = get_simfiles(url, session)
        for sid, name in simfiles:
            if sid not in seen:
                seen.add(sid)
                results.append((sid, name, category_name))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="zenius-update",
        description="Sync new DDR simfiles from Zenius-I-Vanisher to your Stepmania Songs folder.",
    )
    parser.add_argument("--init", action="store_true",
                        help="Run interactive setup to configure categories and download folder")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without downloading anything")
    parser.add_argument("--list", action="store_true",
                        help="List all simfiles found on the site with their download status")
    parser.add_argument("--force-id", metavar="ID",
                        help="Force re-download a specific simfile ID (ignores state)")
    args = parser.parse_args()

    if args.init:
        from .setup import run_setup
        run_setup()
        return

    config = load_config()

    download_dir_str = config.get("download_dir", "").strip()
    if not download_dir_str:
        print("ERROR: Set 'download_dir' in config.json to your Stepmania Songs folder path.")
        raise SystemExit(1)

    download_dir = Path(download_dir_str)
    download_dir.mkdir(parents=True, exist_ok=True)

    state = load_state()
    downloaded: dict = state.setdefault("downloaded", {})

    removed = reconcile_state(state, download_dir)
    if removed:
        print(f"Removed {removed} missing entr{'y' if removed == 1 else 'ies'} from state (songs no longer on disk).")
        save_state(state)

    session = build_session()
    delay: float = config.get("delay_seconds", 2.0)
    skip_videos: bool = config.get("skip_videos", False)

    # --force-id: bypass state and download a single specific simfile
    if args.force_id:
        simfile_id = args.force_id.strip()
        existing = downloaded.get(simfile_id, {})
        song_name = existing.get("name", f"simfile_{simfile_id}")
        category_name = existing.get("category", "")
        dest_dir = download_dir / sanitize(category_name) if category_name else download_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"Force-downloading simfile ID {simfile_id}...")
        folder = download_and_extract(simfile_id, song_name, dest_dir, session, delay, skip_videos)
        if folder is not None:
            if category_name:
                _update_snapshot(state, category_name, folder)
            downloaded[simfile_id] = {
                "name": song_name,
                "category": category_name,
                "folder": folder,
                "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_state(state)
        raise SystemExit(0 if folder is not None else 1)

    all_simfiles = collect_simfiles(config, session)

    if args.list:
        print(f"\n{'ID':<10} {'Status':<14} {'Category':<30} Song")
        print("-" * 80)
        for sid, name, category_name in all_simfiles:
            status = "downloaded" if sid in downloaded else "NEW"
            print(f"{sid:<10} {status:<14} {category_name:<30} {name}")
        print(f"\nTotal: {len(all_simfiles)}  |  Downloaded: {len(downloaded)}  |  New: {sum(1 for s, _, __ in all_simfiles if s not in downloaded)}")
        return

    new_simfiles = [(sid, name, cat) for sid, name, cat in all_simfiles if sid not in downloaded]

    print(f"\nOn site   : {len(all_simfiles)}")
    print(f"Have      : {len(downloaded)}")
    print(f"New       : {len(new_simfiles)}")

    if not new_simfiles:
        print("\nAll up to date.")
        return

    if args.dry_run:
        print("\nDry run -- would download:")
        for sid, name, category_name in new_simfiles:
            print(f"  [{sid}] {category_name} / {name}")
        return

    print(f"\nDownloading {len(new_simfiles)} new simfile(s)...\n")

    success = 0
    skipped = 0
    failed = 0
    for simfile_id, song_name, category_name in new_simfiles:
        game_dir = download_dir / sanitize(category_name)
        game_dir.mkdir(parents=True, exist_ok=True)

        # If the song folder already exists locally, mark it and skip the download
        folder_guess = sanitize(song_name)
        if (game_dir / folder_guess).exists():
            print(f"  [{simfile_id}] {song_name} — already exists, skipping")
            _update_snapshot(state, category_name, folder_guess)
            downloaded[simfile_id] = {
                "name": song_name,
                "category": category_name,
                "folder": folder_guess,
                "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_state(state)
            skipped += 1
            continue

        folder = download_and_extract(simfile_id, song_name, game_dir, session, delay, skip_videos)
        if folder is not None:
            _update_snapshot(state, category_name, folder)
            downloaded[simfile_id] = {
                "name": song_name,
                "category": category_name,
                "folder": folder,
                "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_state(state)
            success += 1
        else:
            failed += 1

    parts = [f"{success} downloaded"]
    if skipped:
        parts.append(f"{skipped} already existed")
    if failed:
        parts.append(f"{failed} failed")
    print(f"\nDone. {', '.join(parts)}.")
    if failed:
        print("Tip: some files may require a Zenius account login. Login support can be added in a future version.")

