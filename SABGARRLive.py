import imaplib
import email
import re
import random
import streamlit as st
import pandas as pd
import shutil
import os
from database import show_player_summary_tab, show_player_of_the_year, show_player_summary_tab1, fetch_cached_series_standings, show_cached_remaining_fixtures_by_series, get_series_completed_matches_detailed, display_match_grid, list_cached_remaining_fixtures, show_cached_matches_completed, display_cached_matchtype_standings, get_averagePR_by_matchtype, list_remaining_fixtures_by_series, display_matchtype_standings_full_details_styled, get_fixturescount_by_matchtype, get_matchcount_by_matchtype, display_series_standings_with_points_and_details, display_series_standings_with_points, display_matchtype_standings_with_points_and_details, display_matchtype_standings_with_points, get_matchcount_by_date_and_series, smccc, get_matchcount_by_series, get_fixturescount_by_series, show_matches_completed_by_series, show_matches_completed, display_sorting_series_table, display_series_table, display_series_table_completedonly, display_match_grid, list_remaining_fixtures, display_group_table, get_remaining_fixtures, get_match_results_for_grid, get_player_stats_with_fixtures, get_player_stats_by_matchtype, get_sorting_standings, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone, date

# Copy Render's secret file to the location Streamlit expects
if os.path.exists("secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    shutil.copy("secrets.toml", ".streamlit/secrets.toml")
    
# Header image — use use_column_width or a pixel width
st.image(
    "https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg",
    use_column_width=True
)

# Add an icon image to sidebar
# Add an icon image to sidebar
st.sidebar.markdown(
    """
    <div style='text-align: center; margin: 10px 5px 10px 5px;'>
        <img src='https://www.sabga.co.za/wp-content/uploads/2020/06/SABGA_logo_tight.jpg' width='200'/>
    </div>
    """, unsafe_allow_html=True
)

days_left = 0

def league_tab(matchtype_id,league_title,days_left):
    #st.write(f"Loading {league_title} data...") 
    with st.spinner(f"Loading {league_title} data..."):
        league_matches_played = get_matchcount_by_matchtype(matchtype_id)
        league_fixtures = get_fixturescount_by_matchtype(matchtype_id)
        ave_pr = get_averagePR_by_matchtype(matchtype_id)
                
        if league_fixtures != 0:
            percentage = (league_matches_played / league_fixtures) * 100
            #metric_value = f"{league_matches_played}/{league_fixtures} ({percentage:.1f}%)"
            metric_value = f"{league_matches_played}/{league_fixtures}"
            games_left = league_fixtures - league_matches_played  # Calculate remaining games
        else:
            percentage = 0
            metric_value = f"{league_matches_played}/{league_fixtures} ({percentage:.1f}%)"
            games_left = 0
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"{league_title} Progress", f"{metric_value}", f"{percentage:.1f}%")
        col2.metric("Games remaining:", games_left)
        col3.metric("Days left:", days_left)
        col4.metric("Average PR:", ave_pr)

        display_cached_matchtype_standings(matchtype_id)
        display_match_grid(matchtype_id)       
        list_cached_remaining_fixtures(matchtype_id)
        show_cached_matches_completed(matchtype_id)

