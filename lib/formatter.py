"""Formattazione delle risposte per il chatbot (testo pronto per Pandorabots)."""
from __future__ import annotations

from .models import Libro, RisultatoRicerca


def lista_to_text(r: RisultatoRicerca, max_items: int = 5) -> str:
    if not r.risultati:
        return f'Non ho trovato libri per "{r.query}".'

    righe = [f'Ho trovato {r.totale} risultati per "{r.query}":']
    for i, libro in enumerate(r.risultati[:max_items], start=1):
        parti = [libro.titolo]
        if libro.autore:
            parti.append(f"di {libro.autore}")
        if libro.anno:
            parti.append(f"({libro.anno})")
        righe.append(f"{i}. {' '.join(parti)}")
    return "\n".join(righe)


def disponibilita_to_text(libro: Libro, biblioteca: str) -> str:
    """Risposta in italiano per "il libro X è disponibile a <biblioteca>?"."""
    intestazione = f'"{libro.titolo}"'
    if libro.autore:
        intestazione += f" di {libro.autore}"

    copie = libro.disponibilita_in(biblioteca)
    if not copie:
        return f"{intestazione} non è presente nella biblioteca di {biblioteca}."

    disponibili = [c for c in copie if c.disponibile]
    in_prestito = [c for c in copie if c.in_prestito]

    if disponibili:
        c = disponibili[0]
        coll = f" (collocazione: {c.collocazione})" if c.collocazione else ""
        return f"{intestazione} è DISPONIBILE alla {c.biblioteca}{coll}."

    if in_prestito:
        c = in_prestito[0]
        rientro = f", rientra il {c.rientra}" if c.rientra else ""
        return f"{intestazione} è IN PRESTITO alla {c.biblioteca}{rientro}."

    c = copie[0]
    stato = c.stato or "stato sconosciuto"
    return f"{intestazione} è alla {c.biblioteca}: {stato}."
