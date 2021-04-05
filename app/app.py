import streamlit as st
import pandas as pd
import urllib
from typing import List

from fantasy.analysis import load_result
from fantasy.tasks.league import League


@st.cache
def get_file_content_as_string(path):
    url = 'https://raw.githubusercontent.com/dthiagarajan/fantasy_exploration/master/' + path
    response = urllib.request.urlopen(url)
    return response.read().decode("utf-8")


def display_player_statistics(normalized_player_statistics: pd.DataFrame, category: str):
    st.markdown(f'**Normalized Player {category} Statistics**')
    st.dataframe(data=normalized_player_statistics.loc[category], width=800)


def display_team_relevances(team_name: str, team_relevances: pd.DataFrame):
    st.markdown(f'**Team Roster Relevances**: {team_name}')
    st.markdown(
        'This is a list of player relevances, computed roughly by assessing how important a player '
        'is relative to each category.'
    )
    st.dataframe(data=team_relevances.loc[team_name], width=800)


def display_rostered_and_unrostered_relevances(
    team_name: str,
    rostered_players: List[str],
    normalized_player_statistics: pd.DataFrame,
    normalized_roster_statistics: pd.DataFrame,
):
    rostered_normalized_player_statistics = normalized_player_statistics[
        normalized_player_statistics.index.isin(rostered_players, level=1)
    ]
    unrostered_normalized_player_statistics = normalized_player_statistics[
        ~normalized_player_statistics.index.isin(rostered_players, level=1)
    ]
    st.markdown(f'**Rostered Player Relevances**: for {team_name}')
    st.markdown(f'Most relevant player on rosters for {team_name}.')
    rostered_relevance_scores = League.get_relevance_scores(
        rostered_normalized_player_statistics,
        normalized_roster_statistics.loc[:, team_name].unstack().T,
    )
    st.dataframe(data=rostered_relevance_scores, width=800)
    st.markdown(f'**Unrostered Player Relevances**: for {team_name}')
    st.markdown(f'Most relevant player not on rosters for {team_name}.')
    unrostered_relevance_scores = League.get_relevance_scores(
        unrostered_normalized_player_statistics,
        normalized_roster_statistics.loc[:, team_name].unstack().T,
    )
    st.dataframe(data=unrostered_relevance_scores, width=800)


def display_trade_relevances(team_1: str, team_2: str, trade_relevances: pd.DataFrame):
    if (team_1, team_2) in trade_relevances.index:
        ordering = (team_1, team_2)
    else:
        ordering = (team_2, team_1)
    if ordering not in trade_relevances.index:
        st.markdown('Please select a different team to trade with.')
    else:
        st.markdown(f'**Trade Relevances With**: {team_2}')
        st.markdown(
            'This is a list of the most relevant players between the two teams when '
            'considering how they would impact the other teams category scores.'
        )
        st.dataframe(data=trade_relevances.loc[ordering], width=800)


def main(current_date='03-28-2021'):
    st.sidebar.title(f'Champions League Statistics (Season: 2020-21, Date: {current_date})')
    team_rosters = load_result('visible_data', current_date, 'team_rosters')
    normalized_player_statistics = load_result(
        'visible_data', current_date, 'normalized_player_statistics'
    )
    normalized_roster_statistics = load_result(
        'visible_data', current_date, 'normalized_roster_statistics'
    )
    categories = normalized_player_statistics.index.get_level_values(0).unique()
    category_app_mode = st.sidebar.selectbox("Category (First Display)", list(categories))
    display_player_statistics(normalized_player_statistics, category_app_mode)
    team_relevances = load_result('visible_data', current_date, 'team_roster_relevances')
    trade_relevances = load_result('visible_data', current_date, 'trade_relevances')
    team_relevance_app_mode = st.sidebar.selectbox("Team", list(team_rosters.keys()))
    display_team_relevances(team_relevance_app_mode, team_relevances)

    rostered_players = sorted([player for roster in team_rosters.values() for player in roster])
    display_rostered_and_unrostered_relevances(
        team_relevance_app_mode,
        rostered_players,
        normalized_player_statistics,
        normalized_roster_statistics,
    )

    trade_relevance_app_mode = st.sidebar.selectbox("Trade With", list(team_rosters.keys()))
    display_trade_relevances(team_relevance_app_mode, trade_relevance_app_mode, trade_relevances)

    st.code(get_file_content_as_string("app/app.py"))


if __name__ == "__main__":
    main()
