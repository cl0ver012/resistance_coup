import random
from typing import List, Optional, Tuple
from pydantic import BaseModel

from langgraph.graph import StateGraph

from src.models.action import Action
from src.models.card import Card
from src.models.players.base import BasePlayer
from src.utils.print import print_text, print_texts
from .graph_state import ChooseActionGraphState

from src.models.players.llm_player.nodes import (
    entry_node,
    check_coup,
    select_coup_target_node,
    select_action_node,
    check_require_target,
    select_target_node,
    validate_action_node,
    validate_action,
    parse_action_node,
    determine_challenge,
    determine_counter,
    remove_card,
    choose_exchange_cards
)


class LLMPlayer(BasePlayer):
    is_ai: bool = True
    cards: List[Card] = []
    _choose_action_graph: Optional[StateGraph] = None

    def __init__(self, name: str, game_handler: 'ResistanceCoupGameHandler', **data):
        super().__init__(name=name, is_ai=True, **data)
        self._game_handler = game_handler
        self._build_choose_action_graph()

    def _get_initial_state(self) -> ChooseActionGraphState:
        return ChooseActionGraphState(
            game_history=self._game_handler.get_game_history(),
            player=self,
            available_actions=[]
        )

    def _build_choose_action_graph(self):
        """Builds and compiles the StateGraph for choose_action."""
        workflow: StateGraph = StateGraph(state_schema=ChooseActionGraphState)
        workflow.add_node("entry_node", entry_node)
        workflow.add_node("select_coup_target_node", select_coup_target_node)
        workflow.add_node("select_action_node", select_action_node)
        workflow.add_node("select_target_node", select_target_node)
        workflow.add_node("validate_action_node", validate_action_node)
        workflow.add_node("parse_action_node", parse_action_node)

        workflow.add_conditional_edges("entry_node", check_coup, {
            True: "select_coup_target_node",
            False: "select_action_node"
        })

        workflow.add_conditional_edges("select_action_node", check_require_target, {
            True: "select_target_node",
            False: "validate_action_node"
        })

        workflow.add_edge("select_target_node", "validate_action_node")

        workflow.add_conditional_edges("validate_action_node", validate_action, {
            True: "parse_action_node",
            False: "select_action_node"
        })

        workflow.add_edge("select_action_node", "parse_action_node")
        workflow.set_entry_point("entry_node")
        workflow.set_finish_point("parse_action_node")

        self._choose_action_graph = workflow.compile()  # Compile the graph

    def choose_action(self, other_players: List['BasePlayer']) -> Tuple[Action, Optional['BasePlayer']]:
        """Choose the next action to perform using a LangChain StateGraph."""
        initial_state = self._get_initial_state()
        initial_state.other_players = other_players

        result = self._choose_action_graph.invoke(initial_state)
        if "selected_target" in result.keys():
            selected_target = result["selected_target"]
        else:
            selected_target = None
        return result["selected_action"], selected_target

    def determine_challenge(self, player: BasePlayer) -> bool:
        """Choose whether to challenge the current player"""
        game_history = self._game_handler.get_game_history()
        return determine_challenge(self, player, game_history)

    def determine_counter(self, player: BasePlayer) -> bool:
        """Choose whether to counter the current player's action"""
        game_history = self._game_handler.get_game_history()
        return determine_counter(self, player, game_history)

    def remove_card(self) -> None:
        """Choose a card and remove it from your hand"""
        game_history = self._game_handler.get_game_history()
        # Remove a random card
        if len(self.cards) == 1:
            discarded_card = self.cards.pop()
        else:
            discarded_card = remove_card(self, game_history)
            for i, card in enumerate(self.cards):
                if str(card) == str(discarded_card):
                    del self.cards[i]
                    break
        message = f"{self} discards their {discarded_card} card"
        print_texts(f"{self} discards their ", (f"{discarded_card}", discarded_card.style), " card")
        self._game_handler.log_message(message)

    def choose_exchange_cards(self, exchange_cards: list[Card]) -> Tuple[Card, Card]:
        """Perform the exchange action. Pick which 2 cards to send back to the deck"""
        game_history = self._game_handler.get_game_history()

        first_card, second_card = choose_exchange_cards(self, exchange_cards, game_history)
        message = f"{self} exchanges 2 cards"
        print_text(message)
        self._game_handler.log_message(message)

        return first_card, second_card
