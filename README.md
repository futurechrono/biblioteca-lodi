# biblioteca-lodi

Middleware Python (serverless su Vercel) che fa da ponte tra un chatbot
Pandorabots e l'OPAC della Biblioteca Comunale di Lodi
(`https://webopac.bibliotechelodi.it`).

Il bot AIML chiama il middleware tramite `<sraix>`, il middleware interroga
l'OPAC, fa parsing dei risultati e restituisce una risposta già pronta per
essere mostrata in chat.

## Architettura

```
Frontend HTML (GitHub Pages)
        │
        ▼
Vercel /api/chat
        │
        ├──► Pandorabots Talk API   (NLP: estrae il titolo dalla frase)
        │
        └──► OPAC Lodi              (ricerca + dettaglio + filtro disponibilità)
```

Il frontend statico chiama un solo endpoint del middleware Vercel. Il middleware
delega a Pandorabots l'analisi linguistica (riconoscimento intent + estrazione
titolo), poi interroga l'OPAC e aggrega la risposta. Questo schema evita le
limitazioni di CORS e di SRAIX esterno sul piano free di Pandorabots.

## Funzionalità

- Ricerca libri per query libera (`/api/cerca?q=...`)
- Ricerca per autore o titolo (`/api/cerca?q=...&campo=autore|titolo`)
- Paginazione dei risultati (`&pagina=2`)
- Dettaglio disponibilità di un libro (`/api/disponibilita?id=...`)
- Cache in-memory con TTL per non sovraccaricare l'OPAC
- Output in due formati: `json` (default) o `testo` (pronto per Pandorabots)

## Endpoint

| Metodo | Path                  | Descrizione                          |
|--------|-----------------------|--------------------------------------|
| GET    | `/api/health`         | Health check                         |
| GET    | `/api/cerca`          | Ricerca libri                        |
| GET    | `/api/disponibilita`  | Disponibilità copie di un libro      |

Parametri di `/api/cerca`:

- `q` (obbligatorio): query di ricerca
- `campo` (opzionale): `libero` (default), `titolo`, `autore`
- `pagina` (opzionale): intero, default 1
- `formato` (opzionale): `json` (default) o `testo`

## Sviluppo locale

Richiede Python ≥ 3.10 (il codice usa la sintassi `X | None`).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py        # Flask in dev mode su http://localhost:8000
```

Oppure senza Vercel CLI, eseguendo il singolo modulo per test rapidi:

```bash
python -m lib.opac_client "pippo"
```

## Deploy

1. Push del repo su GitHub.
2. Import del repo su Vercel.
3. Vercel rileva automaticamente la cartella `api/` come serverless functions.
4. L'URL pubblico (es. `https://biblioteca-lodi.vercel.app`) va configurato
   come Custom Service in Pandorabots.

## Integrazione Pandorabots

Esempi di category AIML in [`aiml/biblioteca.aiml`](aiml/biblioteca.aiml).

## Note

- L'OPAC non espone API pubbliche documentate: il parsing è basato su
  scraping HTML. La logica di parsing è isolata in `lib/parser.py` per
  facilitare l'aggiornamento se il layout dell'OPAC cambia.
- Progetto a scopo didattico universitario.
