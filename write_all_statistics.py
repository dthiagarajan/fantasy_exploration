import prefect
from prefect import Flow, Parameter
from tasks import (
    League,
    get_league_statistics,
    get_teams,
    parse_player_statistics,
    parse_roster_statistics,
)

with Flow(name='Write All Statistics') as flow:
    season = Parameter(name='season', default=2021)
    teams = get_teams(season=season)
    player_info = parse_player_statistics(season=season)
    roster_stats = parse_roster_statistics(season=season, teams=teams, player_info=player_info)
    league_stats = get_league_statistics(roster_stats)

if __name__ == '__main__':
    # TODO: load league_config.json and put it in the Prefect context
    with prefect.context(league=League.load_league('./league_config.json')):
        final_state = flow.run()
