from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LegalParty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    party_id: str = Field(pattern=r"^SYN-PARTY-[0-9]+$")
    name: str = Field(min_length=2)
    role: Literal["disclosing_party", "receiving_party", "service_provider", "customer"]
    jurisdiction: str = Field(min_length=2)


class ContractClause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clause_id: int = Field(ge=1)
    title: str = Field(min_length=2)
    body: str = Field(min_length=8)
    risk_flag: Literal["none", "medium", "high"] = "none"


class LegalContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: str = Field(pattern=r"^LEG-[A-Z0-9-]+$")
    document_type: Literal["nda", "service-agreement", "msa"]
    title: str = Field(min_length=4)
    language: Literal["en-IN", "hi-IN", "gu-IN"] = "en-IN"
    effective_date: date
    term_months: int = Field(ge=1, le=120)
    governing_law: str = Field(min_length=2)
    parties: list[LegalParty] = Field(min_length=2, max_length=2)
    clauses: list[ContractClause] = Field(min_length=3, max_length=12)
    confidentiality: bool = True
    synthetic: bool = True
    disclaimer: str = "Synthetic legal contract. Not legal advice and not an executed agreement."

    @model_validator(mode="after")
    def validate_structure(self) -> "LegalContract":
        if self.parties[0].party_id == self.parties[1].party_id:
            raise ValueError("contract parties must be distinct")
        if [clause.clause_id for clause in self.clauses] != list(range(1, len(self.clauses) + 1)):
            raise ValueError("clause IDs must be sequential")
        if any(not clause.body.strip() for clause in self.clauses):
            raise ValueError("clause bodies must be non-empty")
        return self
