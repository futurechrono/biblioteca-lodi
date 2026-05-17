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
import re

from flask import Flask, Response, jsonify, request, send_from_directory

from lib import formatter, opac_client, pandorabots
from lib.config import BIBLIOTECA_DEFAULT, MAX_RESULTS_PER_PAGE
from lib.matching import titolo_matcha_query

app = Flask(__name__, static_folder="frontend", static_url_path="")

# Marker che Pandorabots usa nelle template per segnalare una ricerca libro.
# L'AIML risponde "TITLE:<star/>" → qui estraiamo il titolo e chiamiamo l'OPAC.
_TITLE_RE = re.compile(r"^\s*TITLE\s*:\s*(?P<titolo>.+?)\s*$", re.IGNORECASE)


@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.get("/")
def index():
    return send_from_directory("frontend", "index.html")


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
    """Scansiona la prima pagina di risultati, scarica i dettagli in parallelo
    e aggrega la disponibilità nella biblioteca richiesta."""
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"errore": "parametro 'q' obbligatorio"}), 400

    biblioteca = request.args.get("biblioteca", BIBLIOTECA_DEFAULT)
    formato = request.args.get("formato", "testo")
    max_edizioni = int(request.args.get("max_edizioni") or MAX_RESULTS_PER_PAGE)
    match_mode = request.args.get("match", "strict")  # "strict" | "loose"

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

    if formato == "testo":
        testo = formatter.disponibilita_aggregata_to_text(
            query=q, edizioni=edizioni_in_sede,
            biblioteca=biblioteca, totale_esaminate=len(catalog_ids),
        )
        return Response(testo, mimetype="text/plain; charset=utf-8")

    return jsonify({
        "query": q,
        "biblioteca": biblioteca,
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


@app.get("/api/chat")
@app.post("/api/chat")
def chat():
    """Punto di ingresso unico per il frontend.

    1. Riceve la frase utente (`msg`).
    2. La passa a Pandorabots che fa NLP e risponde "TITLE:<titolo>" se
       riconosce una richiesta di disponibilità libro, oppure una frase
       normale (saluti, fallback).
    3. Se è una richiesta libro, fa il lookup sull'OPAC e restituisce la
       risposta aggregata; altrimenti rilancia la frase di Pandorabots.
    """
    msg = (request.values.get("msg") or "").strip()
    if not msg:
        return jsonify({"errore": "parametro 'msg' obbligatorio"}), 400

    session_id = request.values.get("session", "anon")
    biblioteca = request.values.get("biblioteca", BIBLIOTECA_DEFAULT)

    if not pandorabots.configurato():
        return jsonify({
            "errore": "Pandorabots non configurato. Definisci PANDORABOTS_APP_ID, "
                      "PANDORABOTS_BOT_NAME, PANDORABOTS_USER_KEY tra le env di Vercel."
        }), 500

    try:
        bot_reply = pandorabots.talk(msg, session_id=session_id)
    except pandorabots.PandorabotsError as e:
        return jsonify({"errore": str(e)}), 502

    m = _TITLE_RE.match(bot_reply or "")
    if not m:
        return jsonify({"intent": "chat", "risposta": bot_reply or ""})

    titolo = m.group("titolo")
    risposta_disp = _disponibilita_aggregata(titolo, biblioteca)
    return jsonify({
        "intent": "ricerca_libro",
        "titolo_estratto": titolo,
        "risposta": risposta_disp,
    })


def _disponibilita_aggregata(query: str, biblioteca: str) -> str:
    """Stessa logica di /api/disponibile ma riusabile internamente."""
    try:
        risultato = opac_client.cerca(query)
    except opac_client.OpacError as e:
        return f"Errore contattando il catalogo: {e}"

    candidati = [l for l in risultato.risultati if l.id and l.id.startswith("lo:catalog:")]
    pertinenti = [l for l in candidati if titolo_matcha_query(l.titolo, query)]
    scartati = len(candidati) - len(pertinenti)
    catalog_ids = [l.id for l in pertinenti][:MAX_RESULTS_PER_PAGE]

    if not catalog_ids:
        if scartati:
            return (f'Per "{query}" il catalogo ha {scartati} risultati, '
                    "ma nessuno con un titolo attinente alla tua ricerca.")
        return f'Non ho trovato "{query}" nel catalogo.'

    try:
        dettagli = opac_client.dettagli_in_parallelo(catalog_ids)
    except opac_client.OpacError as e:
        return f"Errore contattando il catalogo: {e}"

    edizioni_in_sede = [l for l in dettagli if l and l.disponibilita_in(biblioteca)]
    return formatter.disponibilita_aggregata_to_text(
        query=query, edizioni=edizioni_in_sede,
        biblioteca=biblioteca, totale_esaminate=len(catalog_ids),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
