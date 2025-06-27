import imaplib
import email
import re
import random
import streamlit as st
import pandas as pd
from database import show_player_summary_tab, show_cached_remaining_fixtures_by_series, list_cached_remaining_fixtures, display_cached_matchtype_standings, show_cached_matches_completed, get_completed_matches_for_series, fetch_cached_series_standings, get_series_completed_matches_detailed, get_averagePR_by_matchtype, list_remaining_fixtures_by_series, display_matchtype_standings_full_details_styled, get_fixturescount_by_matchtype, get_matchcount_by_matchtype, display_series_standings_with_points_and_details, display_series_standings_with_points, display_matchtype_standings_with_points_and_details, display_matchtype_standings_with_points, get_matchcount_by_date_and_series, smccc, get_matchcount_by_series, get_fixturescount_by_series, show_matches_completed_by_series, show_matches_completed, display_sorting_series_table, display_series_table, display_series_table_completedonly, display_match_grid, list_remaining_fixtures, display_group_table, get_remaining_fixtures, get_match_results_for_grid, get_player_stats_with_fixtures, get_player_stats_by_matchtype, get_sorting_standings, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone, date

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_container_width=True)  # The image will resize to the width of the page

# Add an icon image to sidebar
st.sidebar.markdown(
    """
    <div style='text-align: center; margin: 10px 5px 10px 5px;'>
        <img src='https://www.sabga.co.za/wp-content/uploads/2020/06/SABGA_logo_tight.jpg' width='200'/>
    </div>
    """, unsafe_allow_html=True
)
st.sidebar.title("LEAGUE STATS:")
st.sidebar.markdown("Select the data to display:")

# Create a radio button section with "Current Series" as the default
series_choice = st.sidebar.radio(
    "Select a series:",  
    ["2025 - Series 3 (coming soon)", "2025 - Series 2", "2025 - Series 1", "2024 - Sorting League","View Stats, Lists and Analysis"],  
    index=1  # Sets "Current Series" as the default selection
)

def league_tab(matchtype_id,league_title):
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

def show_stats_and_analysis():
    st.title("Statistics, Lists and Analysis")
    st.write("The idea is to have loads of statistics, lists and analysis! Some will refer to overall performances, series-specific data, player-specific (improvement, movements, etc) and some between players (head-to-head)") 
    # Create tabs in a section
    tab1, tab2, tab3 = st.tabs(["Player Stats", "League Stats", "Overall Stats"])

    # Content for each tab
    with tab1:    
        st.header("Player Statistics")
        st.write("Stats and data related to players.")
        tab4, tab5, tab6, tab7 = st.tabs(["Player stats - summary page","Player vs Player comparison","Player PR changes","Player match record"])
    with tab2:
        # Create tabs for League Stats
        st.header("Player Statistics")
        st.write("Stats and data related to leagues.")
        tab8, tab9, tab10, tab11 = st.tabs(["League Stats - summary page", "League PR avg. changes", "League movements","League something"])
    with tab3:
        # Create tabs for Overall Stats
        st.header("Overall Statistics")
        st.write("Summary and general stats and tables")
        tab12, tab13, tab14, tab15, tab16, tab17, tab18 = st.tabs(["Best PR performances", "Best average PR across a Series", "Best PR over a year","Best Series to Series PR improvement (%)","Wins with 'toughest' luck differential","Best points % per Series","Longest win streaks"])

    with tab4:
        show_player_summary_tab()
    with tab5:
        st.subheader("🤝 Player vs Player Comparison")
        st.write("Head-to-head records, PR comparisons, luck swings.")
    
    with tab6:
        st.subheader("📈 Player PR Changes")
        st.write("Track PR improvements or regressions across series/leagues.")
    
    with tab7:
        st.subheader("🏅 Player Match Record")
        st.write("Full match history by player, with results, PRs, luck, etc.")

    with tab8:
        st.subheader("📊 League Stats - Summary Page")
        st.write("Overview of league standings, match completions, PR averages, and points %.")
    
    with tab9:
        st.subheader("📈 League PR Average Changes")
        st.write("Track how league-wide PR averages improve or change over time.")
    
    with tab10:
        st.subheader("📊 League Movements")
        st.write("Promotions, relegations, and player movement analysis within leagues.")
    
    with tab11:
        st.subheader("🛠️ League Experimental Analysis")
        st.write("Placeholder for additional league-level insights (TBD).")

    with tab12:
        st.subheader("⭐ Best PR Performances")
        st.write("List of the best individual match PRs recorded across all leagues and series.")
    
    with tab13:
        st.subheader("🏆 Best Average PR Across a Series")
        st.write("Players with the lowest average PR in completed series.")
    
    with tab14:
        st.subheader("📅 Best PR Over a Year")
        st.write("Top PR performers over the course of a calendar year.")
    
    with tab15:
        st.subheader("🔼 Best Series-to-Series PR Improvement (%)")
        st.write("Players with the highest percentage improvement in PR between consecutive series.")
    
    with tab16:
        st.subheader("🎲 Wins with Toughest Luck Differential")
        st.write("Matches where players won despite significant negative luck swings.")
    
    with tab17:
        st.subheader("📈 Best Points % Per Series")
        st.write("Players with the highest points % (points earned / points possible) in each series.")
    
    with tab18:
        st.subheader("🏅 Longest Win Streaks")
        st.write("Players with the longest consecutive match win streaks.")


