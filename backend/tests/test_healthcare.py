from app.domain.healthcare import MedicalNote
from app.services.healthcare_generation import OfflineHealthcareGenerator


def test_healthcare_generation_is_deterministic_and_clinically_consistent() -> None:
    generator = OfflineHealthcareGenerator()

    first = generator.generate(count=3, seed=42)
    second = generator.generate(count=3, seed=42)

    assert all(isinstance(note, MedicalNote) for note in first)
    assert [note.model_dump(mode="json") for note in first] == [note.model_dump(mode="json") for note in second]
    assert len({note.note_id for note in first}) == 3
    assert all(note.synthetic is True for note in first)
    assert all(note.diagnoses and note.soap.assessment for note in first)
    assert all(note.patient.name.startswith("Patient-") for note in first)


def test_healthcare_profile_and_medication_controls_are_applied() -> None:
    notes = OfflineHealthcareGenerator().generate(
        count=8,
        seed=42,
        clinical_profile="respiratory",
        include_medications=False,
    )

    assert all(note.diagnoses[0].icd10_code.startswith("J") for note in notes)
    assert all(note.medications == [] for note in notes)
