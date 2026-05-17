from http.server import BaseHTTPRequestHandler

from lib import formatter, opac_client
from lib.http import query_params, send_json, send_text


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = query_params(self)
        q = p.get("q", "").strip()
        if not q:
            send_json(self, 400, {"errore": "parametro 'q' obbligatorio"})
            return

        pagina = int(p.get("pagina", "1") or "1")
        formato = p.get("formato", "json")

        try:
            risultato = opac_client.cerca(q, pagina=pagina)
        except opac_client.OpacError as e:
            send_json(self, 502, {"errore": str(e)})
            return

        if formato == "testo":
            send_text(self, 200, formatter.lista_to_text(risultato))
        else:
            send_json(self, 200, risultato.to_dict())
