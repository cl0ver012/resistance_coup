from typing import List, Optional
from pydantic import BaseModel


class PlayerState(BaseModel):
    name: str
    number_of_coins: int
    number_of_cards: int


class FinalState(BaseModel):
    player_states: List[PlayerState]
    number_of_cards_in_deck: int
    number_of_coins_in_treasury: int


class HistoryRecord(BaseModel):
    turn: int
    current_player: str
    messages: List[str]
    final_state: Optional[FinalState] = None  # Made Optional


class GameHistory(BaseModel):
    history: List[HistoryRecord]