import streamlit as st
from database import get_standings, get_match_results, check_tables, get_email_checker_status, check_for_new_emails

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon: Round Robin 2025")
st.write("Welcome to the homepage of the South African Backgammon Round Robin! This page will automatically update to show the latest standings of the SABGA National Round Robin.")

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
