"""Client minimale per la Pandorabots Talk API (AIaaS).

Endpoint POST https://api.pandorabots.com/talk/{app_id}/{botname}?user_key=...
Body: input=<frase utente>&client_name=<sessione>

Le credenziali sono lette da variabili d'ambiente:
  PANDORABOTS_APP_ID
  PANDORABOTS_BOT_NAME
  PANDORABOTS_USER_KEY
"""
from __future__ import annotations

import os

import requests

from .config import HTTP_TIMEOUT_SECONDS


class PandorabotsError(Exception):
    pass


def configurato() -> bool:
    return all(os.getenv(k) for k in ("PANDORABOTS_APP_ID", "PANDORABOTS_BOT_NAME", "PANDORABOTS_USER_KEY"))


def talk(message: str, session_id: str = "anon") -> str:
    app_id = os.environ["PANDORABOTS_APP_ID"]
    bot_name = os.environ["PANDORABOTS_BOT_NAME"]
    user_key = os.environ["PANDORABOTS_USER_KEY"]
    url = f"https://api.pandorabots.com/talk/{app_id}/{bot_name}"
    try:
        resp = requests.post(
            url,
            params={"user_key": user_key},
            data={"input": message, "client_name": session_id, "sessionid": session_id},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise PandorabotsError(f"Errore Pandorabots: {e}") from e
    data = resp.json() if resp.content else {}
    responses = data.get("responses") or []
    return responses[0].strip() if responses else ""
