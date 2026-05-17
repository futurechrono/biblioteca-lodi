import os

OPAC_BASE_URL = os.getenv("OPAC_BASE_URL", "https://webopac.bibliotechelodi.it")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
HTTP_TIMEOUT_SECONDS = int(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
RESULTS_PER_PAGE = int(os.getenv("RESULTS_PER_PAGE", "10"))

BIBLIOTECA_DEFAULT = os.getenv("BIBLIOTECA_DEFAULT", "Lodi-Biblioteca Comunale Laudense")

USER_AGENT = (
    "biblioteca-lodi-bot/1.0 (progetto universitario; "
    "contatto: studente@example.com)"
)
