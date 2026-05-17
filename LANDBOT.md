# Configurazione del chatbot su Landbot

Guida operativa per creare il bot "Biblioteca di Lodi" su [Landbot](https://landbot.io)
collegandolo al middleware Vercel.

Prerequisiti:
- Il middleware è già deployato su Vercel (es. `https://biblioteca-lodi.vercel.app`).
- L'endpoint `/api/disponibile?q=1984&formato=testo` risponde con del testo
  sensato (verificalo prima di proseguire).

## 1. Crea un account Landbot

1. Vai su [landbot.io](https://landbot.io) → **Sign up**.
2. Scegli il piano **Sandbox / Free** (100 conversazioni/mese, sufficiente per
   il progetto e per la demo al docente).
3. Conferma l'email e accedi al dashboard.

## 2. Crea un nuovo bot

1. Dashboard → **Build a chatbot** (oppure **+ New Bot**).
2. Seleziona il tipo **Website Bot** (è quello con widget e URL pubblica).
3. Parti da un template vuoto: **Build from scratch**.
4. Dai un nome al bot, es. *"Bot Biblioteca Lodi"*.

## 3. Costruisci il flow

Il flow è una catena di blocchi che parte dal "Welcome" automatico.
Trascina i blocchi dalla colonna di sinistra sulla canvas.

### Blocco 1 — Welcome (già presente)

Modifica il messaggio iniziale:

> Ciao! Sono l'assistente virtuale della biblioteca di Lodi.
> Posso dirti se un libro è disponibile alla Biblioteca Comunale Laudense.

### Blocco 2 — Question (Ask a Question)

- Tipo: **Question → Text**
- Messaggio: *"Quale libro stai cercando? Scrivi il titolo."*
- **Save answer in variable**: crea una nuova variabile chiamata `@libro`
  (tipo: testo).

Collega l'output del blocco Welcome a questo blocco.

### Blocco 3 — Webhook (chiamata al middleware)

- Trascina un blocco **Webhooks** (sezione "Advanced" o "Integrations").
- Configuralo così:

| Campo | Valore |
|---|---|
| Method | `GET` |
| URL | `https://biblioteca-lodi.vercel.app/api/disponibile` |
| URL parameters | `q` = `@libro` &nbsp;·&nbsp; `formato` = `testo` |
| Headers | (lasciare vuoto) |
| Body | (lasciare vuoto) |

Nella sezione **Save response** / **Test webhook**:

1. Clicca **Test the request**: Landbot fa una chiamata di prova
   (puoi inserire un valore di test per `@libro`, es. `1984`).
2. Nella risposta che appare, clicca sul **body** della response
   e mappa l'intero corpo della risposta su una nuova variabile `@risposta`
   (tipo: testo).

> Se Landbot non riesce a parsare la risposta come JSON e va in errore,
> assicurati di aver passato `formato=testo`: il middleware risponderà con
> `Content-Type: text/plain`, che Landbot tratta come stringa.

### Blocco 4 — Send a Message

- Tipo: **Send a Message → Text**
- Messaggio:
  ```
  @risposta
  ```
  (Landbot sostituirà la variabile col testo restituito dal middleware.)

### Blocco 5 — Loop opzionale

- Aggiungi un blocco **Buttons** dopo il messaggio:
  - Bottone 1: *"Cerca un altro libro"* → torna al Blocco 2 (Question)
  - Bottone 2: *"Ho finito, grazie"* → blocco **Close Bot** o messaggio
    di chiusura.

Salva il flow (in alto a destra: **Save** / **Publish**).

## 4. Pubblicazione

In alto a destra clicca **Publish**. Poi:

- **Share → Landing page**: ottieni una URL pubblica pronta da inviare
  al docente, es. `https://landbot.online/v3/H-XXXXXX/index.html`.
- **Embed**: ottieni uno snippet HTML/JS per integrarlo dentro un sito.
  Lo puoi mettere in una pagina GitHub Pages o ovunque.

## 5. Test

Apri la URL pubblica della landing page. La conversazione dovrebbe procedere:

```
Bot: Ciao! Sono l'assistente virtuale della biblioteca di Lodi...
Bot: Quale libro stai cercando? Scrivi il titolo.
Tu: 1984
[Landbot chiama https://biblioteca-lodi.vercel.app/api/disponibile?q=1984&formato=testo]
Bot: Per "1984" alla Lodi-Biblioteca Comunale Laudense:
     trovate 2 edizioni con copie in sede (1 disponibili, 1 in prestito).

     DISPONIBILI:
     - 1984 di Orwell, George (2000) — collocazione 823.9 ORW

     IN PRESTITO:
     - 1984 di Orwell, George (2017), rientra il 16/06/2026
Bot: [Cerca un altro libro] [Ho finito, grazie]
```

## 6. Troubleshooting

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| Webhook timeout in Landbot | Vercel cold start lento | Riprova; se persiste alza il timeout in Landbot |
| `(nessuna risposta)` in chat | Variabile `@risposta` non mappata | Rifai il "Test the request" e rimappa il body |
| `Errore parametro q obbligatorio` | Variabile `@libro` vuota | Controlla che il Question block salvi correttamente |
| "Non ho trovato X nel catalogo" | Titolo troppo specifico o errore di battitura | Normale: l'OPAC è esigente |
