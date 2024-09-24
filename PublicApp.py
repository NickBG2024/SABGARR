import streamlit as st
from database import create_connection, get_leaderboard, get_matches

# Connect to the database
conn = create_connection()

# Streamlit title
st.title("SABGA Backgammon: Round Robin 2025")

# Retrieve and display leaderboard
st.subheader("Leaderboard")
leaderboard = get_leaderboard(conn)
st.table(leaderboard)

# Retrieve and display match history
st.subheader("Match History")
matches = get_matches(conn)  # Pass conn here
st.table(matches)
