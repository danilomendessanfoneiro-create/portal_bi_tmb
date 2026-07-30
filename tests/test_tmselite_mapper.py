"""TMS Elite mapper unit tests."""

from __future__ import annotations

from app.integrations.tmselite.mapper import map_delivery_item


def test_map_remessa_numero_as_key():
    item = {
        "remessa": {"numero": 27479272, "status": "EM ROTA"},
        "documentos": {
            "numero": 34437,
            "serie": 1,
            "valor": 592.83,
            "qtdeVolumes": 1,
            "peso": {"informado": 22.9, "taxado": None},
        },
        "destinatario": {"nome": "CLIENTE 173", "cidade": "BH", "uf": "MG"},
        "unidadeEntrega": {"sigla": "MATRIZ"},
        "prazo": {"atual": "2026-07-09T00:00:00"},
        "agendamento": {"atual": None},
        "fluxo": {
            "cadastro": "2026-07-01T14:05:20.137",
            "entrega": None,
            "cancelamento": None,
        },
        "remetente": {"nome": "BRB", "cidade": "Campinas", "uf": "SP"},
        "ocorrencia": {"observacao": None},
        "recebedor": {"nome": None},
    }
    rec = map_delivery_item(item)
    assert rec.remessa_numero == "27479272"
    assert rec.nro_entrega == "27479272"
    assert rec.nota_fiscal == "34437/1"
    assert rec.filial == "MATRIZ"
    assert rec.cliente == "CLIENTE 173"
    assert rec.valor_total == 592.83
