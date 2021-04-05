from dataclasses import dataclass
from typing import List

import prefect
from prefect import task
from prefect.engine.results import LocalResult


@dataclass(frozen=True)
class Team:
    abbrev: str
    id: int
    location: str
    nickname: str
    owners: str

    def __repr__(self):
        return f'{self.location} {self.nickname} [{self.abbrev}]({self.id})'

    def __hash__(self):
        return hash(repr(self))


@task(
    name='Retrieve Fantasy Teams',
    result=LocalResult(location="{output_directory}/{date:%Y}/teams.prefect"),
    checkpoint=True,
)
def get_teams(season: int) -> List[Team]:
    league_info = prefect.context.league.get_league_info(season=season)
    return [Team(**team_info) for team_info in league_info['teams']]
