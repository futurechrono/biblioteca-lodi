from lib.formatter import disponibilita_to_text, lista_to_text
from lib.models import Copia, Libro, RisultatoRicerca


def test_lista_vuota():
    r = RisultatoRicerca(query="xyz", pagina=1, totale=0)
    assert "Non ho trovato" in lista_to_text(r)


def test_lista_con_risultati():
    r = RisultatoRicerca(
        query="1984",
        pagina=1,
        totale=2,
        risultati=[
            Libro(id="1", titolo="1984", autore="Orwell, George", anno="2017"),
            Libro(id="2", titolo="1984: graphic novel", autore="Orwell"),
        ],
    )
    out = lista_to_text(r)
    assert "1984" in out and "Orwell" in out and "(2017)" in out


def test_disponibilita_libro_disponibile_a_lodi():
    libro = Libro(id="lo:catalog:1", titolo="1984", autore="Orwell, George",
                  copie=[
                      Copia(biblioteca="Lodi-Biblioteca Comunale Laudense",
                            stato="Su scaffale", prestabilita="Disponibile",
                            collocazione="823.9 ORW"),
                  ])
    out = disponibilita_to_text(libro, "Lodi")
    assert "DISPONIBILE" in out
    assert "823.9 ORW" in out


def test_disponibilita_libro_in_prestito_a_lodi():
    libro = Libro(id="lo:catalog:1", titolo="1984", autore="Orwell, George",
                  copie=[Copia(biblioteca="Lodi-Biblioteca Comunale Laudense",
                               stato="In prestito", rientra="16/06/2026")])
    out = disponibilita_to_text(libro, "Lodi")
    assert "IN PRESTITO" in out
    assert "16/06/2026" in out


def test_disponibilita_libro_non_a_lodi():
    libro = Libro(id="lo:catalog:1", titolo="1984",
                  copie=[Copia(biblioteca="Codogno-Biblioteca Civica", stato="Su scaffale", prestabilita="Disponibile")])
    out = disponibilita_to_text(libro, "Lodi")
    assert "non è presente" in out
