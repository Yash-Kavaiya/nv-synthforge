from __future__ import annotations

import pytest

from app.services.legal_generation import OfflineLegalGenerator
from app.services.quality import validate_legal_contract

_TYPES = ("nda", "service-agreement", "msa")


def test_legal_generation_is_deterministic() -> None:
    generator = OfflineLegalGenerator()
    first = generator.generate(3, seed=91, language="gu-IN", document_type="mixed", max_clauses=6)
    second = generator.generate(3, seed=91, language="gu-IN", document_type="mixed", max_clauses=6)
    assert [item.model_dump(mode="json") for item in first] == [item.model_dump(mode="json") for item in second]
    assert all(validate_legal_contract(item).score == 1.0 for item in first)
    assert any("\u0a80" <= character <= "\u0aff" for character in first[0].clauses[0].body)


@pytest.mark.parametrize("document_type", _TYPES)
def test_legal_contracts_are_valid_for_every_document_type(document_type: str) -> None:
    contracts = OfflineLegalGenerator().generate(4, seed=17, document_type=document_type, max_clauses=5)
    for contract in contracts:
        report = validate_legal_contract(contract)
        assert report.valid
        assert report.score == 1.0
        assert contract.document_type == document_type
        assert len(contract.parties) == 2
        assert contract.parties[0].party_id != contract.parties[1].party_id
        assert [clause.clause_id for clause in contract.clauses] == list(range(1, len(contract.clauses) + 1))


@pytest.mark.parametrize("max_clauses", range(3, 9))
def test_legal_honors_max_clauses(max_clauses: int) -> None:
    contract = OfflineLegalGenerator().generate(1, seed=5, document_type="nda", max_clauses=max_clauses)[0]
    assert len(contract.clauses) == max_clauses
