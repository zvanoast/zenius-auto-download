import re

import requests
from bs4 import BeautifulSoup

_SIMFILE_ID_RE = re.compile(r"viewsimfile\.php\?simfileid=(\d+)")


def get_simfiles(url: str, session: requests.Session) -> list[tuple[str, str]]:
    """
    Scrape a Zenius category page and return (simfile_id, song_name) pairs.
    Results are deduplicated and preserve page order.
    """
    print(f"Fetching: {url}")
    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    seen: set[str] = set()
    simfiles: list[tuple[str, str]] = []

    for a in soup.find_all("a", href=_SIMFILE_ID_RE):
        match = _SIMFILE_ID_RE.search(a["href"])
        if not match:
            continue
        simfile_id = match.group(1)
        if simfile_id in seen:
            continue
        seen.add(simfile_id)
        simfiles.append((simfile_id, a.get_text(strip=True)))

    return simfiles
