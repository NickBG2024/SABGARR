import streamlit as st
from database import get_leaderboard, get_matches

# Public-facing app for all users
st.title("SABGA Backgammon: Round Robin 2025")

st.sidebar.title("Public Section")
page = st.sidebar.selectbox("View", ["Leaderboard", "Fixtures", "Match History"])

if page == "Leaderboard":
    leaderboard = get_leaderboard()
    st.table(leaderboard)
elif page == "Fixtures":
    st.write("Fixtures will be listed here")
elif page == "Match History":
    matches = get_matches()
    st.table(matches)
