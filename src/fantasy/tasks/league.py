import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import prefect
import requests
from tqdm import tqdm

from prefect import task, Task
from prefect.engine.results import LocalResult

from .teams import Team
from analysis import sigmoid


@dataclass
class League:
    league_id: int
    swid: str
    espn_s2: str
    stats_map: Dict[str, str]
    stats_index_map: Dict[str, str]
    stats_agg_map: Dict[str, str]

    def __post_init__(self):
        self.cookies = {"swid": self.swid, "espn_s2": self.espn_s2}
        self.stats_index_map = {int(k): self.stats_index_map[k] for k in self.stats_index_map}

    def url(self, season: int, views: Optional[List[str]] = None) -> str:
        base_url = 'http://fantasy.espn.com/apis/v3/games/fba/seasons/'
        full_url = (
            base_url + Path(str(season), 'segments/0/leagues', str(self.league_id)).as_posix()
        )
        if views:
            for view in views:
                full_url += f'?view={view}'
        return full_url

    def get_league_info(self, season: int) -> Dict:
        return requests.get(self.url(season=season), cookies=self.cookies).json()

    def _make_readable_stats(
        self,
        stats: Dict[str, Dict[str, float]],
        filter_redundant_keys=True,
        filter_unknown_keys=True,
    ) -> Dict[str, float]:
        try:
            readable_stats = {
                self.stats_map[k]: stats['averageStats'][k]
                for k in stats['averageStats']
                if len(self.stats_map[k]) > 0
                and not ('*' in self.stats_map[k] and filter_redundant_keys)
                and not ('?' in self.stats_map[k] and filter_unknown_keys)
            }
            all_stats = [
                k
                for k in self.stats_map
                if len(self.stats_map[k]) > 0
                and not ('*' in self.stats_map[k] and filter_redundant_keys)
                and not ('?' in self.stats_map[k] and filter_unknown_keys)
            ]
            # Only return if all stats are present
            return readable_stats if len(readable_stats) == len(all_stats) else None

        except KeyError:
            return {
                k: np.nan
                for k in self.stats_map.values()
                if len(k) > 0
                and not ('*' in k and filter_redundant_keys)
                and not ('?' in k and filter_unknown_keys)
            }

    def _parse_player_stats(self, stats: List[Dict[str, Dict[str, float]]]) -> pd.DataFrame:
        return pd.DataFrame(
            {
                self.stats_index_map[i]: self._make_readable_stats(stats_info)
                for i, stats_info in enumerate(stats)
                if i in self.stats_index_map and self._make_readable_stats(stats_info)
            }
        )

    def get_player_statistics(self, season: int) -> pd.DataFrame:
        player_request_info = requests.get(
            self.url(season=season, views=['kona_player_info']),
            cookies=self.cookies,
            headers={
                'x-fantasy-filter': json.dumps(
                    {
                        "players": {
                            "limit": 1500,
                            "sortDraftRanks": {
                                "sortPriority": 100,
                                "sortAsc": True,
                                "value": "STANDARD",
                            },
                        }
                    }
                )
            },
        ).json()
        return pd.concat(
            {
                player_info['player']['fullName']: self._parse_player_stats(
                    player_info['player']['stats']
                )
                for player_info in player_request_info['players']
            },
            axis=0,
        ).sort_index(level=0)

    def _get_per_roster_stats(self, player_info: pd.DataFrame, roster: List[str]) -> pd.DataFrame:
        roster_stats = (
            player_info.loc[roster]
            .groupby(level=1)
            .apply(lambda df: df.agg(func=self.stats_agg_map[df.name]))
        )
        if not isinstance(roster_stats, pd.DataFrame):
            roster_stats = roster_stats.unstack(level=1)
        return roster_stats

    def get_team_rosters(self, season: int, teams: List[Team]) -> Dict[str, List[str]]:
        roster_info = requests.get(
            self.url(season=season, views=['mRoster']),
            cookies=self.cookies,
        ).json()
        rosters = {
            teams[team['id'] - 1].abbrev: [
                entry['playerPoolEntry']['player']['fullName']
                for entry in team['roster']['entries']
            ]
            for team in roster_info['teams']
        }
        return rosters

    def get_roster_statistics(
        self, rosters: Dict[str, List[str]], player_info: pd.DataFrame
    ) -> pd.DataFrame:
        for team in rosters:
            for player in rosters[team]:
                assert player in player_info.index
        return pd.concat(
            {
                team_name: self._get_per_roster_stats(player_info, rosters[team_name])
                for team_name in rosters
            },
            axis=0,
        )

    def get_relevance_scores(
        self, player_stats: pd.DataFrame, roster_stats: pd.DataFrame
    ) -> pd.DataFrame:
        num_players = len(player_stats.index.get_level_values(level=1).unique())
        diffs = np.transpose(
            sigmoid(player_stats.swaplevel().values).reshape((num_players, -1, 4)), axes=(1, 2, 0)
        ) - sigmoid(roster_stats.values[..., None])
        return (
            pd.DataFrame(
                data=np.transpose(diffs, axes=(2, 0, 1)).reshape((27 * num_players, 4)),
                index=player_stats.swaplevel().index,
                columns=player_stats.swaplevel().columns,
            )
            .groupby(level=0)
            .apply(lambda df: df.sum(axis=0))
        )

    def get_team_relevance_scores(
        self,
        team_rosters: Dict[str, List[str]],
        player_stats: pd.DataFrame,
        roster_stats: pd.DataFrame,
        team_name: str,
    ) -> pd.DataFrame:
        team_stats = roster_stats.loc[:, team_name].unstack().T
        return prefect.context.league.get_relevance_scores(player_stats, team_stats).loc[
            team_rosters[team_name]
        ]

    def __repr__(self):
        return f'League {self.league_id}'

    @classmethod
    def load_league(cls, file_path: Union[str, Path]):
        with open(file_path, 'r') as f:
            league_config = json.load(f)
        return cls(**league_config)


