import imaplib
import email
import re
import streamlit as st
from database import get_standings, get_match_results, check_tables, create_connection, insert_match_result, check_result_exists, get_fixture_id 

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon: Round Robin 2025")
st.write("Welcome to the homepage of the South African Backgammon Round Robin! This page will automatically update to show the latest standings of the SABGA National Round Robin.")

# Checking for new emails etc
def check_for_new_emails():
    # Streamlit title
    st.title("Check for New Match Results via Email")

    # Get email credentials from Streamlit Secrets
    EMAIL = st.secrets["imap"]["email"]
    PASSWORD = st.secrets["imap"]["password"]

    # Try connecting to the email server
    try:
        mail = imaplib.IMAP4_SSL('mail.sabga.co.za', 993)
        mail.login(EMAIL, PASSWORD)
        mail.select('inbox')
        st.write("Login successful")
    except imaplib.IMAP4.error as e:
        st.error(f"IMAP login failed: {str(e)}")
        return

    # Search for new emails with the specified subject
    status, messages = mail.search(None, '(SUBJECT "Admin: A league match was played" SUBJECT "Fwd: Admin: A league match was played")')
    email_ids = messages[0].split()

    # Loop through the emails and extract data
    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, '(RFC822)')

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = msg['subject']

                # Clean up subject
                cleaned_subject = re.sub(r"^(Fwd:|Re:)\s*", "", subject).strip()

                # Extract player data
                match = re.search(r"([^)]+)\s*and\s*[^]+([^)]+)", cleaned_subject)
                if match:
                    player_1_values = match.group(1).split()
                    player_2_values = match.group(2).split()

                    # Prepare the match result data
                    player_1_points, player_1_length, player_1_pr, player_1_luck = player_1_values
                    player_2_points, player_2_length, player_2_pr, player_2_luck = player_2_values

                    # Check if result already exists
                    if check_result_exists(player_1_points, player_1_length, player_2_points, player_2_length):
                        st.write("Match result already exists, skipping...")
                        continue

                    # Match result with the associated fixture (you may need to implement get_fixture_id based on your logic)
                    fixture_id = get_fixture_id(cleaned_subject)
                    if fixture_id:
                        # Write the result to the database
                        insert_match_result(fixture_id, player_1_points, player_1_length, player_1_pr, player_1_luck,
                                            player_2_points, player_2_length, player_2_pr, player_2_luck)
                        st.success("Match result added to the database!")
                    else:
                        st.error("Fixture ID not found for the match.")
                else:
                    st.write(f"No match found for email {email_id}")

    # Logout from the email server
    mail.logout()

# Check if the email checker is enabled
if get_email_checker_status():
    #check_for_new_emails()  # Function that checks for new emails and parses them
    st.info("Email checker not created yet.")
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
