from discord_turn_service.models import AskKind, ChoiceOption
from discord_turn_service.models.turns import AskKind as TurnsAskKind
from discord_turn_service.models.turns import ChoiceOption as TurnsChoiceOption
from interaction_contracts import AskKind as ContractAskKind
from interaction_contracts import ChoiceOption as ContractChoiceOption


def test_discord_turn_service_ask_kind_comes_from_interaction_contracts() -> None:
    assert AskKind is ContractAskKind
    assert TurnsAskKind is ContractAskKind


def test_discord_turn_service_choice_option_comes_from_interaction_contracts() -> None:
    assert ChoiceOption is ContractChoiceOption
    assert TurnsChoiceOption is ContractChoiceOption
