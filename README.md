# zenius-auto-download

Automatically sync new DDR simfiles from [Zenius-I-Vanisher](https://zenius-i-vanisher.com) to your local Stepmania Songs folder.

Run it whenever you want to check for updates — it tracks what you already have and only downloads what's new.

---

## Requirements

- Python 3.10 or newer

---

## Installation

### Option A — Install via pip (recommended)

```bash
pip install zenius-downloader
```

This gives you the `zenius-update` command globally.

### Option B — Run from source

```bash
git clone https://github.com/YOUR_USERNAME/zenius-auto-download.git
cd zenius-auto-download
pip install -e .
```

---

## Setup

Run the interactive setup wizard to pick your games and configure your Songs folder:

```bash
zenius-update --init
```

This fetches the list of official DDR/Dance Stage releases from Zenius, lets you select which ones to sync, and writes `config.json` for you.

Alternatively, copy and edit the config manually:

```bash
cp config.example.json config.json
```

```json
{
  "category_urls": [
    "https://zenius-i-vanisher.com/v5.2/viewsimfilecategory.php?categoryid=1709"
  ],
  "download_dir": "C:/Games/StepMania 5/Songs",
  "delay_seconds": 2.0,
  "skip_videos": false
}
```

> Run `zenius-update` from the same folder as your `config.json`.

---

## Usage

```bash
# First-time setup: pick your games interactively
zenius-update --init

# Download all new simfiles
zenius-update

# Preview what would be downloaded (no files touched)
zenius-update --dry-run

# List all simfiles on the site and their download status
zenius-update --list

# Force re-download a specific simfile by ID
zenius-update --force-id 63195
```

---

## Config options

| Key | Description | Default |
|---|---|---|
| `category_urls` | List of Zenius category page URLs to sync | DDR WORLD category |
| `download_dir` | Path to your Stepmania Songs folder | *(required)* |
| `delay_seconds` | Pause between downloads (be polite to the server) | `2.0` |
| `skip_videos` | Skip `.avi` video files when extracting ZIPs | `false` |

To sync multiple categories, add more URLs to the `category_urls` list:

```json
"category_urls": [
  "https://zenius-i-vanisher.com/v5.2/viewsimfilecategory.php?categoryid=1709",
  "https://zenius-i-vanisher.com/v5.2/viewsimfilecategory.php?categoryid=XXXX"
]
```

---

## Automatic scheduling (optional)

### Windows — Task Scheduler

1. Open **Task Scheduler** and click **Create Basic Task**
2. Set the trigger (e.g. daily)
3. Set the action to: `zenius-update`
4. Set **Start in** to the folder containing your `config.json`

### macOS / Linux — cron

```bash
crontab -e
```

Add a line to run daily at 9am:

```
0 9 * * * cd /path/to/your/config/folder && zenius-update
```

---

## How it works

1. Fetches each configured category page and scrapes all simfile IDs
2. Compares against `state.json` (tracks what you've already downloaded)
3. Downloads each new simfile as a ZIP, extracts it into your Songs folder, deletes the ZIP
4. Updates `state.json` after each successful download — safe to interrupt at any time

---

## Troubleshooting

**"Bad ZIP" error** — Some files on Zenius may require a logged-in account to download. Login support is planned for a future version.

**Songs folder not updating** — Make sure `download_dir` in `config.json` points to the correct Stepmania `Songs/` subfolder, not the Stepmania root.
