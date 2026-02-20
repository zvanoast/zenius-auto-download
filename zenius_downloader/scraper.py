import re

import requests
from bs4 import BeautifulSoup

_SIMFILE_ID_RE = re.compile(r"viewsimfile\.php\?simfileid=(\d+)")

_CATEGORY_ID_RE = re.compile(r"viewsimfilecategory\.php\?categoryid=(\d+)")
_CATEGORY_SOURCES = [
    "https://zenius-i-vanisher.com/v5.2/simfiles.php?category=latest-official",
    "https://zenius-i-vanisher.com/v5.2/simfiles.php?category=top-official",
]


def get_categories(session: requests.Session) -> list[tuple[str, str]]:
    """
    Scrape official category pages and return deduplicated (category_id, name) pairs
    for all official game releases found.
    """
    seen: set[str] = set()
    results = []
    for url in _CATEGORY_SOURCES:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", href=_CATEGORY_ID_RE):
            match = _CATEGORY_ID_RE.search(a["href"])
            if not match:
                continue
            cid = match.group(1)
            name = a.get_text(strip=True)
            if cid not in seen and name:
                seen.add(cid)
                results.append((cid, name))
    return results


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
