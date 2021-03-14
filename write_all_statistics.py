import prefect
from prefect import Flow, Parameter
from tasks import (
    League,
    get_league_deviation_statistics,
    get_league_mean_statistics,
    get_normalized_roster_statistics,
    get_teams,
    parse_player_statistics,
    parse_roster_statistics,
)

with Flow(name='Write All Statistics') as flow:
    season = Parameter(name='season', default=2021)
    teams = get_teams(season=season)
    player_info = parse_player_statistics(season=season)
    roster_stats = parse_roster_statistics(season=season, teams=teams, player_info=player_info)
    league_stats_mean, league_stats_deviation = (
        get_league_mean_statistics(roster_stats),
        get_league_deviation_statistics(roster_stats),
    )
    normalized_roster_stats = get_normalized_roster_statistics(
        teams=teams,
        roster_statistics=roster_stats,
        league_mean_statistics=league_stats_mean,
        league_deviation_statistics=league_stats_deviation,
    )

if __name__ == '__main__':
    with prefect.context(league=League.load_league('./league_config.json')):
        final_state = flow.run()
