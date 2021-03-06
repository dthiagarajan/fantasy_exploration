import pandas as pd

import prefect
from prefect import task
from prefect.engine.results import LocalResult


@task(
    name='Parse Player Statistics',
    target="{date:%m}-{date:%d}-{date:%Y}/player_statistics.prefect",
    result=LocalResult(dir='./data'),
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
