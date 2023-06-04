from typing import List, Dict
import strawberry


@strawberry.type
class Score:
    townies: int
    mafia: int


@strawberry.type
class Game:
    id: str
    score: Score
    comments: List[str]


scoreboard: Dict[str, Game] = dict()


@strawberry.type
class Query:
    @strawberry.field
    def game(self, id: str) -> Game:
        return scoreboard[id]

    @strawberry.field
    def games(self) -> List[Game]:
        return scoreboard.values()


@strawberry.type
class Mutation:
    @strawberry.mutation
    def addComment(self, gameID: str, message: str) -> Game:
        scoreboard[gameID].comments.append(message)
        return scoreboard[gameID]

    @strawberry.mutation
    def updateGame(self, gameID: str, towniesScore: int, mafiaScore: int) -> Game:
        if gameID not in scoreboard:
            scoreboard[gameID] = Game(
                id=gameID,
                score=Score(townies=towniesScore, mafia=mafiaScore),
                comments=[],
            )
        else:
            scoreboard[gameID].score = Score(townies=towniesScore, mafia=mafiaScore)
        return scoreboard[gameID]


schema = strawberry.Schema(query=Query, mutation=Mutation)