def show_series_stats_page(series_choice):    

    #2026 - SERIES 1 LEAGUE DATA DISPLAY       
    if series_choice == "2026 - Series 1":
        st.write("Loading data for the 2026 - S1 series...")
    
        #Initialisation variables:
        current_series_id = 10
        matches_played = get_matchcount_by_series(current_series_id)
        total_fixtures = get_fixturescount_by_series(current_series_id)
        # Get today and yesterday's date
        today = date.today()
        yesterday = today - timedelta(days=1)
        # Fetch match count for yesterday
        match_count_yesterday = get_matchcount_by_date_and_series(yesterday.strftime("%Y-%m-%d"), current_series_id)
        
        # Calculate days left until end of series 1 (2 Apr, 2026)
        #today = date.today()
        end_date = date(2026, 4, 2)
        days_left = (end_date - today).days
        
        if total_fixtures !=0:
            percentage = (matches_played / total_fixtures) * 100
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        else:
            percentage = 0
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        
        # Public-facing app for RR Leagues
        st.title("SABGA Backgammon presents...") 
        col1, col2 = st.columns(2)
        col1.title("Round Robin Leagues!")
        col2.metric("Series 1 progress:",metric_value,match_count_yesterday)
        col2.write("Deadline: 2 April 2026")
        #standings = get_sorting_standings()
    
        # Define tab names
        tab_names = ["OVERVIEW", "A-League", "B-League", "C-League", "D-League", "E-League", "F-League","Guppy Group Yellow","Guppy Group Blue","Guppy Group Red"]
    
        # Define corresponding matchtype IDs (adjust these based on your database)
        matchtype_ids = {
            "A-League": 56,
            "B-League": 57,
            "C-League": 58,
            "D-League": 59,
            "E-League": 60,
            "F-League": 61,
            "Guppy Group Yellow": 62,
            "Guppy Group Blue": 63,
            "Guppy Group Red": 64
        }
        
        # Create tabs
        tabs = st.tabs(tab_names)
        
        # Overview tab
        with tabs[0]:
            st.header("Overview")
            pdf_url = "https://www.sabga.co.za/wp-content/uploads/2025/12/SABGA-Online-Backgammon-Round-Robin-Leagues-2026-rules-etc-v1.pdf"
            st.markdown("**The 2026 Round Robin leagues kick off with Series 1, taking place 11 January 2026 - 2 April 2026, with 85 players competing in nine league groups (A-F and 3 Guppy Groups). The top five leagues play matches to 11 points. The next two leagues, E and F, play to 9 points. There are also three 'Guppy' groups for new players.**")
            st.markdown(f"All league information (rules, etc) can be found here: [SABGA Round Robin Leagues 2026 - rules etc v1.1.pdf]({pdf_url})", unsafe_allow_html=True)
            st.write("This tab offers an overview: a table showing all players, recent results and remaining fixtures.")
            
            fetch_cached_series_standings(current_series_id)
            #get_series_completed_matches_detailed(current_series_id)
            smccc(current_series_id)
            show_cached_remaining_fixtures_by_series(current_series_id)
    
    
        # League tabs - dynamically call league_tab() with appropriate matchtype_id
        for i, league_name in enumerate(tab_names[1:], start=1):  # Skip "OVERVIEW"
            with tabs[i]:
                league_tab(matchtype_ids[league_name], league_name, days_left)    

    
    #2025 - SERIES 4 LEAGUE DATA DISPLAY       
    if series_choice == "2025 - Series 4":
        st.write("Loading data for the 2025 - S4 series...")
    
        #Initialisation variables:
        current_series_id = 8
        matches_played = get_matchcount_by_series(current_series_id)
        total_fixtures = get_fixturescount_by_series(current_series_id)
        # Get today and yesterday's date
        today = date.today()
        yesterday = today - timedelta(days=1)
        # Fetch match count for yesterday
        match_count_yesterday = get_matchcount_by_date_and_series(yesterday.strftime("%Y-%m-%d"), current_series_id)
        
        # Calculate days left until end of series 4 (31 Dec, 2025)
        #today = date.today()
        end_date = date(2025, 12, 31)
        days_left = (end_date - today).days
        
        if total_fixtures !=0:
            percentage = (matches_played / total_fixtures) * 100
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        else:
            percentage = 0
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        
        # Public-facing app for RR Leagues
        st.title("SABGA Backgammon presents...") 
        col1, col2 = st.columns(2)
        col1.title("Round Robin Leagues!")
        col2.metric("Series 4 progress:",metric_value,match_count_yesterday)
        col2.write("Deadline: 31 December 2025")
        #standings = get_sorting_standings()
    
        # Define tab names
        tab_names = ["OVERVIEW", "A-League", "B-League", "C-League", "D-League", "E-League", "F-League","Guppy Group 1","Guppy Group 2"]
    
        # Define corresponding matchtype IDs (adjust these based on your database)
        matchtype_ids = {
            "A-League": 48,
            "B-League": 49,
            "C-League": 50,
            "D-League": 51,
            "E-League": 52,
            "F-League": 53,
            "Guppy Group 1": 54,
            "Guppy Group 2": 55
        }
        
        # Create tabs
        tabs = st.tabs(tab_names)
        
        # Overview tab
        with tabs[0]:
            st.header("Overview")
            pdf_url = "https://www.sabga.co.za/wp-content/uploads/2025/07/SABGA-Round-Robin-Leagues-2025-rules-etc-v5dot2.pdf"
            st.markdown("**The 2025 Round Robin leagues continues with Series 4, taking place 2 October 2025 - 31 December 2025, with 74 players competing in eight leagues (A-G). The top five leagues play matches to 11 points. The next two leagues, E and F, play to 9 points. There are also two 'Guppy' groups for new players.**")
            st.markdown(f"All league information (rules, etc) can be found here: [SABGA Round Robin Leagues 2025 - rules etc v5.2.pdf]({pdf_url})", unsafe_allow_html=True)
            st.write("This tab offers an overview: a table showing all players, recent results and remaining fixtures.")
            
            fetch_cached_series_standings(current_series_id)
            #get_series_completed_matches_detailed(current_series_id)
            smccc(current_series_id)
            show_cached_remaining_fixtures_by_series(current_series_id)
    
    
        # League tabs - dynamically call league_tab() with appropriate matchtype_id
        for i, league_name in enumerate(tab_names[1:], start=1):  # Skip "OVERVIEW"
            with tabs[i]:
                league_tab(matchtype_ids[league_name], league_name, days_left)    
    
    #2025 - SERIES 3 LEAGUE DATA DISPLAY       
    if series_choice == "2025 - Series 3":
        st.write("Loading data for the 2025 - S3 series...")
    
        #Initialisation variables:
        current_series_id = 7
        matches_played = get_matchcount_by_series(current_series_id)
        total_fixtures = get_fixturescount_by_series(current_series_id)
        # Get today and yesterday's date
        today = date.today()
        yesterday = today - timedelta(days=1)
        # Fetch match count for yesterday
        match_count_yesterday = get_matchcount_by_date_and_series(yesterday.strftime("%Y-%m-%d"), current_series_id)
        
        # Calculate days left until end of series 2 (30 Sept, 2025)
        #today = date.today()
        end_date = date(2025, 9, 30)
        days_left = (end_date - today).days
        
        if total_fixtures !=0:
            percentage = (matches_played / total_fixtures) * 100
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        else:
            percentage = 0
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        
        # Public-facing app for RR Leagues
        st.title("SABGA Backgammon presents...") 
        col1, col2 = st.columns(2)
        col1.title("Round Robin Leagues!")
        col2.metric("Series 3 progress:",metric_value,match_count_yesterday)
        col2.write("Deadline: 30 September 2025")
        #standings = get_sorting_standings()
    
        # Define tab names
        tab_names = ["OVERVIEW", "A-League", "B-League", "C-League", "D-League", "E-League", "F-League","Guppy Group 1","Guppy Group 2"]
    
        # Define corresponding matchtype IDs (adjust these based on your database)
        matchtype_ids = {
            "A-League": 39,
            "B-League": 40,
            "C-League": 41,
            "D-League": 42,
            "E-League": 44,
            "F-League": 45,
            "Guppy Group 1": 46,
            "Guppy Group 2": 47
        }
        
        # Create tabs
        tabs = st.tabs(tab_names)
        
        # Overview tab
        with tabs[0]:
            st.header("Overview")
            pdf_url = "https://www.sabga.co.za/wp-content/uploads/2025/07/SABGA-Round-Robin-Leagues-2025-rules-etc-v5dot2.pdf"
            st.markdown("**The 2025 Round Robin leagues continues with Series 3, taking place 2 July 2025 - 30 September 2025, with 74 players competing in eight leagues (A-G). The top five leagues play matches to 11 points. The next two leagues, E and F, play to 9 points. There are also two 'Guppy' groups for new players.**")
            st.markdown(f"All league information (rules, etc) can be found here: [SABGA Round Robin Leagues 2025 - rules etc v5.2.pdf]({pdf_url})", unsafe_allow_html=True)
            st.write("This tab offers an overview: a table showing all players, recent results and remaining fixtures.")
            
            fetch_cached_series_standings(current_series_id)
            #get_series_completed_matches_detailed(current_series_id)
            smccc(current_series_id)
            show_cached_remaining_fixtures_by_series(current_series_id)
    
    
        # League tabs - dynamically call league_tab() with appropriate matchtype_id
        for i, league_name in enumerate(tab_names[1:], start=1):  # Skip "OVERVIEW"
            with tabs[i]:
                league_tab(matchtype_ids[league_name], league_name,days_left)    
    
    
    #2025 - SERIES 2 LEAGUE DATA DISPLAY        
    if series_choice == "2025 - Series 2":
        st.write("Loading data for the 2025 - S2 series...")
    
        #Initialisation variables:
        current_series_id = 6
        matches_played = get_matchcount_by_series(current_series_id)
        total_fixtures = get_fixturescount_by_series(current_series_id)
        # Get today and yesterday's date
        # Fetch match count for yesterday
        match_count_yesterday = 0
        
        # Calculate days left until end of series 2 (30 June, 2025)
        #today = date.today()
        end_date = date(2025, 6, 30)
        days_left = 0
        
        if total_fixtures !=0:
            percentage = (matches_played / total_fixtures) * 100
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        else:
            percentage = 0
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        
        # Public-facing app for RR Leagues
        st.title("SABGA Backgammon presents...") 
        col1, col2 = st.columns(2)
        col1.title("Round Robin Leagues!")
        col2.metric("Series 2 progress:",metric_value,match_count_yesterday)
        col2.write("Deadline: 30 June 2025")
        #standings = get_sorting_standings()
    
        # Define tab names
        tab_names = ["OVERVIEW", "A-League", "B-League", "C-League", "D-League", "E-League", "F-League","Guppy Group 1","Guppy Group 2"]
    
        # Define corresponding matchtype IDs (adjust these based on your database)
        matchtype_ids = {
            "A-League": 30,
            "B-League": 31,
            "C-League": 32,
            "D-League": 33,
            "E-League": 34,
            "F-League": 35,
            "Guppy Group 1": 36,
            "Guppy Group 2": 37
        }
        
        # Create tabs
        tabs = st.tabs(tab_names)
        
        # Overview tab
        with tabs[0]:
            st.header("Overview")
            pdf_url = "https://www.sabga.co.za/wp-content/uploads/2025/07/SABGA-Round-Robin-Leagues-2025-rules-etc-v5dot2.pdf"
            st.markdown("**The 2025 Round Robin leagues Series 2, took place 2 Apr 2025 - 30 June 2025, with 74 players competing in eight leagues (A-G). The top four leagues had ten players each, with matches played to 11 points. The next two leagues, E and F, had twelve players each, and played to 9 points. There were also two 'Guppy' groups for new players.**")
            st.markdown(f"All league information (rules, etc) can be found here: [SABGA Round Robin Leagues 2025 - rules etc v5.2.pdf]({pdf_url})", unsafe_allow_html=True)
            st.write("This tab offers an overview: a table showing all players, recent results and remaining fixtures.")
            
            fetch_cached_series_standings(current_series_id)
            show_cached_remaining_fixtures_by_series(current_series_id)
            get_series_completed_matches_detailed(current_series_id)
    
        # League tabs - dynamically call league_tab() with appropriate matchtype_id
        for i, league_name in enumerate(tab_names[1:], start=1):  # Skip "OVERVIEW"
            with tabs[i]:
                league_tab(matchtype_ids[league_name], league_name, days_left)    
    
    #2025 - SERIES 1 LEAGUE DATA DISPLAY        
    elif series_choice == "2025 - Series 1":
        st.write("Loading data for the 2025 - S1 series...")
     
        #Initialisation variables:
        current_series_id = 5
        matches_played = get_matchcount_by_series(current_series_id)
        total_fixtures = get_fixturescount_by_series(current_series_id)
        # Get today and yesterday's date
        today = date.today()
        yesterday = today - timedelta(days=1)
        # Fetch match count for yesterday
        match_count_yesterday = get_matchcount_by_date_and_series(yesterday.strftime("%Y-%m-%d"), current_series_id)
        
        # Calculate days left until end of series 1 (April 1, 2025)
        #today = date.today()
        end_date = date(2025, 4, 1)
        days_left = 0
        
        if total_fixtures !=0:
            percentage = (matches_played / total_fixtures) * 100
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        else:
            percentage = 0
            metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        
        # Public-facing app for RR Leagues
        st.title("SABGA Backgammon presents...") 
        col1, col2 = st.columns(2)
        col1.title("Round Robin Leagues!")
        col2.metric("Series 1 progress:",metric_value,match_count_yesterday)
        col2.write("Deadline: 1 April 2025")
        #standings = get_sorting_standings()
    
        # Define tab names
        tab_names = ["OVERVIEW", "A-League", "B-League", "C-League", "D-League", "E-League", "F-League"]
    
        # Define corresponding matchtype IDs (adjust these based on your database)
        matchtype_ids = {
            "A-League": 19,
            "B-League": 20,
            "C-League": 21,
            "D-League": 23,
            "E-League": 24,
            "F-League": 28
        }
        
        # Create tabs
        tabs = st.tabs(tab_names)
        
        # Overview tab
        with tabs[0]:
            st.header("Overview")
            pdf_url = "https://www.sabga.co.za/wp-content/uploads/2025/01/SABGA-Round-Robin-Leagues-2025-rules-etc-v4dot1.pdf"
            st.markdown("**The 2025 Round Robin leagues kicked-off with Series 1, which ran 11 Jan 2025 - April 2025, with 64 players competing in six leagues (A-F). The top four leagues have ten players each, with matches played to 11 points. The bottom two leagues, E and F, have twelve players each, and play to 9 points.**")
            st.markdown(f"All league information (rules, etc) can be found here: [SABGA Round Robin Leagues 2025 - rules etc v4.1.pdf]({pdf_url})", unsafe_allow_html=True)
            #st.write("This tab will offer an overview of sorts, recent results, player averages, rules, links to other standings, resources?")
            
            fetch_cached_series_standings(current_series_id)
            show_cached_remaining_fixtures_by_series(current_series_id)
            get_series_completed_matches_detailed(current_series_id)
    
        # League tabs - dynamically call league_tab() with appropriate matchtype_id
        for i, league_name in enumerate(tab_names[1:], start=1):  # Skip "OVERVIEW"
            with tabs[i]:
                league_tab(matchtype_ids[league_name], league_name, days_left)    
    
    #SORTING LEAGUE DATA DISPLAY
    elif series_choice == "2024 - Sorting League":
        st.write("Loading data for Sorting League series...")
    
        seriesid = 4
        matches_played = get_matchcount_by_series(seriesid)
        total_fixtures = get_fixturescount_by_series(seriesid)
        percentage = (matches_played / total_fixtures) * 100
        metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"
        
        # Public-facing app for all users
        st.title("SABGA Backgammon presents...") 
        col1, col2 = st.columns(2)
        col1.title("The Great Sorting!")
        col2.metric("Progress...",metric_value, 0)
        standings = get_sorting_standings()
    
        st.header("Player Standings - ordered by PR")
        st.write("Standings to sort players into Round Robin Leagues (A-F) for 2025 RR League: Series 1.")
        # Example series id
        series_id = 4
        #Call function to show series table with series_id
        #display_series_table_completedonly(series_id)
        #display_series_table(series_id)
        display_sorting_series_table(series_id)
        smccc(series_id)
        #list_remaining_fixtures_by_series(series_id)
        #show_matches_completed_by_series(series_id)

