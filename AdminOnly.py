import streamlit as st
from database import add_player, add_match_type, add_match_result, get_all_players, get_all_match_types, get_all_matches

st.title("SABGA Admin Only")

# Sidebar checkboxes
show_add_player_form = st.sidebar.checkbox("Add Player")
show_add_match_type_form = st.sidebar.checkbox("Add Match Type")
show_add_match_result_form = st.sidebar.checkbox("Add Match Result")

# New checkboxes for showing tables
show_players = st.sidebar.checkbox("Show all Players")
show_match_types = st.sidebar.checkbox("Show all Match Types")
show_matches = st.sidebar.checkbox("Show all Matches")

# Headings and forms for adding data
if show_add_player_form:
    st.subheader("Add Player")
    with st.form(key='add_player_form'):
        name = st.text_input("Name")
        nickname = st.text_input("Heroes Nickname")
        email = st.text_input("Email Address")
        submitted = st.form_submit_button("Add Player")
        if submitted:
            add_player(name, nickname, email)
            st.success("Player added successfully!")
            st.experimental_rerun()

if show_add_match_type_form:
    st.subheader("Add Match Type")
    with st.form(key='add_match_type_form'):
        match_type_title = st.text_input("Match Type Title")
        submitted = st.form_submit_button("Add Match Type")
        if submitted:
            add_match_type(match_type_title)
            st.success("Match type added successfully!")
            st.experimental_rerun()

if show_add_match_result_form:
    st.subheader("Add Match Result")
    with st.form(key='add_match_result_form'):
        date = st.date_input("Date")
        time_completed = st.time_input("Time Completed")
        player1_id = st.number_input("Player 1 ID", min_value=1)
        player2_id = st.number_input("Player 2 ID", min_value=1)
        match_type_id = st.number_input("Match Type ID", min_value=1)
        player1_points = st.number_input("Player 1 Points", min_value=0)
        player2_points = st.number_input("Player 2 Points", min_value=0)
        player1_pr = st.number_input("Player 1 PR", min_value=0.0)
        player2_pr = st.number_input("Player 2 PR", min_value=0.0)
        player1_luck = st.number_input("Player 1 Luck", min_value=0.0)
        player2_luck = st.number_input("Player 2 Luck", min_value=0.0)
        submitted = st.form_submit_button("Add Match Result")
        if submitted:
            add_match_result(date, time_completed, player1_id, player2_id, match_type_id, player1_points, player2_points, player1_pr, player2_pr, player1_luck, player2_luck)
            st.success("Match result added successfully!")
            st.experimental_rerun()

# Display tables based on checkboxes
if show_players:
    st.subheader("All Players")
    players = get_all_players()
    if players:
        st.write("PlayerID | Name | Nickname | Email | Games Played | Total Wins | Total Losses | Win Percentage | Average PR")
        st.table(players)
    else:
        st.error("No players found.")

if show_match_types:
    st.subheader("All Match Types")
    match_types = get_all_match_types()
    if match_types:
        st.write("MatchTypeID | MatchTypeTitle")
        st.table(match_types)
    else:
        st.error("No match types found.")

if show_matches:
    st.subheader("All Matches")
    matches = get_all_matches()
    if matches:
        st.write("MatchID | Date | Time Completed | Match Type ID | Player 1 ID | Player 2 ID | Player 1 Points | Player 2 Points | Player 1 PR | Player 2 PR | Player 1 Luck | Player 2 Luck")
        st.table(matches)
    else:
        st.error("No matches found.")
