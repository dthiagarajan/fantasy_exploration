import numpy as np
import pandas as pd
from typing import List

import prefect
from prefect import task
from prefect.engine.results import LocalResult

from .teams import Team


@task(
    name='Parse Player Statistics',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/player_statistics.prefect"
    ),
    checkpoint=True,
)
def parse_player_statistics(season: int) -> pd.DataFrame:
    """Parses player statistics from a request sent to ESPN's fantasy API.

    Args:
        season (int): season to parse player statistics for

    Returns:
        pd.DataFrame: multi-indexed dataframe containing player statistics over
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            all indexed by according names
    """
    return prefect.context.league.get_player_statistics(season=season)


@task(
    name='Get Player Mean Statistics',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/player_mean_statistics.prefect"
    ),
    checkpoint=True,
)
def get_player_mean_statistics(player_stats: pd.DataFrame) -> pd.DataFrame:
    """Aggregates team aggregated statistics over the whole player.

    Args:
        player_stats (pd.DataFrame): multi-indexed dataframe with all players' statistics

    Returns:
        pd.DataFrame: 2D dataframes containing traditional mean statistics
            (e.g. PTS, AST) over
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            all indexed by according names.
    """
    return player_stats.groupby(level=1, dropna=False).apply(
        lambda df: df.replace([np.nan, 'Infinity'], 0).mean(axis=0)
    )


@task(
    name='Get Player Deviation Statistics',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/player_deviation_statistics.prefect"
    ),
    checkpoint=True,
)
def get_player_deviation_statistics(player_stats: pd.DataFrame) -> pd.DataFrame:
    """Aggregates team aggregated statistics over the whole player.

    Args:
        player_stats (pd.DataFrame): multi-indexed dataframe with all players' statistics

    Returns:
        pd.DataFrame: 2D dataframes containing traditional deviation statistics
            (e.g. PTS, AST) over
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            all indexed by according names, both mean and standard deviation.
    """
    return player_stats.groupby(level=1, dropna=False).apply(
        lambda df: df.replace([np.nan, 'Infinity'], 0).std(axis=0)
    )


@task(
    name='Get Normalized Player Statistics',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/normalized_player_statistics.prefect"
    ),
    checkpoint=True,
)
def get_normalized_player_statistics(
    teams: List[Team],
    player_statistics: pd.DataFrame,
    player_mean_statistics: pd.DataFrame,
    player_deviation_statistics: pd.DataFrame,
    epsilon=1e-6,
) -> pd.DataFrame:
    """Gets normalized player statistics using league mean/deviations and z-scores.

    Args:
        teams (List[Team]): list of teams in the league
        player_statistics (pd.DataFrame): statistics for all teams in the league
        player_mean_statistics (pd.DataFrame): mean statistics for the player
        player_deviation_statistics (pd.DataFrame): deviation for statistics in the player
        epsilon (float): float to avoid zero division. Defaults to 1e-6.

    Returns:
        pd.DataFrame: dataframe of z-scores for all players for all statistics for
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            transposed so that the time period and the statistics are on the row-wise index, and the
            team is on the col-wise index
    """
    num_players = len(player_statistics.index.get_level_values(level=0).unique())
    normalized_roster_statistics = (
        np.transpose(
            player_statistics.replace([np.nan, 'Infinity'], 0).values.reshape((num_players, -1, 4)),
            axes=(1, 2, 0),
        )
        - player_mean_statistics.values[..., None]
    ) / (player_deviation_statistics.values[..., None] + epsilon)
    return pd.DataFrame(
        data=np.transpose(np.nan_to_num(normalized_roster_statistics), axes=(2, 0, 1)).reshape(
            (27 * num_players, 4)
        ),
        index=player_statistics.index,
        columns=player_statistics.columns,
    ).swaplevel()