st.sidebar.title("ROUND ROBIN DATA:")

# Add "View Player Statistics" as a navigation option
view_option = st.sidebar.radio(
    "Select what to view:",
    ["League Standings 📊", "Player Stats 👤","Season (year) Stats 📅"],
    #["Series Statistics", "Player Statistics","Series Statistics","Season (year) Statistics "], 
    index=0  # default to Series Stats
)

if view_option == "League Standings 📊":
    st.sidebar.markdown("Select the Series to display:")
    series_choice = st.sidebar.radio(
        "Select a series:",
        ["2026 - Series 1","2025 - Series 4", "2025 - Series 3", "2025 - Series 2", "2025 - Series 1", "2024 - Sorting League"],
        index=0 
    )
    show_series_stats_page(series_choice)
    
elif view_option == "Player Stats 👤":
    # Call your player summary tab directly
    show_player_summary_tab()
    st.stop()

elif view_option == "Season (year) Stats 📅":
    st.sidebar.markdown("Select the Season to analyze:")
    
    # Radio button for season selection
    season_choice = st.sidebar.radio(
        "Select a season:",
        ["2026", "2025"],
        index=0
    )

    # Map the selected season year to season_id
    season_mapping = {
        "2026": 2,
        "2025": 1
    }
    season_id = season_mapping[season_choice]

    # Call the function with the calculated season_id
    show_player_of_the_year(season_id)
    st.stop()
