import streamlit as st
from database import create_players_table, create_match_results_table, create_match_type_table

st.title("Create Backgammon Database")

if st.button("Create Players Table"):
    create_players_table()
    st.success("Players table created.")

if st.button("Create Match Results Table"):
    create_match_results_table()
    st.success("Match Results table created.")

if st.button("Create Match Type Table"):
    create_match_type_table()
    st.success("Match Type table created.")
