# Plan: zenius-auto-download

## Context
Build a distributable Python tool that DDR players can install from GitHub (or PyPI) to automatically detect and download new simfiles from a Zenius-I-Vanisher category page, keeping their local Stepmania Songs folder in sync.

## Confirmed Decisions
- **Language:** Python
- **Distribution:** PyPI (`pip install`) + standalone `.exe` via PyInstaller for GitHub Releases
- **Login:** Anonymous downloads only (no login support for now)
- **ZIP handling:** Extract to Songs folder, delete ZIP
- **Execution:** Manual runs, with scheduler docs in README
- **Git:** Initialize repo as first step

---

## Site Structure (from research)
- Category page: `https://zenius-i-vanisher.com/v5.2/viewsimfilecategory.php?categoryid=1709`
- Each song links to: `viewsimfile.php?simfileid=XXXXX`
- Download URL: `https://zenius-i-vanisher.com/v5.2/download.php?type=ddrsimfile&simfileid=XXXXX` (returns ZIP)
- All simfiles appear on one page (no pagination observed)
- IDs are parsed from anchor `href` attributes matching `viewsimfile.php?simfileid=(\d+)`

---

## Project Structure
```
zenius-auto-download/
├── zenius_downloader/
│   ├── __init__.py          # version info
│   ├── scraper.py           # fetch + parse category pages
│   ├── downloader.py        # download ZIPs, extract, clean up
│   ├── state.py             # load/save state.json
│   └── cli.py               # argparse entry point
├── config.example.json      # template users copy to config.json
├── pyproject.toml           # package metadata + dependencies + CLI entry point
├── .gitignore
└── README.md
```

`config.json` and `state.json` are user-local files (gitignored, not part of the package).

---

## Key Files to Create

### `pyproject.toml`
- Package: `zenius-downloader`
- CLI entry point: `zenius-update = zenius_downloader.cli:main`
- Dependencies: `requests`, `beautifulsoup4`, `lxml`

### `config.example.json`
```json
{
  "category_urls": [
    "https://zenius-i-vanisher.com/v5.2/viewsimfilecategory.php?categoryid=1709"
  ],
  "download_dir": "C:/path/to/Stepmania/Songs",
  "delay_seconds": 2.0
}
```

### `state.json` (auto-generated, gitignored)
```json
{
  "downloaded": {
    "63195": { "name": "1116", "downloaded_at": "2026-02-19 10:00:00" }
  }
}
```

### `zenius_downloader/scraper.py`
- `get_simfiles(url, session) -> list[tuple[str, str]]`
  - GET the category page
  - Parse all `<a href="viewsimfile.php?simfileid=(\d+)">` anchors
  - Return list of `(simfile_id, song_name)`, deduplicated, in page order

### `zenius_downloader/downloader.py`
- `download_and_extract(simfile_id, name, download_dir, session, delay) -> bool`
  - GET `download.php?type=ddrsimfile&simfileid=XXXXX`
  - Write ZIP to a temp file
  - Extract ZIP contents into `download_dir`
  - Delete ZIP
  - Sleep `delay` seconds (polite scraping)
  - Return success/failure

### `zenius_downloader/state.py`
- `load_state(path) -> dict`
- `save_state(state, path) -> None`
- State file lives next to `config.json` in the user's working directory

### `zenius_downloader/cli.py`
- `main()` - argparse entry point
- Commands/flags:
  - `zenius-update` — check and download new files
  - `zenius-update --dry-run` — show what would download, no action
  - `zenius-update --list` — print all site simfiles with NEW/downloaded status
  - `zenius-update --force-id 63195` — re-download a specific ID regardless of state

---

## Download Flow
1. Load `config.json` (if missing, copy from `config.example.json` and prompt user to edit)
2. Load `state.json`
3. For each `category_url`: scrape simfile list
4. Diff against state → find new IDs
5. Print summary: total / already have / new
6. For each new simfile: download → extract → update state → save state
7. Save state after **each** successful download (safe to interrupt mid-run)

---

## Error Handling
- `config.json` missing `download_dir` → clear error message pointing to `config.example.json`
- HTTP errors (4xx/5xx) → print error, skip, continue
- Bad ZIP (possible if auth required) → print note about anonymous access limitation, skip
- Network timeout → print error, skip

---

## Implementation Steps
1. `git init` the repo
2. Create `.gitignore`
3. Create `pyproject.toml`
4. Create `zenius_downloader/__init__.py`
5. Create `zenius_downloader/state.py`
6. Create `zenius_downloader/scraper.py`
7. Create `zenius_downloader/downloader.py`
8. Create `zenius_downloader/cli.py`
9. Create `config.example.json`
10. Create `README.md` (setup, usage, scheduler docs for Windows/Mac/Linux)

---

## Verification
1. `pip install -e .` — installs package locally in editable mode
2. Copy `config.example.json` → `config.json`, set a real `download_dir`
3. `zenius-update --list` — confirm site is scraped and simfiles appear
4. `zenius-update --dry-run` — confirm new files are detected
5. `zenius-update` — confirm a ZIP downloads, extracts, and state updates
6. Run again — confirm already-downloaded files are skipped
