from typing import List, Tuple

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from .graph_state import ChooseActionGraphState
from src.models.game_history import GameHistory
from src.models.players.base import BasePlayer
from src.models.card import Card

choose_action_function = [
    {
        "type": "function",
        "function": {
            "name": "choose_action",
            "description": "This function is used to select one action from the list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [],
                        "description": "This property returns the name of selected action."
                    }
                },
                "required": ["action"]
            }
        }
    }
]

choose_target_player_function = [
    {
        "type": "function",
        "function": {
            "name": "choose_player",
            "description": "This function is used to select one target player from the list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player": {
                        "type": "string",
                        "enum": [],
                        "description": "This property returns the name of selected player."
                    }
                },
                "required": ["player"]
            }
        }
    }
]

determine_challenge_function = [
    {
        "type": "function",
        "function": {
            "name": "determine_challenge",
            "description": "This function is used to determine challenge against specific player or not",
            "parameters": {
                "type": "object",
                "properties": {
                    "challenge": {
                        "type": "string",
                        "enum": ["true", "false"],
                        "description": "This property returns true when you determine to challenge other player. And returns false when you determine do not challenge other player"
                    }
                },
                "required": ["challenge"]
            }
        }
    }
]

determine_counter_function = [
    {
        "type": "function",
        "function": {
            "name": "determine_counter",
            "description": "This function is used to determine counter current player's action or not.",
            "parameters": {
                "type": "object",
                "properties": {
                    "counter": {
                        "type": "string",
                        "enum": ["true", "false"],
                        "description": "This property returns true when you determine to counter player's action. And returns false when you determine do not counter the player."
                    }
                },
                "required": ["counter"]
            }
        }
    }
]

remove_card_function = [
    {
        "type": "function",
        "function": {
            "name": "remove_card",
            "description": "This function is used to determine which card will be discarded.",
            "parameters": {
                "type": "object",
                "properties": {
                    "card": {
                        "type": "string",
                        "enum": [],
                        "description": "This property returns the name of the card that should be discarded."
                    }
                },
                "required": ["card"]
            }
        }
    }
]


choose_exchange_cards_function = [
    {
        "type": "function",
        "function": {
            "name": "choose_exchange_card",
            "description": "This function is used to determine which cards should be exchanged and send back to the deck. You need to choose two cards from the list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first": {
                        "type": "string",
                        "enum": [],
                        "description": "This property returns the name of the first card you wanna return to the deck."
                    },
                    "second": {
                        "type": "string",
                        "enum": [],
                        "description": "This property returns the name of the second card you wanna return to the deck."
                    }
                },
                "required": ["first", "second"]
            }
        }
    }
]


def entry_node(state: ChooseActionGraphState) -> ChooseActionGraphState:
    return state


def check_coup(state: ChooseActionGraphState) -> bool:
    """Checks if the player's coins are greater than or equal to 10."""
    return state.player.coins >= 10


def select_coup_target_node(state: ChooseActionGraphState) -> ChooseActionGraphState:
    """Selects a target player for the Coup action."""
    other_player_names = [str(player) for player in state.other_players]
    selected_action = state.player.available_actions()[0]
    cards = [str(card) for card in state.player.cards]
    coins = state.player.coins
    game_history = game_history_to_str(state.game_history)

    prompt = (
        f"You are professional coup game player called {state.player}. You selected target player for coup action. And now you need to determine target player.\n"
        f"You need to choose one player from {other_player_names}\n"
        f"You have {cards} on the hand and {coins} coins."

        "Here are previous game histories. You need to analyze this history and make the best decision\n"
        f"{game_history}"
    )

    model = ChatOpenAI(
        model="gpt-4o-2024-08-06",
    )

    choose_target_player_function[0]["function"]["parameters"]["properties"]["player"]["enum"] = other_player_names
    choose_target_model = model.bind_tools(choose_target_player_function, tool_choice="choose_player")
    messages = [SystemMessage(prompt)]

    tool_call = choose_target_model.invoke(messages).tool_calls
    selected_player_name = tool_call[0]['args']['player']
    selected_target = next((player for player in state.other_players if str(player) == selected_player_name), None)
    state.selected_target = selected_target
    state.selected_action = selected_action
    return state


