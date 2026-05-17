from pathlib import Path

from lib.parser import parse_dettaglio, parse_risultati

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_risultati_estrae_libri_e_totale():
    html = (FIXTURES / "risultati_aaa.html").read_text(encoding="utf-8")
    r = parse_risultati(html, query="aaa", pagina=1)

    assert r.totale == 15
    assert len(r.risultati) == 3

    primo = r.risultati[0]
    assert primo.id == "lo:catalog:196797"
    assert primo.autore == "Busi, Aldo"
    assert primo.editore == "Bompiani"
    assert primo.luogo == "Milano"
    assert primo.anno == "2010"
    assert primo.copie_totali == 2
    assert primo.disponibile is True


def test_parse_dettaglio_1984_con_copie():
    html = (FIXTURES / "dettaglio_1984.html").read_text(encoding="utf-8")
    libro = parse_dettaglio(html)

    assert libro is not None
    assert libro.id == "lo:catalog:264315"
    assert libro.titolo == "1984"
    assert libro.autore == "Orwell, George"
    assert libro.editore == "Mondadori"
    assert libro.copie_totali == 7
    assert libro.copie_in_prestito == 2
    assert len(libro.copie) == 3


def test_disponibilita_in_lodi_in_prestito():
    libro = parse_dettaglio((FIXTURES / "dettaglio_1984.html").read_text(encoding="utf-8"))
    a_lodi = libro.disponibilita_in("Lodi-Biblioteca Comunale Laudense")
    assert len(a_lodi) == 1
    c = a_lodi[0]
    assert c.in_prestito is True
    assert c.disponibile is False
    assert c.rientra == "16/06/2026"


def test_disponibilita_altrove_disponibile():
    libro = parse_dettaglio((FIXTURES / "dettaglio_1984.html").read_text(encoding="utf-8"))
    a_corte = libro.disponibilita_in("Corte Palasio")
    assert len(a_corte) == 1
    assert a_corte[0].disponibile is True
    assert a_corte[0].stato == "Su scaffale"
