import streamlit as st
from database import get_standings, get_match_results, check_tables

# Public-facing app for all users
st.title("SABGA Backgammon: Round Robin 2025")

# Display tables in the sidebar
tablecheck = check_tables()

st.sidebar.title("Public Section")
page = st.sidebar.selectbox("View", ["Leaderboard", "Fixtures", "Match History"])

# Show Leaderboard
if page == "Leaderboard":
    standings = get_standings()
    st.table(standings)

# Show Fixtures
elif page == "Fixtures":
    st.write("Fixtures will be listed here")

# Show Match History
elif page == "Match History":
    match_results = get_match_results()
    st.table(match_results)