#2025 - SERIES 2 LEAGUE DATA DISPLAY        
if series_choice == "2025 - Series 2":
    st.write("Loading data for the 2025 - S2 series...")

    #Initialisation variables:
    current_series_id = 6
    matches_played = get_matchcount_by_series(current_series_id)
    total_fixtures = get_fixturescount_by_series(current_series_id)
    # Get today and yesterday's date
    today = date.today()
    yesterday = today - timedelta(days=1)
    # Fetch match count for yesterday
    match_count_yesterday = get_matchcount_by_date_and_series(yesterday.strftime("%Y-%m-%d"), current_series_id)
    
    # Calculate days left until end of series 2 (30 June, 2025)
    end_date = date(2025, 6, 30)
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
    col2.metric("Series 2 progress:",metric_value,match_count_yesterday)
    col2.write("Deadline: 30 June 2025")

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
        pdf_url = "https://www.sabga.co.za/wp-content/uploads/2025/04/SABGA-Round-Robin-Leagues-2025-rules-etc-v5dot1.pdf"
        st.markdown("**The 2025 Round Robin leagues continues with Series 2, taking place 2 Apr 2025 - 30 June 2025, with 74 players competing in eight leagues (A-G). The top four leagues have ten players each, with matches played to 11 points. The next two leagues, E and F, have twelve players each, and play to 9 points. There are also two 'Guppy' groups for new players.**")
        st.markdown(f"All league information (rules, etc) can be found here: [SABGA Round Robin Leagues 2025 - rules etc v5.1.pdf]({pdf_url})", unsafe_allow_html=True)
        st.write("This tab offers an overview: a table showing all players, recent results and remaining fixtures.")
        
        fetch_cached_series_standings(current_series_id)
        show_cached_remaining_fixtures_by_series(current_series_id)
        get_series_completed_matches_detailed(current_series_id)

    # League tabs - dynamically call league_tab() with appropriate matchtype_id
    for i, league_name in enumerate(tab_names[1:], start=1):  # Skip "OVERVIEW"
        with tabs[i]:
            league_tab(matchtype_ids[league_name], league_name)    

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
            league_tab(matchtype_ids[league_name], league_name)    

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

    #display_series_table_completedonly(seriesid)
    #display_series_table(seriesid)
    display_sorting_series_table(seriesid)
    smccc(seriesid)
    #list_remaining_fixtures_by_series(series_id)
    #show_matches_completed_by_series(series_id)

#View Stats and Analysis      
elif series_choice == "View Stats, Lists and Analysis":
    show_stats_and_analysis()
