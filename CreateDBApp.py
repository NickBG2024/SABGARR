import streamlit as st
import pandas as pd
from database import get_crontest2, crontest2_table, empty_all_tables, reset_fixtures_completed, reset_match_results, print_table_structure, create_players_table, create_series_table, create_match_results_table, create_match_type_table, create_appsettings_table, create_fixtures_table
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

if st.button("Show MatchResults format:"):
    print_table_structure()
    st.success("table printed")

if st.button("reset matchresults:"):
    reset_match_results()
    reset_fixtures_completed()
    st.success("Match Results emptied, fixtures reset to Completed==0")

if st.button("Empty all Tables"):
    empty_all_tables()
    st.sucess("All tables emptied")

if st.button("Create crontest table"):
    crontest2_table()
    st.success("crontest table made")

if st.button("Show crontable 2 contents"):
    st.subheader("Crons in Database:")
    crons = get_crontest2()
    if not crons.empty:
        st.dataframe(crons)
else:
    st.write("No data found or unable to connect to database.")
    