@task(
    name='Get League Mean Statistics',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/league_mean_statistics.prefect"
    ),
    checkpoint=True,
)
def get_league_mean_statistics(team_stats: pd.DataFrame) -> pd.DataFrame:
    """Aggregates team aggregated statistics over the whole league.

    Args:
        team_stats (pd.DataFrame): multi-indexed dataframe with all teams statistics

    Returns:
        pd.DataFrame: 2D dataframes containing traditional mean statistics
            (e.g. PTS, AST) over
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            all indexed by according names.
    """
    return team_stats.groupby(level=1).apply(lambda df: df.mean(axis=0))


@task(
    name='Get League deviation Statistics',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/league_deviation_statistics.prefect"
    ),
    checkpoint=True,
)
def get_league_deviation_statistics(team_stats: pd.DataFrame) -> pd.DataFrame:
    """Aggregates team aggregated statistics over the whole league.

    Args:
        team_stats (pd.DataFrame): multi-indexed dataframe with all teams statistics

    Returns:
        pd.DataFrame: 2D dataframes containing traditional deviation statistics
            (e.g. PTS, AST) over
            * the last 7 days
            * the last 15 days
            * the last 30 days
            * current year statistics
            all indexed by according names, both mean and standard deviation.
    """
    return team_stats.groupby(level=1).apply(lambda df: df.std(axis=0))


@task(
    name='Compute All Roster Relevances',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/team_roster_relevances.prefect"
    ),
    checkpoint=True,
)
def compute_team_roster_relevances(
    team_rosters: Dict[str, List[str]],
    player_stats: pd.DataFrame,
    roster_stats: pd.DataFrame,
):
    return pd.concat(
        {
            team: prefect.context.league.get_team_relevance_scores(
                team_rosters, player_stats, roster_stats, team
            )
            for team in tqdm(team_rosters, desc='Computing Team Roster Relevances', leave=False)
        }
    )


@task(
    name='Compute All Trade Relevances',
    result=LocalResult(
        location="{output_directory}/{date:%m}-{date:%d}-{date:%Y}/trade_relevances.prefect"
    ),
    checkpoint=True,
)
def compute_trade_relevances(
    team_rosters: Dict[str, List[str]],
    player_stats: pd.DataFrame,
    roster_stats: pd.DataFrame,
) -> pd.DataFrame:
    team_names = list(team_rosters.keys())
    all_trade_scores = {}
    for i in tqdm(range(len(team_names)), desc='Computing Trade Relevances', leave=False):
        my_team_stats = roster_stats.loc[:, team_names[i]].unstack().T
        for j in range(i + 1, len(team_names)):
            their_team_stats = roster_stats.loc[:, team_names[j]].unstack().T
            all_trade_scores[(team_names[i], team_names[j])] = pd.concat(
                [
                    prefect.context.league.get_relevance_scores(player_stats, my_team_stats).loc[
                        team_rosters[team_names[j]]
                    ],
                    prefect.context.league.get_relevance_scores(player_stats, their_team_stats).loc[
                        team_rosters[team_names[i]]
                    ],
                ]
            )
    return pd.concat(all_trade_scores)
