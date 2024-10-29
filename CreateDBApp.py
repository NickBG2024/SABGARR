import streamlit as st
from database import create_players_table, create_series_table, create_match_results_table, create_match_type_table, create_appsettings_table, create_fixtures_table, alter_matchresults

st.title("Create Backgammon Database")

if st.button("Create Players Table"):
    create_players_table()
    st.success("Players table created.")

if st.button("Create Series Table"):
    create_series_table()
    st.success("Series table created.")

if st.button("Create Match Results Table"):
    create_match_results_table()
    st.success("Match Results table created.")

if st.button("Create Match Type Table"):
    create_match_type_table()
    st.success("Match Type table created.")

if st.button("Create appSettings Table"):
    create_appsettings_table()
    st.success("App settings table created.")

if st.button("Create fixtures Table"):
    create_fixtures_table()
    st.success("Fixtures table created.")

if st.button("Alter matchresults"):
    alter_matchresults()
    st.success("Altered matchresults.")
