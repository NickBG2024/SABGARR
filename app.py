# app.py
import streamlit as st
from database import get_leaderboard, get_matches, insert_player, insert_match
from auth import login

# Admin authentication
is_admin = login()  # Function from auth.py
if is_admin:
    st.sidebar.title("Admin Options")
    manage_players = st.sidebar.button("Player Management")
    manage_matches = st.sidebar.button("Match Management")

    if manage_players:
        # Player management logic (e.g., adding, updating players)
        pass

    if manage_matches:
        # Match management logic (e.g., adding match results)
        pass
else:
    st.title("Backgammon Community App")
    st.write("Welcome to the app!")

    # Dropdown for leaderboard, round tables, match history
    page = st.selectbox("View", ["Leaderboard", "Round Tables", "Match History"])

    if page == "Leaderboard":
        st.write(get_leaderboard())  # Display leaderboard
    elif page == "Round Tables":
        st.write("Round Tables view")
    elif page == "Match History":
        st.write(get_matches())  # Display match history
