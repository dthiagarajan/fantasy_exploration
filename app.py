import streamlit as st
import pandas as pd

from fantasy.analysis import load_result


def display_team_relevances(team_name: str, team_relevances: pd.DataFrame):
    st.markdown(f'**Team Roster Relevances**: {team_name}')
    st.dataframe(data=team_relevances.loc[team_name], width=800)


def display_trade_relevances(team_1: str, team_2: str, trade_relevances: pd.DataFrame):
    if (team_1, team_2) in trade_relevances.index:
        ordering = (team_1, team_2)
    else:
        ordering = (team_2, team_1)
    if ordering not in trade_relevances.index:
        st.markdown('Please select a different team to trade with.')
    else:
        st.markdown(f'**Trade Relevances With**: {team_2}')
        st.dataframe(data=trade_relevances.loc[ordering], width=800)


def main(current_date='03-28-2021'):
    st.sidebar.title('Champions League Statistics (2020-21)')
    team_rosters = load_result('data', current_date, 'team_rosters')
    team_relevances = load_result('data', current_date, 'team_roster_relevances')
    trade_relevances = load_result('data', current_date, 'trade_relevances')
    team_relevance_app_mode = st.sidebar.selectbox("Team", list(team_rosters.keys()))
    display_team_relevances(team_relevance_app_mode, team_relevances)
    trade_relevance_app_mode = st.sidebar.selectbox("Trade With", list(team_rosters.keys()))
    display_trade_relevances(team_relevance_app_mode, trade_relevance_app_mode, trade_relevances)


if __name__ == "__main__":
    main()
