import random
from enum import Enum
from typing import List, Optional, Tuple, Union
import io
import sys

import names

from src.models.action import Action, ActionType, CounterAction, get_counter_action
from src.models.card import Card, build_deck
from src.models.players.ai import AIPlayer
from src.models.players.base import BasePlayer
from src.models.players.human import HumanPlayer
from src.models.game_history import GameHistory, HistoryRecord, FinalState, PlayerState
from src.utils.game_state import generate_players_table, generate_state_panel
from src.utils.print import (
    build_action_report_string,
    build_counter_report_string,
    print_confirm,
    print_panel,
    print_table,
    print_text,
    print_texts,
)


class ChallengeResult(Enum):
    no_challenge = 0
    challenge_failed = 1
    challenge_succeeded = 2


class ResistanceCoupGameHandler:
    _players: List[BasePlayer] = []
    _current_player_index = 0
    _deck: List[Card] = []
    _number_of_players: int = 0
    _treasury: int = 0
    _game_history: GameHistory = GameHistory(history=[])
    _turn_count: int = 0
    _current_turn_messages: List[str] = []

    def __init__(self, player_name: str, number_of_players: int, ai_play: bool = False):
        self._number_of_players = number_of_players
        if ai_play:
            unique_names = set()
            for i in range(number_of_players):
                gender = random.choice(["male", "female"])

                ai_name = names.get_first_name(gender=gender)
                while ai_name in unique_names:
                    ai_name = names.get_first_name(gender=gender)

                unique_names.add(ai_name)

                self._players.append(AIPlayer(name=ai_name, game_handler=self))
        else:
            # Set up players
            self._players.append(HumanPlayer(name=player_name, game_handler=self))

            unique_names = set()
            for i in range(number_of_players - 1):
                gender = random.choice(["male", "female"])

                ai_name = names.get_first_name(gender=gender)
                while ai_name in unique_names:
                    ai_name = names.get_first_name(gender=gender)

                unique_names.add(ai_name)

                self._players.append(AIPlayer(name=ai_name, game_handler=self))

    @property
    def current_player(self) -> BasePlayer:
        return self._players[self._current_player_index]

    @property
    def remaining_player(self) -> BasePlayer:
        """Return the only remaining player"""
        return [player for player in self._players if player.is_active][0]

    def _capture_print_output(self, func, *args, **kwargs):
        """Captures the printed output of a function and returns it as a string."""
        captured_output = io.StringIO()
        sys.stdout = captured_output
        func(*args, **kwargs)
        sys.stdout = sys.__stdout__  # Restore the original stdout
        return captured_output.getvalue()

    def print_game_state(self) -> None:
        # Print the table and panel directly without capturing
        print_table(generate_players_table(self._players, self._current_player_index))
        print_panel(generate_state_panel(self._deck, self._treasury, self.current_player))

    def _players_without_player(self, excluded_player: BasePlayer):
        players_copy = self._players.copy()
        return [
            player
            for player in players_copy
            if player.is_active and player.name != excluded_player.name
        ]

    def _shuffle_deck(self) -> None:
        random.shuffle(self._deck)

    def setup_game(self) -> None:
        self._deck = build_deck()
        self._shuffle_deck()

        self._treasury = 50 - 2 * len(self._players)

        for player in self._players:
            player.reset_player()

            # Deal 2 cards to each player
            player.cards.append(self._deck.pop())
            player.cards.append(self._deck.pop())

            # Gives each player 2 coins
            player.coins = 2

            # Includes the player in the game
            player.is_active = True

        # Random starting player
        self._current_player_index = random.randint(0, self._number_of_players - 1)

        # Reset game history, turn count, and current turn messages
        self._game_history = GameHistory(history=[])
        self._turn_count = 0
        self._current_turn_messages = []

    def _swap_card(self, player: BasePlayer, card: Card) -> None:
        self._deck.append(card)
        self._shuffle_deck()
        player.cards.append(self._deck.pop())

    def _take_coin_from_treasury(self, player: BasePlayer, number_of_coins: int):
        if number_of_coins <= self._treasury:
            self._treasury -= number_of_coins
            player.coins += number_of_coins
        else:
            coins = self._treasury
            self._treasury = 0
            player.coins += coins

    def _give_coin_to_treasury(self, player: BasePlayer, number_of_coins: int):
        self._treasury += number_of_coins
        player.coins -= number_of_coins

    def _next_player(self):
        self._current_player_index = (self._current_player_index + 1) % len(self._players)
        while not self.current_player.is_active:
            self._current_player_index = (self._current_player_index + 1) % len(self._players)

    def _remove_defeated_player(self) -> Optional[BasePlayer]:
        for ind, player in enumerate(self._players):
            if not player.cards and player.is_active:
                player.is_active = False
                self._give_coin_to_treasury(player, player.coins)

                return player
        return None

    def _determine_win_state(self) -> bool:
        return sum(player.is_active for player in self._players) == 1

    def _action_phase(
            self, players_without_current: list[BasePlayer]
    ) -> Tuple[Action, Optional[BasePlayer]]:
        # Player chooses action
        target_action, target_player = self.current_player.choose_action(players_without_current)

        action_message = build_action_report_string(
            player=self.current_player, action=target_action, target_player=target_player
        )
        captured_output = self._capture_print_output(
            print_text, action_message, with_markup=True
        )
        self._current_turn_messages.append(captured_output)

        return target_action, target_player

    def _challenge_against_player_failed(
            self, player_being_challenged: BasePlayer, card: Card, challenger: BasePlayer
    ):
        # Player being challenged reveals the card
        message = f"{player_being_challenged} reveals their {card} card!"
        captured_output = self._capture_print_output(
            print_texts,
            f"{player_being_challenged} reveals their ",
            (f"{card}", card.style),
            " card!",
        )
        self._current_turn_messages.append(captured_output)
        captured_output = self._capture_print_output(
            print_text, f"{challenger} loses the challenge"
        )
        self._current_turn_messages.append(captured_output)

        # Challenge player loses influence (chooses a card to remove)
        challenger.remove_card()

        # Player puts card into the deck and gets a new card
        captured_output = self._capture_print_output(
            print_text, f"{player_being_challenged} gets a new card"
        )
        self._current_turn_messages.append(captured_output)
        self._swap_card(player_being_challenged, card)

    def _challenge_against_player_succeeded(self, player_being_challenged: BasePlayer):
        message = f"{player_being_challenged} bluffed! They do not have the required card!"
        captured_output = self._capture_print_output(print_text, message)
        self._current_turn_messages.append(captured_output)

        # Player being challenged loses influence (chooses a card to remove)
        player_being_challenged.remove_card()

    def _challenge_phase(
            self,
            other_players: list[BasePlayer],
            player_being_challenged: BasePlayer,
            action_being_challenged: Union[Action, CounterAction],
    ) -> ChallengeResult:
        # Every player can choose to challenge
        for challenger in other_players:
            should_challenge = challenger.determine_challenge(player_being_challenged)
            if should_challenge:
                challenge_message = f"{challenger} is challenging {player_being_challenged}!"
                if challenger.is_ai:
                    captured_output = self._capture_print_output(print_text, challenge_message)
                    self._current_turn_messages.append(captured_output)

                # Player being challenged has the card
                if card := player_being_challenged.find_card(
                        action_being_challenged.associated_card_type
                ):
                    self._challenge_against_player_failed(
                        player_being_challenged=player_being_challenged,
                        card=card,
                        challenger=challenger,
                    )
                    return ChallengeResult.challenge_failed

                # Player being challenged bluffed
                else:
                    self._challenge_against_player_succeeded(player_being_challenged)
                    return ChallengeResult.challenge_succeeded

        # No challenge happened
        return ChallengeResult.no_challenge

    def _counter_phase(
            self, players_without_current: list[BasePlayer], target_action: Action
    ) -> Tuple[Optional[BasePlayer], Optional[CounterAction]]:
        # Every player can choose to counter
        for countering_player in players_without_current:
            should_counter = countering_player.determine_counter(self.current_player)
            if should_counter:
                target_counter = get_counter_action(target_action.action_type)
                counter_message = build_counter_report_string(
                    target_player=self.current_player,
                    counter=target_counter,
                    countering_player=countering_player,
                )
                captured_output = self._capture_print_output(print_text, counter_message)
                self._current_turn_messages.append(captured_output)

                return countering_player, target_counter

        return None, None

    def _execute_action(
            self, action: Action, target_player: BasePlayer, countered: bool = False
    ) -> None:
        match action.action_type:
            case ActionType.income:
                # Player gets 1 coin
                self._take_coin_from_treasury(self.current_player, 1)
                message = f"{self.current_player}'s coins are increased by 1"
                captured_output = self._capture_print_output(print_text, message)
                self._current_turn_messages.append(captured_output)
            case ActionType.foreign_aid:
                if not countered:
                    # Player gets 2 coin
                    self._take_coin_from_treasury(self.current_player, 2)
                    message = f"{self.current_player}'s coins are increased by 2"
                    captured_output = self._capture_print_output(print_text, message)
                    self._current_turn_messages.append(captured_output)
            case ActionType.coup:
                # Player pays 7 coin
                self._give_coin_to_treasury(self.current_player, 7)
                message = f"{self.current_player} pays 7 coins and performs the coup against {target_player}"
                captured_output = self._capture_print_output(print_text, message)
                self._current_turn_messages.append(captured_output)

                if target_player.cards:
                    # Target player loses influence
                    target_player.remove_card()
            case ActionType.tax:
                # Player gets 3 coins
                self._take_coin_from_treasury(self.current_player, 3)
                message = f"{self.current_player}'s coins are increased by 3"
                captured_output = self._capture_print_output(print_text, message)
                self._current_turn_messages.append(captured_output)
            case ActionType.assassinate:
                # Player pays 3 coin
                self._give_coin_to_treasury(self.current_player, 3)
                if not countered and target_player.cards:
                    message = f"{self.current_player} assassinates {target_player}"
                    captured_output = self._capture_print_output(print_text, message)
                    self._current_turn_messages.append(captured_output)
                    target_player.remove_card()
            case ActionType.steal:
                if not countered:
                    # Take 2 (or all) coins from a player
                    steal_amount = min(target_player.coins, 2)
                    target_player.coins -= steal_amount
                    self.current_player.coins += steal_amount
                    message = f"{self.current_player} steals {steal_amount} coins from {target_player}"
                    captured_output = self._capture_print_output(print_text, message)
                    self._current_turn_messages.append(captured_output)
            case ActionType.exchange:
                # Get 2 random cards from deck
                cards = [self._deck.pop(), self._deck.pop()]
                first_card, second_card = self.current_player.choose_exchange_cards(cards)
                self._deck.append(first_card)
                self._deck.append(second_card)

    def _record_final_state(self):
        player_states = [
            PlayerState(
                name=player.name,
                number_of_coins=player.coins,
                number_of_cards=len(player.cards)
            )
            for player in self._players
        ]
        final_state = FinalState(
            player_states=player_states,
            number_of_cards_in_deck=len(self._deck),
            number_of_coins_in_treasury=self._treasury
        )
        self._game_history.history[-1].final_state = final_state

    def handle_turn(self) -> bool:
        self._turn_count += 1
        self._current_turn_messages = []  # Reset messages for the new turn

        # Create new record for the current turn
        self._game_history.history.append(
            HistoryRecord(
                turn=self._turn_count,
                current_player=self.current_player.name,
                messages=[],
                final_state=None
            )
        )

        players_without_current = self._players_without_player(self.current_player)

        # Choose an action to perform
        target_action, target_player = self._action_phase(players_without_current)

        # Opportunity to challenge action
        challenge_result = ChallengeResult.no_challenge
        if target_action.can_be_challenged:
            challenge_result = self._challenge_phase(
                other_players=players_without_current,
                player_being_challenged=self.current_player,
                action_being_challenged=target_action,
            )

        if challenge_result == ChallengeResult.challenge_succeeded:
            # Challenge succeeded and the action does not take place
            pass
        elif challenge_result == ChallengeResult.challenge_failed:
            # Challenge failed and the action is still resolved
            self._execute_action(target_action, target_player)
        elif challenge_result == ChallengeResult.no_challenge:
            # Action can't be countered
            if not target_action.can_be_countered:
                self._execute_action(target_action, target_player)

            # Opportunity to counter
            else:
                countering_player, counter = self._counter_phase(
                    players_without_current, target_action
                )

                # Opportunity to challenge counter
                counter_challenge_result = ChallengeResult.no_challenge
                if countering_player and counter:
                    players_without_countering_player = self._players_without_player(
                        countering_player
                    )
                    counter_challenge_result = self._challenge_phase(
                        other_players=players_without_countering_player,
                        player_being_challenged=countering_player,
                        action_being_challenged=counter,
                    )

                # Successfully countered and counter not challenged
                if counter and counter_challenge_result in [
                    ChallengeResult.no_challenge,
                    ChallengeResult.challenge_failed,
                ]:
                    self._execute_action(target_action, target_player, countered=True)
                # No counter occurred
                else:
                    self._execute_action(target_action, target_player)

        # Is any player out of the game?
        while player := self._remove_defeated_player():
            if player.is_ai:
                message = f"{player} was defeated! :skull: :skull: :skull:"
                captured_output = self._capture_print_output(print_text, message, with_markup=True)
                self._current_turn_messages.append(captured_output)
            else:
                # Our human was defeated
                message = "You were defeated! :skull: :skull: :skull:"
                captured_output = self._capture_print_output(print_text, message, with_markup=True)
                self._current_turn_messages.append(captured_output)
                end_game = print_confirm("Do you want to end the game early?")
                if end_game:
                    return True

        # Have we reached a winner?
        if self._determine_win_state():
            message = f":raising_hands: Congratulations {self.remaining_player}! You are the final survivor!"
            captured_output = self._capture_print_output(print_text, message, with_markup=True)
            self._current_turn_messages.append(captured_output)
            self._record_final_state()
            return True

        self._record_final_state()
        self._next_player()

        # Record the messages for the completed turn
        self._game_history.history[-1].messages = self._current_turn_messages

        # No winner yet
        return False

    def print_game_history(self):
        """Prints the game history in a readable format."""
        for record in self._game_history.history:
            print(f"Turn {record.turn}:")
            print(f"  Current Player: {record.current_player}")
            for message in record.messages:
                print(f"    {message}")
            if record.final_state:
                print("  Final State:")
                for player_state in record.final_state.player_states:
                    print(
                        f"    {player_state.name}: Coins - {player_state.number_of_coins}, Cards - {player_state.number_of_cards}")
                print(f"    Deck: {record.final_state.number_of_cards_in_deck} cards")
                print(f"    Treasury: {record.final_state.number_of_coins_in_treasury} coins")

    def print_last_turn_history(self):
        """Prints the history of the last completed turn."""
        if self._game_history.history:
            last_record = self._game_history.history[-1]
            print(f"Turn {last_record.turn}:")
            print(f"  Current Player: {last_record.current_player}")
            for message in last_record.messages:
                print(f"    {message}")
            if last_record.final_state:
                print("  Final State:")
                for player_state in last_record.final_state.player_states:
                    print(
                        f"    {player_state.name}: Coins - {player_state.number_of_coins}, Cards - {player_state.number_of_cards}")
                print(f"    Deck: {last_record.final_state.number_of_cards_in_deck} cards")
                print(f"    Treasury: {last_record.final_state.number_of_coins_in_treasury} coins")
        else:
            print("No game history available yet.")

    def log_message(self, message: str):
        """Logs a message to the current turn's history."""
        self._current_turn_messages.append(message)