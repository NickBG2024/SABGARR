import streamlit as st
from database import get_standings, get_match_results, check_tables

# Public-facing app for all users
st.title("SABGA Backgammon: Round Robin 2025")

st.sidebar.title("Public Section")
page = st.sidebar.selectbox("View", ["Standings", "Fixtures", "Match History"])

if page == "Standings":
    standings = get_standings()
    st.table(standings)
elif page == "Fixtures":
    st.write("Current fixtures:")
elif page == "Match Results":
    matchresults = get_match_results()
    st.table(matchresults)
