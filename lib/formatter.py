"""Formattazione delle risposte per il chatbot (testo pronto per Pandorabots)."""
from __future__ import annotations

from .models import Copia, Libro, RisultatoRicerca


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


def disponibilita_aggregata_to_text(
    query: str, edizioni: list[Libro], biblioteca: str, totale_esaminate: int
) -> str:
    """Risposta aggregata su più edizioni scansionate.

    `edizioni` contiene solo i Libri che hanno almeno una copia nella biblioteca.
    `totale_esaminate` è il numero totale di risultati scansionati (per messaggio).
    """
    if not edizioni:
        if totale_esaminate == 0:
            return f'Non ho trovato "{query}" nel catalogo.'
        return (f'Ho esaminato {totale_esaminate} edizioni di "{query}", '
                f"ma nessuna è presente alla biblioteca di {biblioteca}.")

    copie_disp: list[tuple[Libro, Copia]] = []
    copie_prest: list[tuple[Libro, Copia]] = []
    for libro in edizioni:
        for c in libro.disponibilita_in(biblioteca):
            if c.disponibile:
                copie_disp.append((libro, c))
            elif c.in_prestito:
                copie_prest.append((libro, c))

    righe = [f'Per "{query}" alla {biblioteca}:']
    righe.append(
        f"trovate {len(edizioni)} edizioni con copie in sede "
        f"({len(copie_disp)} disponibili, {len(copie_prest)} in prestito)."
    )

    if copie_disp:
        righe.append("")
        righe.append("DISPONIBILI:")
        for libro, c in copie_disp[:5]:
            righe.append(f"- {_titolo_edizione(libro)} — collocazione {c.collocazione or '?'}")

    if copie_prest:
        righe.append("")
        righe.append("IN PRESTITO:")
        for libro, c in copie_prest[:5]:
            rientro = f", rientra il {c.rientra}" if c.rientra else ""
            righe.append(f"- {_titolo_edizione(libro)}{rientro}")

    return "\n".join(righe)


def _titolo_edizione(libro: Libro) -> str:
    pezzi = [libro.titolo]
    if libro.autore:
        pezzi.append(f"di {libro.autore}")
    if libro.anno:
        pezzi.append(f"({libro.anno})")
    return " ".join(pezzi)


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
