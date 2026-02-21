from __future__ import annotations

import re
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

_SIMFILE_ID_RE = re.compile(r"viewsimfile\.php\?simfileid=(\d+)")
_SERVER_TIME_RE = re.compile(r"Server Time:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
_RELATIVE_DATE_RE = re.compile(r"([\d.]+)\s+(day|week|month|year)s?\s+ago", re.IGNORECASE)

_CATEGORY_ID_RE = re.compile(r"viewsimfilecategory\.php\?categoryid=(\d+)")
_CATEGORY_SOURCES = [
    "https://zenius-i-vanisher.com/v5.2/simfiles.php?category=latest-official",
    "https://zenius-i-vanisher.com/v5.2/simfiles.php?category=top-official",
]


def _parse_server_time(soup) -> datetime | None:
    """Extract the absolute server time from the page footer."""
    m = _SERVER_TIME_RE.search(soup.get_text())
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _parse_relative_date(text: str, server_time: datetime) -> datetime | None:
    """Convert a relative string like '7.2 months ago' to an absolute datetime."""
    m = _RELATIVE_DATE_RE.search(text)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    days_per_unit = {"day": 1.0, "week": 7.0, "month": 30.44, "year": 365.25}
    days = value * days_per_unit[unit]
    return server_time - timedelta(days=days)


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


def get_simfiles(url: str, session: requests.Session) -> tuple[str, list[tuple[str, str, datetime | None]]]:
    """
    Scrape a Zenius category page and return
    (category_name, [(simfile_id, song_name, zenius_updated_at), ...]).
    Results are deduplicated and preserve page order.
    zenius_updated_at is None when the date cannot be parsed from the page.
    """
    print(f"Fetching: {url}")
    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Derive the game name from the page heading, falling back to title then URL
    category_name = ""
    h1 = soup.find("h1")
    if h1:
        category_name = h1.get_text(strip=True)
    if not category_name:
        title_tag = soup.find("title")
        if title_tag:
            category_name = title_tag.get_text(strip=True).split(" - ")[0].strip()
    if not category_name:
        m = _CATEGORY_ID_RE.search(url)
        category_name = f"Category_{m.group(1)}" if m else "Unknown"

    server_time = _parse_server_time(soup)

    seen: set[str] = set()
    simfiles: list[tuple[str, str, datetime | None]] = []

    for a in soup.find_all("a", href=_SIMFILE_ID_RE):
        match = _SIMFILE_ID_RE.search(a["href"])
        if not match:
            continue
        simfile_id = match.group(1)
        if simfile_id in seen:
            continue
        seen.add(simfile_id)

        zenius_updated_at: datetime | None = None
        if server_time is not None:
            tr = a.find_parent("tr")
            if tr:
                tds = tr.find_all("td", recursive=False)
                if len(tds) >= 2:
                    zenius_updated_at = _parse_relative_date(tds[1].get_text(strip=True), server_time)

        simfiles.append((simfile_id, a.get_text(strip=True), zenius_updated_at))

    return category_name, simfiles
