"""Filtro di attinenza titolo↔query.

L'OPAC cerca su titolo + autore + soggetto + abstract, quindi può tornare
libri non pertinenti al titolo cercato. Qui applichiamo un match a token:
ogni parola "di contenuto" della query deve comparire nel titolo.

Esempio:
  query  = "lo sviluppo e liberta"
  titolo = "Lo sviluppo è libertà"     → MATCH (sviluppo, liberta sono entrambi presenti)
  titolo = "Capitalismo e libertà"     → NO MATCH (manca "sviluppo")
  titolo = "Libertà e moderazione"     → NO MATCH (manca "sviluppo")
"""
from __future__ import annotations

import re
import unicodedata

# Stopword italiane: articoli, preposizioni, congiunzioni comuni.
_STOPWORDS_IT = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "l",
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "e", "ed", "o", "od", "ma", "che", "se", "si", "ne", "non", "è",
    "del", "dello", "della", "dei", "degli", "delle",
    "al", "allo", "alla", "ai", "agli", "alle",
    "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "nel", "nello", "nella", "nei", "negli", "nelle",
    "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "col", "coi",
}


def _normalize(s: str) -> str:
    """Lowercase + rimozione accenti + solo alfanumerico e spazi."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return s


def _tokens_contenuto(s: str) -> set[str]:
    return {t for t in _normalize(s).split() if t and t not in _STOPWORDS_IT and len(t) > 1}


def titolo_matcha_query(titolo: str, query: str) -> bool:
    """Vero se tutti i token di contenuto della query sono presenti nel titolo."""
    q = _tokens_contenuto(query)
    if not q:
        return True
    t = _tokens_contenuto(titolo)
    return q.issubset(t)
