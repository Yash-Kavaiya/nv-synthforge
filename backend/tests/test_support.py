from __future__ import annotations

import pytest

from app.services.quality import validate_support_conversation
from app.services.support_generation import OfflineSupportGenerator

_ARCS = ("recovery", "steady-positive", "escalation")


def test_support_generation_is_deterministic() -> None:
    generator = OfflineSupportGenerator()

    first = generator.generate(3, seed=314, industry="mixed", sentiment_arc="recovery", max_turns=8)
    second = generator.generate(3, seed=314, industry="mixed", sentiment_arc="recovery", max_turns=8)

    assert [conversation.model_dump(mode="json") for conversation in first] == [
        conversation.model_dump(mode="json") for conversation in second
    ]
    assert len({conversation.conversation_id for conversation in first}) == 3


@pytest.mark.parametrize("arc", _ARCS)
@pytest.mark.parametrize("max_turns", range(4, 11))
def test_support_conversations_are_valid_for_every_arc_and_turn_length(arc: str, max_turns: int) -> None:
    conversations = OfflineSupportGenerator().generate(
        4, seed=7, industry="mixed", sentiment_arc=arc, max_turns=max_turns
    )

    for conversation in conversations:
        report = validate_support_conversation(conversation)
        assert report.valid, (arc, max_turns, [violation.rule for violation in report.violations])
        assert report.score == 1.0
        assert [turn.turn_id for turn in conversation.turns] == list(range(1, len(conversation.turns) + 1))
        assert all(turn.timestamp >= conversation.started_at for turn in conversation.turns)
        assert [turn.timestamp for turn in conversation.turns] == sorted(turn.timestamp for turn in conversation.turns)


@pytest.mark.parametrize("max_turns", range(4, 11))
def test_support_honors_max_turns_upper_bound_and_ends_on_agent(max_turns: int) -> None:
    conversation = OfflineSupportGenerator().generate(
        1, seed=11, industry="telecom", sentiment_arc="recovery", max_turns=max_turns
    )[0]

    # Conversations must end on an agent turn, so the largest even count <= max_turns is used.
    expected = max_turns if max_turns % 2 == 0 else max_turns - 1
    assert len(conversation.turns) == expected
    assert conversation.turns[0].role == "customer"
    assert conversation.turns[-1].role == "agent"
    assert len(conversation.turns) % 2 == 0


@pytest.mark.parametrize("arc", _ARCS)
def test_support_resolution_status_matches_arc(arc: str) -> None:
    conversation = OfflineSupportGenerator().generate(
        1, seed=99, industry="banking", sentiment_arc=arc, max_turns=10
    )[0]

    if arc == "escalation":
        assert conversation.resolution_status == "escalated"
    else:
        assert conversation.resolution_status == "resolved"
        assert conversation.turns[-1].sentiment >= 0.5
