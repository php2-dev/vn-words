from __future__ import annotations

from typing import Iterator, Optional

import requests

API_URL = "https://vi.wiktionary.org/w/api.php"
USER_AGENT = "wiktionary-vi-pipeline/0.1 (https://vi.wiktionary.org)"

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": USER_AGENT})


def _request(params: dict) -> dict:
    response = _SESSION.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_category_members(category_title: str, limit: Optional[int] = None) -> Iterator[str]:
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category_title,
        "cmnamespace": 0,
        "cmlimit": "max",
        "format": "json",
    }

    count = 0
    cont: Optional[dict] = None

    while True:
        if cont:
            params.update(cont)
        data = _request(params)
        members = data.get("query", {}).get("categorymembers", [])

        for item in members:
            yield item["title"]
            count += 1
            if limit is not None and count >= limit:
                return

        cont = data.get("continue")
        if not cont:
            break


def get_page_wikitext(title: str) -> Optional[str]:
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": 2,
    }

    data = _request(params)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None

    page = pages[0]
    if page.get("missing"):
        return None

    revisions = page.get("revisions")
    if not revisions:
        return None

    return revisions[0]["slots"]["main"]["content"]
