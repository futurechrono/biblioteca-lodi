"""GET /api/disponibile?q=1984[&biblioteca=Lodi][&formato=testo]

Endpoint one-shot per il chatbot:
  1. cerca il libro per query
  2. prende il primo risultato (preferendo quelli con copie reali)
  3. ne legge la pagina di dettaglio
  4. risponde se è disponibile nella biblioteca richiesta

Pensato per essere invocato da Pandorabots via <sraix> con formato=testo.
"""
from http.server import BaseHTTPRequestHandler

from lib import formatter, opac_client
from lib.config import BIBLIOTECA_DEFAULT
from lib.http import query_params, send_json, send_text


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = query_params(self)
        q = p.get("q", "").strip()
        if not q:
            send_json(self, 400, {"errore": "parametro 'q' obbligatorio"})
            return

        biblioteca = p.get("biblioteca", BIBLIOTECA_DEFAULT)
        formato = p.get("formato", "testo")

        try:
            risultato = opac_client.cerca(q)
        except opac_client.OpacError as e:
            send_json(self, 502, {"errore": str(e)})
            return

        candidato = _miglior_candidato(risultato.risultati)
        if not candidato or not candidato.id:
            msg = f'Non ho trovato il libro "{q}" nel catalogo.'
            if formato == "testo":
                send_text(self, 200, msg)
            else:
                send_json(self, 200, {"trovato": False, "messaggio": msg})
            return

        try:
            libro = opac_client.dettaglio(candidato.id)
        except opac_client.OpacError as e:
            send_json(self, 502, {"errore": str(e)})
            return

        if not libro:
            send_json(self, 404, {"errore": f"Dettaglio non disponibile per {candidato.id}"})
            return

        if formato == "testo":
            send_text(self, 200, formatter.disponibilita_to_text(libro, biblioteca))
        else:
            copie = libro.disponibilita_in(biblioteca)
            send_json(self, 200, {
                "trovato": True,
                "id": libro.id,
                "titolo": libro.titolo,
                "autore": libro.autore,
                "biblioteca": biblioteca,
                "copie_nella_biblioteca": [c.to_dict() for c in copie],
                "disponibile_nella_biblioteca": any(c.disponibile for c in copie),
            })


def _miglior_candidato(libri):
    """Preferisce libri fisici con copie (catalog) rispetto a risorse MLOL."""
    con_copie = [l for l in libri if l.id and l.id.startswith("lo:catalog:") and (l.copie_totali or 0) > 0]
    if con_copie:
        return con_copie[0]
    catalog = [l for l in libri if l.id and l.id.startswith("lo:catalog:")]
    if catalog:
        return catalog[0]
    return libri[0] if libri else None