def game_history_to_str(game_history: GameHistory) -> str:
    """Returns the game history as a readable string."""
    output = ""
    for record in game_history.history:
        output += f"Turn {record.turn}:\n"
        output += f"  Current Player: {record.current_player}\n"
        for message in record.messages:
            output += f"    {message}\n"
        if record.final_state:
            output += "  Final State:\n"
            for player_state in record.final_state.player_states:
                output += f"    {player_state.name}: Coins - {player_state.number_of_coins}, Cards - {player_state.number_of_cards}\n"
            output += f"    Deck: {record.final_state.number_of_cards_in_deck} cards\n"
            output += f"    Treasury: {record.final_state.number_of_coins_in_treasury} coins\n"

    return output


def select_action_node(state: ChooseActionGraphState) -> ChooseActionGraphState:
    """Selects an action from the available actions."""
    available_actions = state.player.available_actions()
    state.selected_action = None
    state.other_players = None
    state.selected_target = None

    game_history = game_history_to_str(state.game_history)
    action_names = [str(action) for action in available_actions]
    cards = [str(card) for card in state.player.cards]
    coins = state.player.coins

    prompt = (
        f"You are professional coup game player called {state.player}. And now is your turn. You need to choose an action from {action_names}\n"
        f"You have {cards} on the hand and {coins} coins."

        "Here are previous game histories. You need to analyze this history and make the best decision\n"
        f"{game_history}"
    )

    model = ChatOpenAI(
        model="gpt-4o-2024-08-06",
    )

    choose_action_function[0]["function"]["parameters"]["properties"]["action"]["enum"] = action_names
    choose_action_model = model.bind_tools(choose_action_function, tool_choice="choose_action")
    messages = [SystemMessage(prompt)]

    tool_call = choose_action_model.invoke(messages).tool_calls
    selected_action_str = tool_call[0]['args']['action']
    selected_action = next((action for action in available_actions if str(action) == selected_action_str), None)

    state.selected_action = selected_action
    return state


def check_require_target(state: ChooseActionGraphState) -> bool:
    """Checks if the selected action requires a target player."""
    return state.selected_action.requires_target


def select_target_node(state: ChooseActionGraphState) -> ChooseActionGraphState:
    """Selects a target player for the action."""
    other_player_names = [str(player) for player in state.other_players]
    selected_action = state.selected_action
    cards = [str(card) for card in state.player.cards]
    coins = state.player.coins
    game_history = game_history_to_str(state.game_history)

    prompt = (
        f"You are professional coup game player called {state.player}. You selected action {selected_action} and now you need to determine target player.\n"
        f"You need to choose one player from {other_player_names}\n"
        f"You have {cards} on the hand and {coins} coins."

        "Here are previous game histories. You need to analyze this history and make the best decision\n"
        f"{game_history}"
    )

    model = ChatOpenAI(
        model="gpt-4o-2024-08-06",
    )

    choose_target_player_function[0]["function"]["parameters"]["properties"]["player"]["enum"] = other_player_names
    choose_target_model = model.bind_tools(choose_target_player_function, tool_choice="choose_player")
    messages = [SystemMessage(prompt)]

    tool_call = choose_target_model.invoke(messages).tool_calls
    selected_player_name = tool_call[0]['args']['player']
    selected_target = next((player for player in state.other_players if str(player) == selected_player_name), None)
    state.selected_target = selected_target

    return state


def determine_challenge(player: BasePlayer, challenged_player: BasePlayer, game_history: GameHistory) -> bool:
    cards = [str(card) for card in player.cards]
    coins = player.coins
    game_history = game_history_to_str(game_history)

    prompt = (
        f"You are professional coup game player called {player}. This is the {challenged_player}'s turn. You need to determine weather challenge {str(challenged_player)} or not.\n"
        f"You have {cards} on the hand and {coins} coins.\n"
        "Please be carefully while challenging other because if you lose the callenge, you need to discard one of your card. Please make safe decisions."
        "Here are previous game histories. You need to analyze this history and make the best decision\n"
        f"{game_history}"
    )

    model = ChatOpenAI(
        model="gpt-4o-2024-08-06",
    )

    determine_challenge_model = model.bind_tools(determine_challenge_function, tool_choice="determine_challenge")
    messages = [SystemMessage(prompt)]
    tool_call = determine_challenge_model.invoke(messages).tool_calls

    determine_challenge_str = tool_call[0]['args']['challenge']

    if determine_challenge_str == "true":
        return True
    else:
        return False


