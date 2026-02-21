# zenius-auto-download

A Python CLI tool that syncs DDR simfiles from Zenius-I-Vanisher to a local StepMania Songs folder.

## Project Structure

```
zenius_downloader/
├── cli.py        # Entry point, argparse, main download loop
├── scraper.py    # HTML scraping for category/simfile lists
├── downloader.py # ZIP download, extraction, delay logic
├── state.py      # Load/save state.json
└── setup.py      # Interactive --init wizard (uses questionary)
```

## CLI Commands

```bash
zenius-update --init       # Interactive setup wizard
zenius-update              # Sync new simfiles
zenius-update --dry-run    # Preview without downloading
zenius-update --list       # Show all simfiles with status
zenius-update --force-id <ID>  # Re-download a specific simfile
```

## Config (config.json)

Must be in the working directory when running `zenius-update`.

```json
{
  "category_urls": ["https://zenius-i-vanisher.com/v5.2/viewsimfilecategory.php?categoryid=1709"],
  "download_dir": "C:\\Games\\StepMania 5\\Songs",
  "delay_seconds": 2.0,
  "skip_videos": false
}
```

- `download_dir` must point to the `Songs/` subfolder, not the StepMania root.
- `config.json` and `state.json` are git-ignored (user-specific).

## State (state.json)

Tracks downloaded simfile IDs with name and timestamp. Saved after each successful download — safe to interrupt mid-run.

## Development

```bash
pip install -e .   # Editable install; CLI reflects code changes immediately
```

Entry point defined in `pyproject.toml`: `zenius-update = "zenius_downloader.cli:main"`

## Key Conventions

- Downloads stream to a temp file first, then extract — prevents corrupt ZIPs.
- Simfile IDs are deduplicated across multiple category URLs.
- Illegal filename characters are replaced with underscores.
- Uses a Mozilla User-Agent to avoid server blocks.
- Anonymous access only — some files may fail if they require login.

## Dependencies

- `requests` — HTTP downloads
- `beautifulsoup4` + `lxml` — HTML parsing
- `questionary` — interactive setup prompts

## Zenius URL Patterns

- Category list: `simfiles.php?category=latest-official` / `top-official`
- Category page: `viewsimfilecategory.php?categoryid={ID}`
- Download: `download.php?type=ddrsimfile&simfileid={ID}`

## Publishing to PyPI

Every PyPI release requires a version bump in `pyproject.toml`. Default to incrementing the
**minor** version (e.g. `0.2.0` → `0.3.0`); use the **major** version only for breaking changes.

```bash
# 1. Bump version in pyproject.toml, commit, and push

# 2. Build
pip install build twine   # one-time setup
python -m build           # produces dist/

# 3. Upload
twine upload dist/*       # prompts for credentials, or uses ~/.pypirc
```

`~/.pypirc` for token-based auth (recommended):
```ini
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
```
