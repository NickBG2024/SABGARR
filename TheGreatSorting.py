import imaplib
import email
import re
import streamlit as st
from database import get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon: The Great Sorting 2025")
st.write("Welcome to the homepage of the South African Backgammon Round Robin sorting process, aka The Great Sorting!")
st.write("This page will automatically update to show the latest standings, fixtures and results of the SABGA National Round Robin.")

# Check if the email checker is enabled
if get_email_checker_status():
    check_for_new_emails()  # Function that checks for new emails and parses them
    # Get the current time in hh:mm format
    current_time = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%H:%M")
    # Display the message with the time
    st.info(f"Emails checked at {current_time}")
else:
    st.info("Email checker is currently disabled by the admin.")
    
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

# Initialize the default page as "League Standings"
page = "League Standings"

# Create buttons for each page option
if st.sidebar.button("League Standings"):
    page = "League Standings"
elif st.sidebar.button("League Fixtures"):
    page = "League Fixtures"
elif st.sidebar.button("Result History"):
    page = "Result History"

# Show League Standings
if page == "League Standings":
    standings = get_standings()
    st.write("SABGA Round Robin: 2025")
    # Create tabs in a section
    tab1, tab2, tab3 = st.tabs(["Current Season", "Past Seasons", "Round Robin Stats"])

    # Content for each tab
    with tab1:
        st.header("Current Season")
        st.write("SABGA Round Robin Season 1 (Jan 2024 - March 2024)")
        st.table(standings)

    with tab2:
        st.header("Past Seasons")
        st.write("Use the tabs below to browse previous season standings.")

    with tab3:
        st.header("Round Robin Stats")
        st.write("Display the RR stats here.")
        # Create tabs for additional stats
        tab4, tab5, tab6, tab7 = st.tabs(["Stats by Player", "Stats by Season", "Stats by Year", "Historical Stats"])
        with tab4:
            st.header("Stats by Player")
            st.write("Select a player from the dropdown to view their stats")
        with tab5:
            st.header("Stats by Season")
            st.write("Select the season from the dropdown to view season's stats")
        with tab6:
            st.header("Stats by Year")
            st.write("Select the year from the dropdown to view year's stats")
        with tab7:
            st.header("Historical Stats")
            st.write("Overall stats, from all time:")

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

# In the main section
#st.sidebar.metric(label="Players", value="34", delta="5")

# In the sidebar
#st.sidebar.metric(label="Matches played", value="70%", delta="-3%")
 