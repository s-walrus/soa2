from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import random

import transitions

import utils


class InvalidAction(Exception):
    pass


class Role(Enum):
    NOBODY = 0
    TOWNIE = 1
    MAFIA = 2


@dataclass
class PlayerState:
    name: str
    alive: bool = True
    role: Role = Role.NOBODY
    vote: str = ""


class GameController(object):
    STATES = ["not_started", "day", "night", "finished"]

    ROLES = [Role.TOWNIE, Role.TOWNIE, Role.TOWNIE, Role.MAFIA, Role.MAFIA]

    def __init__(self, print_message, score_callback):
        self.players: Dict[str, PlayerState] = dict()
        self.visitors: List[str] = []
        self.score: Dict[Role, int] = {role: 0 for role in set(self.ROLES)}

        self.announce = print_message
        self.send_score = score_callback
        self.send_score(0, 0)

        # Init the state machine
        self.machine = transitions.Machine(
            model=self, states=self.STATES, initial="not_started"
        )
        self.machine.add_transition(
            "start_game", "not_started", "day", after=["_reset_votes", "_give_roles"]
        )
        self.machine.add_transition("finish_day", "day", "night", after="_reset_votes")
        self.machine.add_transition(
            "finish_night", "night", "day", after="_reset_votes"
        )
        self.machine.add_transition(
            "finish_game",
            ["day", "night"],
            "not_started",
            after=["_reset_votes", "_reset_alive", "_restart_game"],
        )
        # Can add callbacks as string arguments: before, after, conditions

    def join(self, player_name: str) -> str:
        if not self.is_not_started():
            raise InvalidAction("The game is in progress, cannot join")

        # Validate name
        if self._get_token_by_name(player_name):
            raise InvalidAction(f"Name is already taken: {player_name}")
        if not utils.validate_player_name(player_name):
            raise InvalidAction(f"Bad player name: {player_name}")

        # Allocate a new token
        token = utils.make_player_token()
        if token in self.players:
            raise RuntimeError("Player token collision")

        # Create player info
        self.players[token] = PlayerState(player_name)
        self.visitors.append(player_name)

        # Announce status
        self.announce(f"A player joines the game: {player_name}")
        self.announce(
            f"Status: {len(self.players)}/{len(self.ROLES)} players have joined"
        )

        # Advance
        if len(self.players) == len(self.ROLES):
            self.start_game()

        return token

    def do_leave(self, token: str) -> str:
        player = self._get_player(token)

        self.announce(f"A player leaves the game: {player.name}")

        if self.is_not_started():
            # Remove player
            self.players.pop(token)

            # Announce status
            self.announce(
                f"Status: {len(self.players)}/{len(self.ROLES)} players are joined"
            )
        else:
            # Kill player
            self._kill(player, quit=True)

        return "OK"

    def do_chat(self, token: str, message: str) -> str:
        # Preconditions
        player = self._get_player(token)
        if self.is_night():
            raise InvalidAction("Chatting is not allowed at night")

        self.announce(f"[{player.name}] {message}")
        return "OK"

    def do_vote_sacrifice(self, token: str, name: str) -> str:
        # Preconditions
        player = self._get_player(token)
        if not self.is_day():
            raise InvalidAction("Voting is allowed at day only")
        if not player.alive:
            raise InvalidAction("You must be alive to vote")

        # Get target
        target_token = self._get_token_by_name(name)
        if not target_token:
            raise InvalidAction(f"No such player: {name}")
        target = self._get_player(target_token)
        if not target.alive:
            raise InvalidAction(f"Player character is dead: {name}")

        # Vote
        player.vote = target_token

        # Announce
        self.announce(f"{player.name} votes for {target.name}")

        # Advance
        self._check_sacrifice()

        return "OK"

    def do_vote_murder(self, token: str, name: str) -> str:
        # Preconditions
        player = self._get_player(token)
        if not self.is_night():
            raise InvalidAction("Voting for murder is allowed at day only")
        if player.role != Role.MAFIA:
            raise InvalidAction("Only mafia can vote for murder")
        if not player.alive:
            raise InvalidAction("You must be alive to vote")

        # Get target
        target_token = self._get_token_by_name(name)
        if not target_token:
            raise InvalidAction(f"No such player: {name}")
        target = self._get_player(target_token)
        if not target.alive:
            raise InvalidAction(f"Player character is dead: {name}")

        # Vote
        player.vote = target_token

        # Advance
        self._check_murder()

        return "OK"

    def do_get_status(self, player_name: str) -> str:
        player = self._get_player(player_name)

        if self.is_not_started():
            return f"Waiting for players: {len(self.players)}/{len(self.ROLES)}"
        elif self.is_day():
            return f"The city is awake. You are {player.role}."
        elif self.is_night():
            return f"The city is asleep. You are {player.role}."
        assert False, "Should never reach here"

    def _get_player(self, token: str) -> PlayerState:
        if token not in self.players:
            raise InvalidAction(f"No player with such token: {token}")
        return self.players[token]

    def _kill(self, player: PlayerState, quit: bool = False):
        if player.alive:
            self.announce(f"{player.name} dies!")
            player.alive = False
        if quit:
            self.players.popitem(player)
        self._check_winning()

    def _check_winning(self):
        assert not self.is_not_started()
        mafia_cnt = len(
            [
                item
                for item in self.players.values()
                if item.alive and item.role == Role.MAFIA
            ]
        )
        townie_cnt = len(
            [
                item
                for item in self.players.values()
                if item.alive and item.role == Role.TOWNIE
            ]
        )
        assert mafia_cnt != 0 or townie_cnt != 0
        if mafia_cnt == 0:
            self.announce("Mafia is dead, TOWNIES win the game!")
            self.score[Role.TOWNIE] += 1
            self.finish_game()
            self.send_score(self.score[Role.TOWNIE], self.score[Role.MAFIA])
        elif townie_cnt == 0:
            self.announce("Townies are dead, MAFIA wins the game!")
            self.score[Role.MAFIA] += 1
            self.finish_game()
            self.send_score(self.score[Role.TOWNIE], self.score[Role.MAFIA])

    def _check_sacrifice(self):
        assert self.is_day()
        alive_players = [p for p in self.players.values() if p.alive]
        votes = [p.vote for p in alive_players if p.vote]
        self.announce(
            f"Status: {len(votes)}/{len(alive_players)} players have voted for sacrifice"
        )
        if len(votes) == len(alive_players):
            self.announce("Voting is done")
            target = self._choose_voted_player(votes, silent=False)
            self.announce(f"Sacrificing {target.name}")
            self._kill(target)
            if self.is_day():
                self.finish_day()

    def _check_murder(self):
        assert self.is_night()
        alive_mafia = [
            p for p in self.players.values() if p.alive and p.role == Role.MAFIA
        ]
        votes = [p.vote for p in alive_mafia if p.vote]
        if len(votes) == len(alive_mafia):
            self.announce("Voting is done")
            target = self._choose_voted_player(votes, silent=True)
            self.announce(f"The mafia have murdered {target.name}")
            self._kill(target)
            if self.is_night():
                self.finish_night()

    def _choose_voted_player(self, votes: List[str], silent: bool) -> PlayerState:
        assert votes
        # Neglecting O-complexity because item count <= 5
        votes.sort()
        max_vote_cnt = votes.count(votes[0])
        match = [t for t in votes if votes.count(t) == max_vote_cnt]
        if len(match) != 1 and not silent:
            self.announce(
                f"Choosing the target at random among: {','.join(self._get_player(t).name for t in match)}"
            )
        target_token = random.choice(match)
        target = self._get_player(target_token)
        return target

    def _get_token_by_name(self, name: str) -> Optional[str]:
        match = [token for token, player in self.players.items() if player.name == name]
        if len(match) != 1:
            return None
        return match[0]

    def _reset_votes(self):
        for p in self.players.values():
            p.vote = ""

    def _reset_alive(self):
        for p in self.players.values():
            p.alive = True

    def _give_roles(self):
        roles = [r for r in self.ROLES]
        random.shuffle(roles)
        for i, p in enumerate(self.players.values()):
            p.role = roles[i]

    def _restart_game(self):
        self.announce("Starting again! Leave if you wish")
        self.start_game()
