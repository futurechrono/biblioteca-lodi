"""Client HTTP verso l'OPAC della biblioteca di Lodi."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import requests

from . import parser
from .cache import get_or_set
from .config import HTTP_TIMEOUT_SECONDS, OPAC_BASE_URL, RESULTS_PER_PAGE, USER_AGENT
from .models import Libro, RisultatoRicerca


class OpacError(Exception):
    pass


_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html"})


def _fetch(path: str, params: dict | None = None) -> str:
    url = f"{OPAC_BASE_URL}{path}"
    try:
        resp = _session.get(url, params=params or {}, timeout=HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise OpacError(f"Errore chiamando OPAC: {e}") from e
    return resp.text


def cerca(query: str, pagina: int = 1) -> RisultatoRicerca:
    """OPAC paginazione: parametro `start` = offset 0-based."""
    start = max(0, (pagina - 1) * RESULTS_PER_PAGE)
    key = f"cerca:{start}:{query.lower().strip()}"

    def _do() -> RisultatoRicerca:
        params = {"q": query}
        if start:
            params["start"] = start
        html = _fetch("/opac/search/lst", params)
        return parser.parse_risultati(html, query=query, pagina=pagina)

    return get_or_set(key, _do)


def dettagli_in_parallelo(libro_ids: list[str], max_workers: int = 5) -> list[Libro | None]:
    """Recupera il dettaglio di più libri in parallelo (I/O bound)."""
    if not libro_ids:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(dettaglio, libro_ids))


def dettaglio(libro_id: str) -> Libro | None:
    key = f"det:{libro_id}"

    def _do() -> Libro | None:
        html = _fetch(f"/opac/detail/view/{libro_id}")
        return parser.parse_dettaglio(html)

    return get_or_set(key, _do)


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        sys.exit("Uso: python -m lib.opac_client <query>            (ricerca)\n"
                 "     python -m lib.opac_client lo:catalog:XXXXX   (dettaglio)")
    arg = sys.argv[1]
    if arg.startswith("lo:"):
        libro = dettaglio(arg)
        print(json.dumps(libro.to_dict() if libro else None, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(cerca(arg).to_dict(), indent=2, ensure_ascii=False))
