import imaplib
import email
import re
import random
import streamlit as st
import pandas as pd
from database import get_matchcount_by_series, get_fixturescount_by_series, show_matches_completed_by_series, show_matches_completed, display_series_table, display_series_table_completedonly, display_match_grid, list_remaining_fixtures, display_group_table, get_remaining_fixtures, get_match_results_for_grid, get_player_stats_with_fixtures, get_player_stats_by_matchtype, get_sorting_standings, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon presents...") 
col1, col2, col3 = st.columns(3)
col1.metric("Players", "54", "3",help="fred")
col2.metric("Games Played",get_matchcount_by_series(4), "2")
col3.metric("The Great Sorting Completion", "6%", "0.5%")
st.header("The Great Sorting 2025!")
standings = get_sorting_standings()
# Create tabs in a section
tab1, tab2, tab3 = st.tabs(["Player Standings", "Sorting Groups (1 - 7)", "Sorting Groups (8 - 14)"])

# Content for each tab
with tab1:
    st.header("Player Standings - ordered by PR")
    st.write("These standings will be used to help sort players in their appropriate league groups, for the start of the SABGA Round Robin 2025.")
    # Example series id
    series_id = 4
    #Call function to show series table with series_id
    #display_series_table_completedonly(series_id)
    display_series_table(series_id)
    df = pd.DataFrame(
        {
            "name": ["Roadmap", "Extras", "Issues"],
            "url": ["https://roadmap.streamlit.app", "https://extras.streamlit.app", "https://issues.streamlit.app"],
            "stars": [random.randint(0, 1000) for _ in range(3)],
            "views_history": [[random.randint(0, 5000) for _ in range(30)] for _ in range(3)],
        }
    )
    st.dataframe(
        df,
        column_config={
            "name": "App name",
            "stars": st.column_config.NumberColumn(
                "Github Stars",
                help="Number of stars on GitHub",
                format="%d ⭐",
            ),
            "url": st.column_config.LinkColumn("App URL"),
            "views_history": st.column_config.LineChartColumn(
                "Views (past 30 days)", y_min=0, y_max=5000
            ),
        },
        hide_index=True,
    )
    show_matches_completed_by_series(series_id)
with tab2:
    # Create tabs for additional stats
    tab4, tab5, tab6, tab7, tab8, tab9, tab10  = st.tabs(["Group 1", "Group 2", "Group 3", "Group 4", "Group 5","Group 6","Group 7"])
with tab3:
    tab11, tab12, tab13, tab14, tab15, tab16, tab17 = st.tabs(["Group 8","Group 9","Group 10","Group 11","Group 12","Group 13","Group 14"])
    
    with tab4:
        # Example match type id
        match_type_id = 4
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab5:
        match_type_id = 5      
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab6:
        match_type_id = 6      
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)    
    with tab7:
        match_type_id = 7      
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab8:
        match_type_id = 8      
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab9:       
        match_type_id = 9      
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab10:
        match_type_id = 10      
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab11:       
        match_type_id = 11      
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab12:
        match_type_id = 12      
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab13:       
        match_type_id = 13     
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab14:       
        match_type_id = 15
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab15:       
        match_type_id = 16     
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab16:       
        match_type_id = 17     
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
    with tab17:       
        match_type_id = 18    
        #Call function to show group table with match_type_id
        #display_group_metrics(match_type_id)
        display_group_table(match_type_id)
        display_match_grid(match_type_id)        
        list_remaining_fixtures(match_type_id)
        show_matches_completed(match_type_id)
