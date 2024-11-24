import imaplib
import email
import re
import streamlit as st
import pandas as pd
from database import display_match_grid, list_remaining_fixtures, display_group_table, get_remaining_fixtures, get_match_results_for_grid, get_player_stats_with_fixtures, get_player_stats_by_matchtype, get_sorting_standings, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon presents...") 
st.header("The Great Sorting 2025!")
standings = get_sorting_standings()
# Create tabs in a section
tab1, tab2 = st.tabs(["Player Standings", "Sorting Groups"])

# Content for each tab
with tab1:
    st.header("Player Standings - ordered by PR")
    st.write("These standings will be used to help sort players in their appropriate league groups, for the start of the SABGA Round Robin 2025.")
    st.table(standings)

with tab2:
    # Create tabs for additional stats
    tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 = st.tabs(["Group 1", "Group 2", "Group 3", "Group 4", "Group 5","Group 6","Group 7","Group 8","Group 9","Group 10","Group 11",])
    with tab3:
        # Example match type id
        match_type_id = 1
        
        #Call function to show group table with match_type_id
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        st.write("Maybe a metric of completion ?")
    with tab4:
        st.header("Sorting Group 2")
        st.write("Sorting Group 2:")
        st.write("To add: table, outstanding fixtures, match-grid")
        st.write("Maybe a metric of completion?")
    with tab5:
        st.header("Sorting Group 3")
        st.write("Select the season from the dropdown to view season's stats")
    with tab6:
        st.header("Sorting Group 4")
        st.write("Select the year from the dropdown to view year's stats")
