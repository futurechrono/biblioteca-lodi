"""GET /api/disponibilita?id=lo:catalog:264315[&biblioteca=Lodi][&formato=testo]

Restituisce la lista copie per biblioteca leggendola dalla pagina di dettaglio.
Se passi `biblioteca`, filtra solo quelle che contengono la stringa nel nome.
"""
from http.server import BaseHTTPRequestHandler

from lib import formatter, opac_client
from lib.config import BIBLIOTECA_DEFAULT
from lib.http import query_params, send_json, send_text


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = query_params(self)
        libro_id = p.get("id", "").strip()
        if not libro_id:
            send_json(self, 400, {"errore": "parametro 'id' obbligatorio"})
            return

        biblioteca = p.get("biblioteca", BIBLIOTECA_DEFAULT)
        formato = p.get("formato", "json")

        try:
            libro = opac_client.dettaglio(libro_id)
        except opac_client.OpacError as e:
            send_json(self, 502, {"errore": str(e)})
            return

        if not libro:
            send_json(self, 404, {"errore": f"Libro non trovato: {libro_id}"})
            return

        if formato == "testo":
            send_text(self, 200, formatter.disponibilita_to_text(libro, biblioteca))
        else:
            copie = libro.disponibilita_in(biblioteca) if biblioteca else libro.copie
            send_json(self, 200, {
                "id": libro.id,
                "titolo": libro.titolo,
                "autore": libro.autore,
                "biblioteca_filtro": biblioteca,
                "copie": [c.to_dict() for c in copie],
            })
