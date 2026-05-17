from dataclasses import dataclass, asdict, field


@dataclass
class Copia:
    biblioteca: str | None
    collocazione: str | None = None
    inventario: str | None = None
    stato: str | None = None           # "Su scaffale", "In prestito", ...
    prestabilita: str | None = None    # "Disponibile" o vuoto
    rientra: str | None = None         # data di rientro se in prestito

    @property
    def in_prestito(self) -> bool:
        return (self.stato or "").strip().lower() == "in prestito"

    @property
    def disponibile(self) -> bool:
        return (self.prestabilita or "").strip().lower() == "disponibile"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["in_prestito"] = self.in_prestito
        d["disponibile"] = self.disponibile
        return d


@dataclass
class Libro:
    id: str | None                 # es. "lo:catalog:264315"
    titolo: str
    autore: str | None = None
    editore: str | None = None
    luogo: str | None = None
    anno: str | None = None
    edizione: str | None = None
    tipo: str | None = None
    abstract: str | None = None
    copertina_url: str | None = None
    url_dettaglio: str | None = None
    copie_totali: int | None = None
    copie_in_prestito: int | None = None
    prenotazioni: int | None = None
    copie: list[Copia] = field(default_factory=list)

    @property
    def disponibile(self) -> bool | None:
        if self.copie_totali is None or self.copie_in_prestito is None:
            return None
        return self.copie_totali > self.copie_in_prestito

    def disponibilita_in(self, biblioteca: str) -> list[Copia]:
        """Copie nella biblioteca il cui nome contiene `biblioteca` (case-insensitive)."""
        k = biblioteca.lower().strip()
        return [c for c in self.copie if c.biblioteca and k in c.biblioteca.lower()]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["disponibile"] = self.disponibile
        d["copie"] = [c.to_dict() for c in self.copie]
        return d


@dataclass
class RisultatoRicerca:
    query: str
    pagina: int
    totale: int
    risultati: list[Libro] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "pagina": self.pagina,
            "totale": self.totale,
            "risultati": [l.to_dict() for l in self.risultati],
        }
