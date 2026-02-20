import re
import tempfile
import time
import zipfile
from pathlib import Path

import requests

BASE_URL = "https://zenius-i-vanisher.com/v5.2/"
_CONTENT_DISP_RE = re.compile(r'filename[^;=\n]*=\s*["\']?([^"\';\n]+)')


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()


def download_and_extract(
    simfile_id: str,
    song_name: str,
    download_dir: Path,
    session: requests.Session,
    delay: float = 2.0,
    skip_videos: bool = False,
) -> bool:
    """
    Download the ZIP for a simfile, extract it into download_dir, delete the ZIP.
    Returns True on success, False on any error.
    """
    url = f"{BASE_URL}download.php?type=ddrsimfile&simfileid={simfile_id}"
    print(f"  [{simfile_id}] {song_name}")

    try:
        resp = session.get(url, timeout=60, stream=True)
        resp.raise_for_status()

        # Write to a temp file so a partial download never leaves a corrupt ZIP
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)

        size_kb = tmp_path.stat().st_size // 1024
        print(f"    Downloaded {size_kb} KB")

        with zipfile.ZipFile(tmp_path, "r") as z:
            members = [m for m in z.namelist()
                       if not (skip_videos and m.lower().endswith(".avi"))]
            z.extractall(download_dir, members=members)
        tmp_path.unlink()

        if skip_videos:
            print(f"    Extracted to: {download_dir} (videos skipped)")
        else:
            print(f"    Extracted to: {download_dir}")
        time.sleep(delay)
        return True

    except requests.HTTPError as e:
        print(f"    HTTP error: {e}")
    except zipfile.BadZipFile:
        print(f"    Bad ZIP — file may require a Zenius login to download")
        if "tmp_path" in dir() and tmp_path.exists():
            tmp_path.unlink()
    except Exception as e:
        print(f"    Error: {e}")
        if "tmp_path" in dir() and tmp_path.exists():
            tmp_path.unlink()

    return False
