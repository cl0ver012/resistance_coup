from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from src.models.game_history import GameHistory
from src.models.action import Action
from src.models.players.base import BasePlayer


class ChooseActionGraphState(BaseModel):
    game_history: GameHistory
    player: BasePlayer
    available_actions: List[Action]
    selected_action: Optional[Action] = None
    other_players: Optional[List[BasePlayer]] = None
    selected_target: Optional[BasePlayer] = None
