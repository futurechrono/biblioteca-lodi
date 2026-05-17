"""Parsing dell'HTML dell'OPAC di Lodi (software DiscoveryNG di Comperio).

Selettori basati sul DOM reale delle pagine:
  - /opac/search/lst         → lista risultati
  - /opac/detail/view/{id}   → dettaglio con tabella copie
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .config import OPAC_BASE_URL
from .models import Copia, Libro, RisultatoRicerca

_RE_TOTALE = re.compile(r"Trovati\s*<strong>\s*(\d+)\s*</strong>", re.IGNORECASE)


def _txt(el: Tag | None) -> str | None:
    if el is None:
        return None
    s = el.get_text(" ", strip=True)
    return s or None


def _int(el: Tag | None) -> int | None:
    s = _txt(el)
    if not s:
        return None
    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else None


def _absolute(href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(OPAC_BASE_URL + "/", href)


# --- LISTA RISULTATI ---------------------------------------------------------

def parse_risultati(html: str, query: str, pagina: int) -> RisultatoRicerca:
    soup = BeautifulSoup(html, "lxml")
    libri = [_parse_item_lista(item) for item in soup.select("#result-list .lst-item")]
    totale = _estrai_totale(soup, html) or len(libri)
    return RisultatoRicerca(query=query, pagina=pagina, totale=totale, risultati=libri)


def _parse_item_lista(item: Tag) -> Libro:
    actions = item.select_one(".title-actions")
    libro_id = (actions.get("data-manid") if actions else None) or item.get("id", "").removeprefix("man_") or None

    titolo_el = item.select_one(".main-title strong, .main-title")
    cover_img = item.select_one(".cover-wrapper img")
    cover_link = item.select_one(".cover-wrapper a.cover") or item.select_one("a.manifestation_link")

    edizione, luogo, editore, anno = _parse_dettagli_pubblicazione(item)

    return Libro(
        id=libro_id,
        titolo=_txt(titolo_el) or "(senza titolo)",
        autore=_txt(item.select_one(".main-author")),
        editore=editore,
        luogo=luogo,
        anno=anno,
        edizione=edizione,
        tipo=_txt(item.select_one(".doc-type-label")),
        abstract=_txt(item.select_one(".abstract .abs-content")),
        copertina_url=(cover_img.get("src") if cover_img else None),
        url_dettaglio=_absolute(cover_link.get("href") if cover_link else None),
        copie_totali=_int(item.select_one(".visible_items")),
        copie_in_prestito=_int(item.select_one(".onloan_items")),
        prenotazioni=_int(item.select_one(".pending_requests")),
    )


def _parse_dettagli_pubblicazione(item: Tag) -> tuple[str | None, str | None, str | None, str | None]:
    """Da `.details p` ritorna (edizione, luogo, editore, anno)."""
    edizione = luogo = editore = anno = None
    paragrafi = [_txt(p) for p in item.select(".details p")]
    paragrafi = [p for p in paragrafi if p]

    pubblicazione = None
    for p in paragrafi:
        if re.search(r"\b(ed\.?|edizione)\b", p, re.IGNORECASE) and "," not in p:
            edizione = p
        else:
            pubblicazione = p

    if pubblicazione:
        m = re.match(r"^\s*(?:(?P<luogo>[^:]+)\s*:\s*)?(?P<editore>[^,]+?),\s*(?P<anno>[^,]+?)\s*$", pubblicazione)
        if m:
            luogo = (m.group("luogo") or "").strip() or None
            editore = m.group("editore").strip() or None
            anno = m.group("anno").strip() or None
        else:
            editore = pubblicazione
    return edizione, luogo, editore, anno


def _estrai_totale(soup: BeautifulSoup, html: str) -> int | None:
    header = soup.select_one(".resultPage h2.page-header small")
    if header:
        n = _int(header)
        if n is not None:
            return n
    m = _RE_TOTALE.search(html)
    if m:
        return int(m.group(1))
    return None


# --- PAGINA DI DETTAGLIO -----------------------------------------------------

def parse_dettaglio(html: str) -> Libro | None:
    """Parsa /opac/detail/view/{id}, ritorna Libro completo con copie per biblioteca."""
    soup = BeautifulSoup(html, "lxml")

    wrapper = soup.select_one("[id^='man_'][data-manid]")
    if not wrapper:
        return None

    libro_id = wrapper.get("data-manid")
    titolo = _txt(wrapper.select_one(".main-title")) or "(senza titolo)"
    autore = _txt(wrapper.select_one(".main-author"))
    tipo = _txt(wrapper.select_one(".doc-type-label"))
    abstract = _txt(wrapper.select_one(".abstract .abs-content"))

    cover_img = wrapper.select_one(".cover-wrapper img")
    luogo = editore = anno = None
    for p in wrapper.select(".pubdetails p"):
        label = _txt(p.select_one("strong")) or ""
        if "Pubblicazione" in label:
            val = (_txt(p) or "").replace(label, "", 1).strip()
            m = re.match(r"^\s*(?:(?P<luogo>[^:]+)\s*:\s*)?(?P<editore>[^,]+?),\s*(?P<anno>.+?)\s*$", val)
            if m:
                luogo = (m.group("luogo") or "").strip() or None
                editore = m.group("editore").strip() or None
                anno = m.group("anno").strip() or None

    copie = _parse_copie(wrapper)

    return Libro(
        id=libro_id,
        titolo=titolo,
        autore=autore,
        editore=editore,
        luogo=luogo,
        anno=anno,
        tipo=tipo,
        abstract=abstract,
        copertina_url=(cover_img.get("src") if cover_img else None),
        url_dettaglio=f"{OPAC_BASE_URL}/opac/detail/view/{libro_id}" if libro_id else None,
        copie_totali=_int(wrapper.select_one(".visible_items")),
        copie_in_prestito=_int(wrapper.select_one(".onloan_items")),
        prenotazioni=_int(wrapper.select_one(".pending_requests")),
        copie=copie,
    )


def _parse_copie(wrapper: Tag) -> list[Copia]:
    """Estrae le righe della tabella #items_table."""
    copie: list[Copia] = []
    for row in wrapper.select("#items_table tr"):
        biblioteca = _txt(row.select_one('td[title="Biblioteca"] span[property="name"]')) \
            or _txt(row.select_one('td[title="Biblioteca"]'))
        copie.append(
            Copia(
                biblioteca=biblioteca,
                collocazione=_txt(row.select_one('td[title="Collocazione"]')),
                inventario=_txt(row.select_one('td[title="Inventario"]')),
                stato=_txt(row.select_one("td.loan_status_item")),
                prestabilita=_txt(row.select_one("td.lendability_item")),
                rientra=_txt(row.select_one('td[title="Rientra"]')),
            )
        )
    return copie
