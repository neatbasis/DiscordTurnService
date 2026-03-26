from discord_turn_service.models import AskKind, ChoiceOption
from discord_turn_service.models.turns import AskKind as TurnsAskKind
from discord_turn_service.models.turns import ChoiceOption as TurnsChoiceOption
from interaction_contracts import (
    AnswerTemplate,
    InteractionMode,
    InteractionResult,
    InteractionSpec,
    SlotSpec,
)
from interaction_contracts import (
    AskKind as ContractAskKind,
)
from interaction_contracts import (
    ChoiceOption as ContractChoiceOption,
)


def test_discord_turn_service_ask_kind_comes_from_interaction_contracts() -> None:
    assert AskKind is ContractAskKind
    assert TurnsAskKind is ContractAskKind


def test_discord_turn_service_choice_option_comes_from_interaction_contracts() -> None:
    assert ChoiceOption is ContractChoiceOption
    assert TurnsChoiceOption is ContractChoiceOption


def test_choice_option_aliases_behavior_is_unchanged() -> None:
    option = ChoiceOption(key="accept", label="Accept", aliases=["yes", "go ahead"])

    assert option.key == "accept"
    assert option.label == "Accept"
    assert option.aliases == ["yes", "go ahead"]


def test_slot_spec_valid() -> None:
    slot = SlotSpec(name="destination", description="Where to go", required=True, multi=False)

    assert slot.name == "destination"
    assert slot.description == "Where to go"
    assert slot.required is True
    assert slot.multi is False


def test_answer_template_valid() -> None:
    template = AnswerTemplate(
        id="mission-ready",
        sentences=["Proceed to {destination} via {route}"],
        label="Mission Route",
        slot_bindings={"route": "fastest"},
    )

    assert template.id == "mission-ready"
    assert template.sentences == ["Proceed to {destination} via {route}"]
    assert template.label == "Mission Route"
    assert template.slot_bindings == {"route": "fastest"}


def test_interaction_spec_valid() -> None:
    spec = InteractionSpec(
        id="route-selection",
        prompt="How should we proceed?",
        mode=InteractionMode.MIXED,
        slots=[SlotSpec(name="destination")],
        choices=[ChoiceOption(key="fastest", label="Fastest")],
        templates=[
            AnswerTemplate(
                id="route-template",
                sentences=["Take the {route} path to {destination}"],
            )
        ],
        timeout_seconds=45.0,
    )

    assert spec.id == "route-selection"
    assert spec.mode == InteractionMode.MIXED
    assert len(spec.slots) == 1
    assert len(spec.choices) == 1
    assert len(spec.templates) == 1
    assert spec.timeout_seconds == 45.0


def test_interaction_result_valid() -> None:
    result = InteractionResult(
        interaction_id="route-selection",
        status="answered",
        answer_id="route-template",
        sentence="Take the fastest path to HQ",
        slots={"route": "fastest", "destination": "HQ"},
        channel="discord:dm",
        meta={"turn_id": "turn-123"},
    )

    assert result.interaction_id == "route-selection"
    assert result.status == "answered"
    assert result.answer_id == "route-template"
    assert result.slots["route"] == "fastest"
    assert result.channel == "discord:dm"
