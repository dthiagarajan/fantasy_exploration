import prefect
from prefect import Flow, Parameter
from prefect.engine.results import LocalResult

from tasks import (
    League,
    get_league_deviation_statistics,
    get_league_mean_statistics,
    get_normalized_player_statistics,
    get_normalized_roster_statistics,
    get_player_deviation_statistics,
    get_player_mean_statistics,
    get_teams,
    get_team_rosters,
    parse_player_statistics,
    parse_roster_statistics,
    compute_team_roster_relevances,
    compute_trade_relevances,
)

with Flow(name='Write All Statistics') as flow:
    season = Parameter(name='season', default=2021)
    teams = get_teams(season=season)
    player_info = parse_player_statistics(season=season)
    player_stats_mean, player_stats_deviation = (
        get_player_mean_statistics(player_info),
        get_player_deviation_statistics(player_info),
    )
    rosters = get_team_rosters(season=season, teams=teams)
    roster_stats = parse_roster_statistics(season=season, rosters=rosters, player_info=player_info)
    league_stats_mean, league_stats_deviation = (
        get_league_mean_statistics(roster_stats),
        get_league_deviation_statistics(roster_stats),
    )
    normalized_player_statistics = get_normalized_player_statistics(
        teams=teams,
        player_statistics=player_info,
        player_mean_statistics=player_stats_mean,
        player_deviation_statistics=player_stats_deviation,
    )
    normalized_roster_stats = get_normalized_roster_statistics(
        teams=teams,
        roster_statistics=roster_stats,
        league_mean_statistics=league_stats_mean,
        league_deviation_statistics=league_stats_deviation,
    )
    team_roster_relevances = compute_team_roster_relevances(
        team_rosters=rosters,
        player_stats=normalized_player_statistics,
        roster_stats=normalized_roster_stats,
    )

    trade_relevances = compute_trade_relevances(
        team_rosters=rosters,
        player_stats=normalized_player_statistics,
        roster_stats=normalized_roster_stats,
    )

if __name__ == '__main__':
    with prefect.context(league=League.load_league('./league_config.json')):
        final_state = flow.run()
