import json
from typing import List

import pandas as pd
import requests

import prefect
from prefect import task
from prefect.engine.results import LocalResult

from .teams import Team


@task(
    name='Parse Roster Statistics',
    target="{date:%m}-{date:%d}-{date:%Y}/roster_statistics.prefect",
    result=LocalResult(dir='./data'),
    checkpoint=True,
)
def parse_roster_statistics(
    season: int, teams: List[Team], player_info: pd.DataFrame
) -> pd.DataFrame:
    """Parses roster statistics from a request sent to ESPN's fantasy API.

    Args:
        season (int): the season to get roster statistics for
        teams (List[Team]): the teams in the league to consider
        player_info (pd.DataFrame): statistics for all players

    Returns:
        pd.DataFrame: multi-indexed dataframe containing roster statistics over
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            all indexed by according names
    """
    return prefect.context.league.get_roster_statistics(
        season=season, teams=teams, player_info=player_info
    )
