import imaplib
import email
import re
import random
import streamlit as st
import pandas as pd
from database import display_matchtype_standings_with_points, get_matchcount_by_matchtype, get_fixturescount_by_matchtype, display_match_gridd, smccc, get_matchcount_by_date, get_matchcount_by_series, get_fixturescount_by_series, show_matches_completed_by_series, show_matches_completed, display_sorting_series_table, display_series_table, display_series_table_completedonly, display_match_grid, list_remaining_fixtures, display_group_table, get_remaining_fixtures, get_match_results_for_grid, get_player_stats_with_fixtures, get_player_stats_by_matchtype, get_sorting_standings, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone, date

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_container_width=True)  # The image will resize to the width of the page

#InitiationVariables
#series_id = 
match_type_id = 27

matches_played = get_matchcount_by_matchtype(match_type_id)
total_fixtures = get_fixturescount_by_matchtype(match_type_id)
percentage = (matches_played / total_fixtures) * 100
metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"

# Get today and yesterday's date
today = date.today()
yesterday = today - timedelta(days=1)

# Fetch match count for yesterday
match_count_yesterday = get_matchcount_by_date(yesterday.strftime("%Y-%m-%d"))

# Public-facing app for all users
st.title("SABGA Backgammon presents...") 
col1, col2 = st.columns(2)
col1.title("CTB Blitz!")
col2.metric("Progress...",metric_value, match_count_yesterday)
#standings = get_sorting_standings()

# Create tabs in a section
tab1, tab2 = st.tabs(["Player Standings", "Further Details"])

# Content for each tab
with tab1:    
    st.header("Player Standings - ordered by Points")
    st.write("Winner gets R2500, second place R500. Loser gets shamed.")
    # Example series id
    #series_id = 4
    #Call function to show series table with series_id
    #display_series_table_completedonly(series_id)
    #display_series_table(series_id)
    #display_sorting_series_table(series_id)
    #smccc(series_id)
    #show_matches_completed_by_series(series_id)
    display_matchtype_standings_with_points(match_type_id)
with tab2:
        #display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)    
