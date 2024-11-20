import imaplib
import email
import re
import streamlit as st
import pandas as pd
from database import get_player_stats_by_matchtype, get_players_by_match_type, get_fixtures_with_names_by_match_type, get_match_results_nicely_formatted, print_table_structure, get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture, get_standings, get_match_types, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_email_checker_status 
from datetime import datetime, timedelta, timezone

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon: Round Robin 2025")
st.write("Welcome to the homepage of the South African Backgammon Round Robin!")
st.write("This page will automatically update to show the latest standings, fixtures and results of the SABGA National Round Robin.")
st.write("Please be patient as League data is fetched from the database...")

def check_for_new_emails():
    #st.title("Check for New Match Results via Email")

    EMAIL = st.secrets["imap"]["email"]
    PASSWORD = st.secrets["imap"]["password"]

    try:
        mail = imaplib.IMAP4_SSL('mail.sabga.co.za', 993)
        mail.login(EMAIL, PASSWORD)
        mail.select('inbox')
        #st.write("Login to Inbox successful")
    except imaplib.IMAP4.error as e:
        st.error(f"IMAP login failed: {str(e)}")
        return

    status, messages = mail.search(None, '(SUBJECT "Admin: A league match was played" SUBJECT "Fwd: Admin: A league match was played")')
    email_ids = messages[0].split()

    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, '(RFC822)')

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = msg['subject']
                cleaned_subject = re.sub(r"^(Fwd:|Re:)\s*", "", subject).strip()
                #st.write(f"Cleaned Subject: {cleaned_subject}")

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8')
                            break
                else:
                    body = msg.get_payload(decode=True).decode('utf-8')

                forwarded_to = re.search(r"To:.*<(.+?)>", body)
                if forwarded_to:
                    forwarded_email = forwarded_to.group(1)
                    #st.write(f"Forwarded email address: {forwarded_email}")

                    match_type_identifier = re.search(r"\+([^@]+)@", forwarded_email)
                    if match_type_identifier:
                        match_type_text = match_type_identifier.group(1)
                        #st.write(f"MatchType Identifier: {match_type_text}")

                        match_type_id = get_match_type_id_by_identifier(match_type_text)
                        if not match_type_id:
                            st.error("MatchTypeID not found for identifier.")
                            continue

                match = re.search(r"between (\w+) \(([^)]+)\) and (\w+) \(([^)]+)\)", cleaned_subject)
                if match:
                    player_1_nickname, player_2_nickname = match.group(1), match.group(3)
                    player_1_stats, player_2_stats = match.group(2).split(), match.group(4).split()

                    if len(player_1_stats) == 4 and len(player_2_stats) == 4:
                        player_1_points, player_1_length, player_1_pr, player_1_luck = player_1_stats
                        player_2_points, player_2_length, player_2_pr, player_2_luck = player_2_stats

                        # Ensure the stats are in the right format
                        player_1_points = float(player_1_points) if '.' in player_1_points else int(player_1_points)
                        player_1_length = float(player_1_length) if '.' in player_1_length else int(player_1_length)
                        player_1_pr = float(player_1_pr)
                        player_1_luck = float(player_1_luck)

                        player_2_points = float(player_2_points) if '.' in player_2_points else int(player_2_points)
                        player_2_length = float(player_2_length) if '.' in player_2_length else int(player_2_length)
                        player_2_pr = float(player_2_pr)
                        player_2_luck = float(player_2_luck)

                        player_1_id = get_player_id_by_nickname(player_1_nickname)
                        player_2_id = get_player_id_by_nickname(player_2_nickname)
                        if not player_1_id or not player_2_id:
                            st.error("Player ID not found for one or both nicknames.")
                            continue

                        # Call get_fixture to retrieve fixture and completion status
                        fixture = get_fixture(match_type_id, player_1_id, player_2_id)
                        if fixture is None or fixture.get("Completed") == 1:
                            # Check if fixture was not found or is already marked as completed
                            #st.error("No matching fixture found or fixture is already completed. Skipping.")
                            continue

                        fixture_id = fixture["FixtureID"]
                        st.write(f"Fixture content: {fixture}")

                        # Calculate the lower value for each player's points
                        player_1_points = min(player_1_points, player_1_length)
                        player_2_points = min(player_2_points, player_2_length)

                        # Now call the insert function with the correct data
                        insert_match_result(
                            fixture_id,
                            player_1_points, player_1_pr, player_1_luck,
                            player_2_points, player_2_pr, player_2_luck,
                            match_type_id, player_1_id, player_2_id
                        )
                        st.success("Match result added to the database!")
                    else:
                        st.error("Player data format is incorrect. Expected 4 values for each player.")
                else:
                    st.write(f"No match data found for email {email_id} - Subject: {subject}")

    # Ensure this line is properly indented to run after the loop is complete
    mail.logout()

# Check if the email checker is enabled
#if get_email_checker_status():
#    check_for_new_emails()  # Function that checks for new emails and parses them
    # Get the current time in hh:mm format
#    current_time = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%H:%M")
    # Display the message with the time
#    st.info(f"Emails checked at {current_time}")
#else:
#    st.info("Email checker is currently disabled by the admin.")
    
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

        # Select Match Type
        # Could edit this to only fetch active match types...
        st.subheader("Player Stats for Selected Match Type")
        match_types = get_match_types()
        match_type_dict = {mt[1]: mt[0] for mt in match_types}  # Map titles to IDs
        
        selected_match_type = st.selectbox("Select Match Type", list(match_type_dict.keys()))
        # Format and Display Player Stats
if selected_match_type:
    match_type_id = match_type_dict[selected_match_type]
    player_stats = get_player_stats_by_matchtype(match_type_id)
    
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
    else:
        st.write("No data found for the selected match type.")


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
