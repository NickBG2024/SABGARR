import imaplib
import email
import re
import random
import streamlit as st
import pandas as pd
from database import display_series_standings_with_points, display_matchtype_standings_with_points, display_matchtype_standings_with_points_bold, smccc, display_series_with_points, get_unique_player_count_by_series, get_matchcount_by_series, get_fixturescount_by_series, show_matches_completed_by_series, show_matches_completed, display_sorting_series_table, display_series_table, display_series_table_completedonly, display_match_grid, list_remaining_fixtures, display_group_table, get_remaining_fixtures, get_match_results_for_grid, get_player_stats_with_fixtures, get_player_stats_by_matchtype, get_sorting_standings, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_container_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("TESTING...") 
matches_played = get_matchcount_by_series(4)
total_fixtures = get_fixturescount_by_series(4)
percentage = (matches_played / total_fixtures) * 100
metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"

# Display the metric in the sidebar
st.sidebar.metric(label="Matches Played", value=metric_value)

col1, col2, col3 = st.columns(3)
col1.title("The Great Sorting!")
col2.metric("Progress...",metric_value, "4")
col3.metric("Players", get_unique_player_count_by_series(4), "3",help="Using series ID = 4")
#standings = get_sorting_standings()
# Create tabs in a section
tab1, tab2, tab3 = st.tabs(["Player Standings", "Sorting Groups (1 - 7)", "2025 Rules etc"])

# Content for each tab
with tab1:
    st.header("Player Standings - ordered by PR")
    st.write("Standings to sort players into Round Robin Leagues (A-F) for 2025 RR League: Series 1.")
    # Example series id
    series_id = 4
    match_type_id = 11
    #Call function to show series table with series_id
    #display_series_table_completedonly(series_id)
    #display_series_table(series_id)
    #display_series_with_points(series_id)
    display_matchtype_standings_with_points_bold(match_type_id)
    #display_sorting_series_table(series_id)

    
    # Example data
    data = [
        ["2025-01-01", "Win", 10, 2.3, 0.5, 2.7, -0.3],
        ["2025-01-02", "Loss", 8, 3.0, -0.1, 1.8, 0.8],
    ]
    
    # Create a DataFrame
    df = pd.DataFrame(
        {
            "Date Completed": [row[0] for row in data],
            "Result": [row[1] for row in data],
            "Score": [row[2] for row in data],
            "Winner PR": [row[3] for row in data],
            "Winner Luck": [row[4] for row in data],
            "Loser PR": [row[5] for row in data],
            "Loser Luck": [row[6] for row in data],
        }
    )
    
    # Define a custom Styler function to highlight the lower PR
    def highlight_lower_pr(row):
        # Determine the lower PR value
        min_pr = min(row["Winner PR"], row["Loser PR"])
        styles = [
            "font-weight: bold;" if value == min_pr else "" for value in row[["Winner PR", "Loser PR"]]
        ]
        # Return styles for all columns
        return [""] * (len(row) - 2) + styles
    
    # Apply the Styler to the DataFrame
    styled_df = df.style.apply(highlight_lower_pr, axis=1)
    
    # Display in Streamlit
    st.dataframe(styled_df)

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
    #show_matches_completed_by_series(series_id)
    smccc(series_id)
with tab2:
    # Create tabs for additional stats
    tab4, tab5, tab6, tab7, tab8, tab9, tab10  = st.tabs(["Group 1", "Group 2", "Group 3", "Group 4", "Group 5","Group 6","Group 7"])
with tab3:
    # Title for the page
    st.title("Streamlit PDF Viewer")
    
    # Add the PDF viewer
    pdf_url = "https://www.sabga.co.za/wp-content/uploads/2025/01/SABGA-Round-Robin-Leagues-2025-rules-etc-v3dot1.pdf"  # Replace with your PDF's URL
    st.markdown(
        f"""
        <iframe src="{pdf_url}" width="700" height="1000" frameborder="0"></iframe>
        """,
        unsafe_allow_html=True,
    )
    with tab4:
        display_series_standings_with_points(series_id)        
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
