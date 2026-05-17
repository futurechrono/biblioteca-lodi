# biblioteca-lodi

Middleware Python (Flask, deploy serverless su Vercel) che funge da ponte tra
un chatbot **Landbot** e l'OPAC della Biblioteca Comunale di Lodi
(`https://webopac.bibliotechelodi.it`).

Il chatbot in chat fa una domanda all'utente, cattura il titolo del libro
cercato e lo passa al middleware tramite Webhook block. Il middleware
interroga l'OPAC, fa scraping del catalogo, filtra per attinenza titolo e
restituisce un testo pronto da mostrare in chat.

## Architettura

```
Utente ──► Chat Landbot (iframe sul sito o URL pubblica)
              │
              ▼
        Webhook block:
        GET https://biblioteca-lodi.vercel.app/api/disponibile?q=<titolo>&formato=testo
              │
              ▼
        Vercel (Flask) ──► OPAC Lodi (scraping)
                        ── cache in-memory (TTL 5 min)
                        ── parsing HTML (DiscoveryNG)
                        ── filtro attinenza titolo↔query
                        ── aggregazione disponibilità per biblioteca
              │
              ▼
        Risposta in chat
```

## Funzionalità del middleware

- Ricerca libri per query libera (`/api/cerca?q=...&pagina=N`)
- Disponibilità aggregata in una specifica biblioteca (`/api/disponibile?q=...`)
- Dettaglio copie singolo libro (`/api/disponibilita?id=lo:catalog:NNN`)
- Filtro di attinenza titolo↔query con token + stopword italiane (`lib/matching.py`)
- Recupero dettagli in parallelo per scansione veloce delle edizioni
- Output disponibile in JSON o testo (per chat)

## Endpoint

| Path | Descrizione | Parametri principali |
|---|---|---|
| `/api/health` | Health check | — |
| `/api/cerca` | Ricerca libri sulla prima pagina | `q`, `pagina`, `formato` |
| `/api/disponibile` | "X è disponibile a Lodi?" | `q`, `biblioteca`, `max_edizioni`, `match`, `formato` |
| `/api/disponibilita` | Copie di un titolo per biblioteca | `id`, `biblioteca`, `formato` |

`formato` accetta `json` (default) o `testo`. Per Landbot serve `formato=testo`.

## Sviluppo locale

Richiede Python ≥ 3.10.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py        # Flask dev server su http://localhost:8000
```

## Deploy su Vercel

1. Push del repo su GitHub.
2. Import del repo su Vercel: rileva automaticamente Flask via `app.py`.
3. (Opzionale) Configura le env in **Settings → Environment Variables**
   secondo `.env.example`.
4. L'URL pubblico è del tipo `https://biblioteca-lodi.vercel.app`.

## Configurazione chatbot Landbot

Vedi guida passo passo in [`LANDBOT.md`](LANDBOT.md).

## Note

- L'OPAC non espone API pubbliche: tutto avviene via scraping del DOM
  (DiscoveryNG di Comperio). I selettori sono isolati in `lib/parser.py`.
- Progetto a scopo didattico universitario.
