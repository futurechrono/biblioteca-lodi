"""Entrypoint Flask del middleware OPAC Lodi.

Espone tre endpoint:
  GET /api/health         health check
  GET /api/cerca          ricerca libri (q, pagina, formato)
  GET /api/disponibile    domanda one-shot del chatbot: "X è disponibile a Lodi?"
                          (q, biblioteca, formato)
  GET /api/disponibilita  copie per biblioteca dato l'id catalogo
                          (id, biblioteca, formato)

Tutte le query arrivano dal chatbot — nessun libro è hard-coded nel codice.
"""
from flask import Flask, Response, jsonify, request

from lib import formatter, opac_client
from lib.config import BIBLIOTECA_DEFAULT

app = Flask(__name__)


@app.get("/")
@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "biblioteca-lodi"})


@app.get("/api/cerca")
def cerca():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"errore": "parametro 'q' obbligatorio"}), 400

    pagina = int(request.args.get("pagina", "1") or "1")
    formato = request.args.get("formato", "json")

    try:
        risultato = opac_client.cerca(q, pagina=pagina)
    except opac_client.OpacError as e:
        return jsonify({"errore": str(e)}), 502

    if formato == "testo":
        return Response(formatter.lista_to_text(risultato), mimetype="text/plain; charset=utf-8")
    return jsonify(risultato.to_dict())


@app.get("/api/disponibile")
def disponibile():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"errore": "parametro 'q' obbligatorio"}), 400

    biblioteca = request.args.get("biblioteca", BIBLIOTECA_DEFAULT)
    formato = request.args.get("formato", "testo")

    try:
        risultato = opac_client.cerca(q)
    except opac_client.OpacError as e:
        return jsonify({"errore": str(e)}), 502

    candidato = _miglior_candidato(risultato.risultati)
    if not candidato or not candidato.id:
        msg = f'Non ho trovato il libro "{q}" nel catalogo.'
        if formato == "testo":
            return Response(msg, mimetype="text/plain; charset=utf-8")
        return jsonify({"trovato": False, "messaggio": msg})

    try:
        libro = opac_client.dettaglio(candidato.id)
    except opac_client.OpacError as e:
        return jsonify({"errore": str(e)}), 502

    if not libro:
        return jsonify({"errore": f"Dettaglio non disponibile per {candidato.id}"}), 404

    if formato == "testo":
        return Response(formatter.disponibilita_to_text(libro, biblioteca),
                        mimetype="text/plain; charset=utf-8")
    copie = libro.disponibilita_in(biblioteca)
    return jsonify({
        "trovato": True,
        "id": libro.id,
        "titolo": libro.titolo,
        "autore": libro.autore,
        "biblioteca": biblioteca,
        "copie_nella_biblioteca": [c.to_dict() for c in copie],
        "disponibile_nella_biblioteca": any(c.disponibile for c in copie),
    })


@app.get("/api/disponibilita")
def disponibilita():
    libro_id = (request.args.get("id") or "").strip()
    if not libro_id:
        return jsonify({"errore": "parametro 'id' obbligatorio"}), 400

    biblioteca = request.args.get("biblioteca", BIBLIOTECA_DEFAULT)
    formato = request.args.get("formato", "json")

    try:
        libro = opac_client.dettaglio(libro_id)
    except opac_client.OpacError as e:
        return jsonify({"errore": str(e)}), 502
    if not libro:
        return jsonify({"errore": f"Libro non trovato: {libro_id}"}), 404

    if formato == "testo":
        return Response(formatter.disponibilita_to_text(libro, biblioteca),
                        mimetype="text/plain; charset=utf-8")
    copie = libro.disponibilita_in(biblioteca) if biblioteca else libro.copie
    return jsonify({
        "id": libro.id,
        "titolo": libro.titolo,
        "autore": libro.autore,
        "biblioteca_filtro": biblioteca,
        "copie": [c.to_dict() for c in copie],
    })


def _miglior_candidato(libri):
    """Preferisce libri fisici a catalogo con copie reali, poi catalogo, poi qualsiasi."""
    con_copie = [l for l in libri if l.id and l.id.startswith("lo:catalog:") and (l.copie_totali or 0) > 0]
    if con_copie:
        return con_copie[0]
    catalog = [l for l in libri if l.id and l.id.startswith("lo:catalog:")]
    if catalog:
        return catalog[0]
    return libri[0] if libri else None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
