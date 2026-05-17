import pytest

from lib.matching import titolo_matcha_query


@pytest.mark.parametrize("titolo,query,expected", [
    # match esatto con accento e ignorando articoli
    ("Lo sviluppo è libertà",         "lo sviluppo e liberta",     True),
    ("Lo sviluppo è libertà",         "sviluppo libertà",          True),

    # libri non attinenti che l'OPAC ritorna per ricerca full-text
    ("Capitalismo e libertà",         "lo sviluppo e liberta",     False),
    ("Libertà e moderazione",         "lo sviluppo e liberta",     False),
    ("Libertà e innovazione",         "lo sviluppo e liberta",     False),
    ("Storia della libertà",          "lo sviluppo e liberta",     False),

    # case insensitivity
    ("1984",                          "1984",                      True),
    ("Il nome della rosa",            "nome della rosa",           True),
    ("Il nome della rosa",            "nome della tulipano",       False),

    # query vuota → match
    ("Qualsiasi cosa",                "",                          True),

    # punteggiatura
    ("Aaa!",                          "aaa",                       True),
])
def test_titolo_matcha_query(titolo, query, expected):
    assert titolo_matcha_query(titolo, query) is expected