def determine_counter(player: BasePlayer, challenged_player: BasePlayer, game_history: GameHistory) -> bool:
    cards = [str(card) for card in player.cards]
    coins = player.coins
    game_history = game_history_to_str(game_history)

    prompt = (
        f"You are professional coup game player called {player}. This is the {challenged_player}'s turn. You need to determine weather counter {str(challenged_player)}'s action or not.\n"
        f"You have {cards} on the hand and {coins} coins."
        "Here are previous game histories. You need to analyze this history and make the best decision\n"
        f"{game_history}"
    )

    model = ChatOpenAI(
        model="gpt-4o-2024-08-06",
    )

    determine_counter_model = model.bind_tools(determine_counter_function, tool_choice="determine_counter")
    messages = [SystemMessage(prompt)]
    tool_call = determine_counter_model.invoke(messages).tool_calls

    determine_counter_str = tool_call[0]['args']['counter']

    if determine_counter_str == "true":
        return True
    else:
        return False


def remove_card(player: BasePlayer, game_history: GameHistory) -> Card:
    cards = [str(card) for card in player.cards]
    coins = player.coins
    game_history = game_history_to_str(game_history)

    prompt = (
        f"You are professional coup game player called {player}. Now, you need to discard one of your card."
        f"You have {cards} on the hand and {coins} coins. You must choose one card to be discarded"

        "Here are previous game histories. You need to analyze this history and make the best decision\n"
        f"{game_history}"
    )

    model = ChatOpenAI(
        model="gpt-4o-2024-08-06",
    )

    remove_card_function[0]["function"]["parameters"]["properties"]["card"]["enum"] = cards
    remove_card_model = model.bind_tools(remove_card_function, tool_choice="remove_card")
    messages = [SystemMessage(prompt)]
    tool_call = remove_card_model.invoke(messages).tool_calls

    discarded_card_name = tool_call[0]['args']['card']
    discarded_card = next((card for card in player.cards if str(card) == discarded_card_name), None)

    return discarded_card


def choose_exchange_cards(player: BasePlayer, exchange_cards: List[Card], game_history: GameHistory) -> Tuple[Card, Card]:
    cards = player.cards
    cards += exchange_cards
    card_names = [str(card) for card in cards]

    coins = player.coins
    game_history = game_history_to_str(game_history)

    prompt = (
        f"You are professional coup game player called {player}. Now, you need to select two cards to turn back to the deck."
        f"You have {card_names} and {coins} coins. You must choose two cards to turn back to the deck."

        "Here are previous game histories. You need to analyze this history and make the best decision\n"
        f"{game_history}"
    )

    model = ChatOpenAI(
        model="gpt-4o-2024-08-06",
    )

    choose_exchange_cards_function[0]["function"]["parameters"]["properties"]["first"]["enum"] = card_names
    choose_exchange_cards_function[0]["function"]["parameters"]["properties"]["second"]["enum"] = card_names
    choose_exchange_model = model.bind_tools(choose_exchange_cards_function, tool_choice="choose_exchange_card")
    messages = [SystemMessage(prompt)]
    tool_call = choose_exchange_model.invoke(messages).tool_calls

    first_card_name = tool_call[0]['args']['first']
    second_card_name = tool_call[0]['args']['second']
    first_card = None
    second_card = None
    for i, card in enumerate(cards):
        if str(card) == first_card_name:
            first_card = cards[i]
            del cards[i]
            break
    for i, card in enumerate(cards):
        if str(card) == second_card_name:
            second_card = cards[i]
            del cards[i]
            break

    return first_card, second_card


def validate_action_node(state: ChooseActionGraphState) -> ChooseActionGraphState:
    """Validates the selected action and target player."""
    return state


def validate_action(state: ChooseActionGraphState) -> bool:
    """Gets the target player object from the selected target name."""
    selected_action = state.selected_action
    selected_target_name = str(state.selected_target)
    other_players = state.other_players
    selected_target = next((player for player in other_players if str(player) == selected_target_name), None)

    is_valid = selected_action is not None and (
        selected_target is not None if selected_action.requires_target else True)

    return is_valid


def parse_action_node(state: ChooseActionGraphState) -> ChooseActionGraphState:
    return state
