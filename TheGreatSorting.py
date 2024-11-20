import imaplib
import email
import re
import streamlit as st
import pandas as pd
from database import get_player_stats_by_matchtype, get_sorting_standings, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon: The Great Sorting 2025")
st.write("Welcome to the homepage of the South African Backgammon Round Robin sorting process, aka The Great Sorting!")
st.write("This page will automatically update to show the latest standings, fixtures and results of the SABGA National Round Robin.")
    
# Add an icon image to sidebar
st.sidebar.markdown(
    """
    <div style='text-align: center; margin: 20px 5px 20px 5px;'>
        <img src='https://www.sabga.co.za/wp-content/uploads/2020/06/SABGA_logo_tight.jpg' width='250'/>
    </div>
    """, unsafe_allow_html=True
)

# Sidebar with buttons instead of dropdown
st.sidebar.title("Display selection:")

# Initialize the default page as "Player "
page = "Player Standings"

# Create buttons for each page option
if st.sidebar.button("Player Standings"):
    page = "Player Standings"
elif st.sidebar.button("League Fixtures"):
    page = "League Fixtures"
elif st.sidebar.button("Result History"):
    page = "Result History"

# Show Player Standings
if page == "Player Standings":
    standings = get_sorting_standings()
    st.write("SABGA Round Robin: 2025")
    # Create tabs in a section
    tab1, tab2 = st.tabs(["Player Standings", "Sorting Groups"])

    # Content for each tab
    with tab1:
        st.header("")
        st.write("Player Standings - ordered by PR")
        st.table(standings)

    with tab2:
        st.header("Sorting Group details")
        st.write("Select a group below")
        # Create tabs for additional stats
        tab3, tab4, tab5, tab6 = st.tabs(["Group 1", "Group 2", "Group 3", "Group 4"])
        with tab3:
            st.header("Sorting Group 1")
            st.write("Sorting Group 1:")

            player_stats = get_player_stats_by_matchtype(4)
            if player_stats:
                # Format data for display
                formatted_stats = []
                for stat in player_stats:
                    name_with_nickname = f"{stat[0]} ({stat[1]})"  # Combine Name and Nickname
                    wins = stat[2]
                    losses = stat[3]
                    games_played = stat[4]
                    win_percentage = round((wins / games_played) * 100, 2) if games_played > 0 else 0
                    avg_pr = round(stat[5], 2) if stat[5] is not None else "N/A"
                    avg_luck = round(stat[6], 2) if stat[6] is not None else "N/A"
                    formatted_stats.append(
                        [name_with_nickname, wins, losses, win_percentage, avg_pr, avg_luck]
                    )
        
                # Convert to DataFrame for display
                df = pd.DataFrame(
                    formatted_stats, 
                    columns=["Name (Nickname)", "Wins", "Losses", "Win%", "Average PR", "Average Luck"]
                )
                
                # Sort by Average PR (ascending)
                df = df.sort_values(by="Average PR", ascending=True)
        
                # Display the table
                st.dataframe(df)
            st.write("To add: table, outstanding fixtures, match-grid")
            st.write("Maybe a metric of completion?")
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

# Show League Fixtures
elif page == "League Fixtures":
    # Fetch all match types
    match_types = get_match_types()

    # Filter active match types and create a list of titles
    active_match_types = [mt for mt in match_types if mt[3] == 1]  # Filter only active types
    match_type_titles = [mt[1] for mt in active_match_types]  # Extract MatchTypeTitle for button labels

    # Display buttons for each match type
    for title in match_type_titles:
        if st.button(title):
            selected_match_type = title
            break
    else:
        selected_match_type = None

    # Show fixtures if a match type is selected
    if selected_match_type:
        fixtures = get_fixtures_with_names_by_match_type(selected_match_type)
        if fixtures:
            fixture_data = pd.DataFrame(fixtures, columns=["Match Type", "Player 1", "Player 2", "Completed"])
            st.table(fixture_data)
        else:
            st.write("No fixtures found in the database.")
            st.write("We are currently between seasons, stay tuned for upcoming fixtures.")

# Show Result History
elif page == "Result History":
    st.subheader("Match Results Nicely Formatted:")
    matchresults = get_match_results_nicely_formatted()
    if matchresults:
            # Convert list of tuples to a DataFrame for table display
            matchresults_data = pd.DataFrame(matchresults, columns=[
                "MatchResult ID", "Date", "Time Completed", "MatchTypeID",
                "Player1ID", "Player2ID", "Player 1 pts", "Player 2 pts",
                "Player 1 PR", "Player 2 PR", "Player 1 Luck", "Player 2 Luck"
            ])
    
            # Format date and time columns, if needed
            matchresults_data["Date"] = pd.to_datetime(matchresults_data["Date"]).dt.date
            matchresults_data["Time Completed"] = matchresults_data["Time Completed"].astype(str)
    
            st.table(matchresults_data)
    else:
            st.write("No match results found in the database.")
 
