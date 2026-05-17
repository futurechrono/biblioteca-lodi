"""Entrypoint Flask del middleware OPAC Lodi.

Espone:
  GET /api/health         health check
  GET /api/cerca          ricerca libri (q, pagina, formato)
  GET /api/disponibile    domanda one-shot: "X è disponibile a Lodi?"
                          (q, biblioteca, max_edizioni, match, formato)
  GET /api/disponibilita  copie per biblioteca dato l'id catalogo
                          (id, biblioteca, formato)

Tutti gli endpoint accettano CORS da qualunque origine: pensati per essere
chiamati dal Webhook block di Landbot (o da altri chatbot esterni).
"""
from flask import Flask, Response, jsonify, request

from lib import formatter, opac_client
from lib.config import BIBLIOTECA_DEFAULT, MAX_RESULTS_PER_PAGE
from lib.matching import titolo_matcha_query

app = Flask(__name__)


@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


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
    """Endpoint principale per il chatbot.

    Scansiona la prima pagina di risultati OPAC, filtra per attinenza
    titolo↔query, scarica i dettagli in parallelo e aggrega le copie
    disponibili nella biblioteca richiesta.
    """
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"errore": "parametro 'q' obbligatorio"}), 400

    biblioteca = request.args.get("biblioteca", BIBLIOTECA_DEFAULT)
    formato = request.args.get("formato", "json")
    max_edizioni = int(request.args.get("max_edizioni") or MAX_RESULTS_PER_PAGE)
    match_mode = request.args.get("match", "strict")

    try:
        risultato = opac_client.cerca(q)
    except opac_client.OpacError as e:
        return jsonify({"errore": str(e)}), 502

    candidati = [l for l in risultato.risultati if l.id and l.id.startswith("lo:catalog:")]
    scartati_titolo = 0
    if match_mode == "strict":
        pertinenti = [l for l in candidati if titolo_matcha_query(l.titolo, q)]
        scartati_titolo = len(candidati) - len(pertinenti)
        candidati = pertinenti

    catalog_ids = [l.id for l in candidati][:max_edizioni]

    if not catalog_ids:
        if scartati_titolo:
            msg = (f'Per "{q}" il catalogo ha {scartati_titolo} risultati, '
                   "ma nessuno con un titolo attinente alla tua ricerca.")
        else:
            msg = f'Non ho trovato "{q}" nel catalogo.'
        if formato == "testo":
            return Response(msg, mimetype="text/plain; charset=utf-8")
        return jsonify({"query": q, "biblioteca": biblioteca, "messaggio": msg,
                        "edizioni_in_sede": []})

    try:
        dettagli = opac_client.dettagli_in_parallelo(catalog_ids)
    except opac_client.OpacError as e:
        return jsonify({"errore": str(e)}), 502

    edizioni_in_sede = [
        libro for libro in dettagli
        if libro and libro.disponibilita_in(biblioteca)
    ]

    messaggio = formatter.disponibilita_aggregata_to_text(
        query=q, edizioni=edizioni_in_sede,
        biblioteca=biblioteca, totale_esaminate=len(catalog_ids),
    )

    if formato == "testo":
        return Response(messaggio, mimetype="text/plain; charset=utf-8")

    return jsonify({
        "query": q,
        "biblioteca": biblioteca,
        "messaggio": messaggio,
        "edizioni_scansionate": len(catalog_ids),
        "edizioni_in_sede": [
            {
                "id": libro.id,
                "titolo": libro.titolo,
                "autore": libro.autore,
                "anno": libro.anno,
                "copie": [c.to_dict() for c in libro.disponibilita_in(biblioteca)],
            }
            for libro in edizioni_in_sede
        ],
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
