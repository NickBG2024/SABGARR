import imaplib
import email
import re
import random
import streamlit as st
import pandas as pd
from database import get_fixturescount_by_matchtype, get_matchcount_by_matchtype, display_series_standings_with_points, display_matchtype_standings_with_points, get_matchcount_by_date_and_series, smccc, get_matchcount_by_series, get_fixturescount_by_series, show_matches_completed_by_series, show_matches_completed, display_sorting_series_table, display_series_table, display_series_table_completedonly, display_match_grid, list_remaining_fixtures, display_group_table, get_remaining_fixtures, get_match_results_for_grid, get_player_stats_with_fixtures, get_player_stats_by_matchtype, get_sorting_standings, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone, date

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_container_width=True)  # The image will resize to the width of the page

#Initialisation variables:
series_id = 5
matches_played = get_matchcount_by_series(series_id)
total_fixtures = get_fixturescount_by_series(series_id)
# Get today and yesterday's date
today = date.today()
yesterday = today - timedelta(days=1)
# Fetch match count for yesterday
match_count_yesterday = get_matchcount_by_date_and_series(yesterday.strftime("%Y-%m-%d"), series_id)

if total_fixtures !=0:
    percentage = (matches_played / total_fixtures) * 100
    metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
else:
    percentage = 0
    metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"

# Public-facing app for RR Leagues
st.title("SABGA Backgammon presents...") 
col1, col2 = st.columns(2)
col1.title("Round Robin Leagues 2025!")
col2.metric("Series 1 progress:",metric_value,match_count_yesterday)
col2.write("Deadline: 1 April 2025")
#standings = get_sorting_standings()
# Create tabs in a section
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["OVERVIEW", "A-League", "B-League", "C-League", "D-League", "E-League", "F-League"])

# Content for each tab
with tab1:    
    st.header("Overview:")
    pdf_url = "https://www.sabga.co.za/wp-content/uploads/2025/01/SABGA-Round-Robin-Leagues-2025-rules-etc-v4.pdf"
    st.markdown("**The 2025 Round Robin leagues kick-off with Series 1, taking place 11 Jan 2025 - April 2025, with 64 players competing in six leagues (A-F). The top four leagues have ten players each, with matches played to 11 points. The bottom two leagues, E and F, have twelve players each, and play to 9 points.**")
    st.markdown(f"All league information (rules, etc) can be found here: [SABGA Round Robin Leagues 2025 - rules etc v4.pdf]({pdf_url})", unsafe_allow_html=True)
    st.write("This tab will offer an overview of sorts, recent results, player averages, rules, links to other standings, resources?")
    
    #Call function to show series table with series_id
    #display_series_table_completedonly(series_id)
    #display_series_table(series_id)
    #display_sorting_series_table(series_id)
    display_series_standings_with_points(series_id)
    smccc(series_id)
    #show_matches_completed_by_series(series_id)
with tab2:
       # Example match type id        
        match_type_id = 19
        league_matches_played = get_matchcount_by_matchtype(match_type_id)
        league_fixtures = get_fixturescount_by_matchtype(match_type_id)
        
        if league_fixtures != 0:
            percentage = (league_matches_played / league_fixtures) * 100
            metric_value = f"{league_matches_played}/{league_fixtures} ({percentage:.1f}%)"
            games_left = league_fixtures - league_matches_played  # Calculate remaining games
        else:
            percentage = 0
            metric_value = f"{league_matches_played}/{league_fixtures} ({percentage:.1f}%)"
            games_left = 0
        
        # Calculate days left until April 1, 2025
        today = datetime.date.today()
        end_date = datetime.date(2025, 4, 1)
        days_left = (end_date - today).days
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("A-League progress:", metric_value)
        col2.metric("Games remaining:", games_left)
        col3.metric("Days left:", days_left)
        #Call function to show group table with match_type_id
        display_matchtype_standings_with_points(match_type_id)
        #display_group_metrics(match_type_id)
        #display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
with tab3:
       # Example match type id
        match_type_id = 20
        #Call function to show group table with match_type_id
        display_matchtype_standings_with_points(match_type_id)
        #display_group_metrics(match_type_id)
        #display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
with tab4:
        # Example match type id
        match_type_id = 21
        #Call function to show group table with match_type_id
        display_matchtype_standings_with_points(match_type_id)
        #display_group_metrics(match_type_id)
        #display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
with tab5:
        match_type_id = 23
        #Call function to show group table with match_type_id
        display_matchtype_standings_with_points(match_type_id)
        #display_group_metrics(match_type_id)
        #display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
with tab6:
        match_type_id = 24      
        #Call function to show group table with match_type_id
        display_matchtype_standings_with_points(match_type_id)
        #display_group_metrics(match_type_id)
        #display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
with tab7:
        match_type_id = 28     
        #Call function to show group table with match_type_id
        display_matchtype_standings_with_points(match_type_id)
        #display_group_metrics(match_type_id)
        #display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
