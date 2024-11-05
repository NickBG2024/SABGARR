import imaplib
import email
import re
import streamlit as st
from database import get_player_id_by_nickname, get_match_type_id_by_identifier, check_result_exists, insert_match_result, get_fixture_id, get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_fixture_id, get_email_checker_status 
from datetime import datetime, timedelta

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon: Round Robin 2025")
st.write("Welcome to the homepage of the South African Backgammon Round Robin! This page will automatically update to show the latest standings of the SABGA National Round Robin.")

# Checking for new emails etc
# Checking for new emails etc
def check_for_new_emails():
    st.title("Check for New Match Results via Email")

    # Get email credentials from Streamlit Secrets
    EMAIL = st.secrets["imap"]["email"]
    PASSWORD = st.secrets["imap"]["password"]

    try:
        mail = imaplib.IMAP4_SSL('mail.sabga.co.za', 993)
        mail.login(EMAIL, PASSWORD)
        mail.select('inbox')
        st.write("Login to Inbox successful")
    except imaplib.IMAP4.error as e:
        st.error(f"IMAP login failed: {str(e)}")
        return

    # Search for new emails with the specified subject
    status, messages = mail.search(None, '(SUBJECT "Admin: A league match was played" SUBJECT "Fwd: Admin: A league match was played")')
    email_ids = messages[0].split()

    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, '(RFC822)')

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = msg['subject']
                cleaned_subject = re.sub(r"^(Fwd:|Re:)\s*", "", subject).strip()
                st.write(f"Cleaned Subject: {cleaned_subject}")

                # Extract the body of the email
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8')
                            break
                else:
                    body = msg.get_payload(decode=True).decode('utf-8')

                # Extract forwarded email address and MatchType identifier
                forwarded_to = re.search(r"To:.*<(.+?)>", body)
                if forwarded_to:
                    forwarded_email = forwarded_to.group(1)
                    st.write(f"Forwarded email address: {forwarded_email}")

                    match_type_identifier = re.search(r"\+([^@]+)@", forwarded_email)
                    if match_type_identifier:
                        match_type_text = match_type_identifier.group(1)
                        st.write(f"MatchType Identifier: {match_type_text}")

                        # Get MatchTypeID using the identifier
                        match_type_id = get_match_type_id_by_identifier(match_type_text)
                        if not match_type_id:
                            st.error("MatchTypeID not found for identifier.")
                            continue

                # Extract player data from the subject line
                match = re.search(r"between ([^ ]+) ([^)]+) and ([^ ]+) ([^)]+)", cleaned_subject)
                if match:
                    player_1_nickname = match.group(1)
                    player_1_stats = match.group(2).split()
                    player_2_nickname = match.group(3)
                    player_2_stats = match.group(4).split()

                    # Print the raw stats for debugging
                    st.write("Raw Player 1 Stats:", player_1_stats)
                    st.write("Raw Player 2 Stats:", player_2_stats)

                    # Ensure each player has exactly four pieces of information
                    if len(player_1_stats) != 4 or len(player_2_stats) != 4:
                        st.error("Player data format is incorrect. Expected 4 values for each player.")
                    else:
                        player_1_points, player_1_length, player_1_pr, player_1_luck = player_1_stats
                        player_2_points, player_2_length, player_2_pr, player_2_luck = player_2_stats

                        # Print unpacked values for debugging
                        st.write("Player 1 Details - Nickname: {}, Points: {}, Length: {}, PR: {}, Luck: {}".format(
                            player_1_nickname, player_1_points, player_1_length, player_1_pr, player_1_luck))
                        st.write("Player 2 Details - Nickname: {}, Points: {}, Length: {}, PR: {}, Luck: {}".format(
                            player_2_nickname, player_2_points, player_2_length, player_2_pr, player_2_luck))

                        # Map player nicknames to IDs
                        player_1_id = get_player_id_by_nickname(player_1_nickname)
                        player_2_id = get_player_id_by_nickname(player_2_nickname)
                        if not player_1_id or not player_2_id:
                            st.error("Player ID not found for one or both nicknames.")
                            continue

                        # Check if the match is already recorded or completed
                        fixture = get_fixture_id(match_type_id, player_1_id, player_2_id)
                        if not fixture:
                            st.error("Fixture ID not found for the match.")
                            continue

                        if fixture["Completed"]:
                            st.write("Match result already recorded, skipping...")
                            continue

                        # Insert match result into the database
                        insert_match_result(
                            fixture["FixtureID"],
                            player_1_points, player_1_length, player_1_pr, player_1_luck,
                            player_2_points, player_2_length, player_2_pr, player_2_luck
                        )
                        mark_fixture_as_completed(fixture["FixtureID"])
                        st.success("Match result added to the database!")
                else:
                    st.write(f"No match data found for email {email_id} - Subject: {subject}")

    mail.logout()

# Check if the email checker is enabled
if get_email_checker_status():
    check_for_new_emails()  # Function that checks for new emails and parses them
    # Get the current time in hh:mm format
    current_time = (datetime.utcnow() + timedelta(hours=2)).strftime("%H:%M")
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


st.sidebar.title("Display selection: ")
page = st.sidebar.selectbox("View", ["Standings", "Fixtures", "Match History"])

# Show Standings
if page == "Standings":
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
        # Create tabs in a section
        tab4, tab5, tab6, tab7 = st.tabs(["Stats by Player", "Stats by Season", "Stats by Year", "Historical Stats"])
        # Content for each tab
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

# Show Fixtures
elif page == "Fixtures":
    st.write("We are currently between seasons, stay tuned for upcoming fixtures.")

# Show Match History
elif page == "Match History":
    match_results = get_match_results()
    st.table(match_results)

# In the main section
st.sidebar.metric(label="Players", value="34", delta="5")

# In the sidebar
st.sidebar.metric(label="Matches played", value="70%", delta="-3%")
