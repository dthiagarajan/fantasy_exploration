from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import prefect
from prefect import task
from prefect.engine.results import LocalResult

from .teams import Team


@task(
    name='Get Team Rosters',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/team_rosters.prefect"
    ),
    checkpoint=True,
)
def get_team_rosters(season: int, teams: List[Team]) -> Dict[str, List[str]]:
    """Gets rosters for each team using ESPN's fantasy API.

    Args:
        season (int): the season to get roster statistics for
        teams (List[Team]): the teams in the league to consider

    Returns:
        Dict[str, List[str]]: mapping from roster name to roster (list of player names)
    """
    return prefect.context.league.get_team_rosters(season=season, teams=teams)


@task(
    name='Parse Roster Statistics',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/roster_statistics.prefect"
    ),
    checkpoint=True,
)
def parse_roster_statistics(
    season: int, rosters: Dict[str, List[str]], player_info: pd.DataFrame
) -> pd.DataFrame:
    """Parses roster statistics from a request sent to ESPN's fantasy API.

    Args:
        season (int): the season to get roster statistics for
        rosters (Dict[str, List[str]]): the rosters in the league to consider
        player_info (pd.DataFrame): statistics for all players

    Returns:
        pd.DataFrame: multi-indexed dataframe containing roster statistics over
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            all indexed by according names
    """
    return prefect.context.league.get_roster_statistics(rosters=rosters, player_info=player_info)


@task(
    name='Get Normalized Roster Statistics',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/normalized_roster_statistics.prefect"
    ),
    checkpoint=True,
)
def get_normalized_roster_statistics(
    teams: List[Team],
    roster_statistics: pd.DataFrame,
    league_mean_statistics: pd.DataFrame,
    league_deviation_statistics: pd.DataFrame,
    epsilon=1e-6,
) -> pd.DataFrame:
    """Gets normalized roster statistics using league mean/deviations and z-scores.

    Args:
        teams (List[Team]): list of teams in the league
        roster_statistics (pd.DataFrame): statistics for all teams in the league
        league_mean_statistics (pd.DataFrame): mean statistics for the league
        league_deviation_statistics (pd.DataFrame): deviation for statistics in the league
        epsilon (float): float to avoid zero division. Defaults to 1e-6.

    Returns:
        pd.DataFrame: dataframe of z-scores for all rosters for all statistics for
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            transposed so that the time period and the statistics are on the row-wise index, and the
            team is on the col-wise index
    """
    num_teams = len(teams)
    normalized_roster_statistics = (
        np.transpose(roster_statistics.values.reshape((num_teams, -1, 4)), axes=(1, 2, 0))
        - league_mean_statistics.values[..., None]
    ) / (league_deviation_statistics.values[..., None] + epsilon)
    return (
        pd.DataFrame(
            data=np.transpose(np.nan_to_num(normalized_roster_statistics), axes=(2, 0, 1)).reshape(
                (27 * 12, 4)
            ),
            index=roster_statistics.index,
            columns=roster_statistics.columns,
        )
        .unstack()
        .T
    )
