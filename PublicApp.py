import streamlit as st
from database import get_standings, get_match_results, check_tables

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

# Public-facing app for all users
st.title("SABGA Backgammon: Round Robin 2025")
st.write("Welcome to the homepage of the South African Backgammon Round Robin! This page will automatically update to show the latest standings of the SABGA National Round Robin.")

# Add an icon image to sidebar
st.sidebar.markdown(
    """
    <div style='text-align: center; margin: 20px 5px 20px 5px;'>
        <img src='https://www.sabga.co.za/wp-content/uploads/2020/06/SABGA_logo_tight.jpg' width='250'/>
    </div>
    """, unsafe_allow_html=True
)


st.sidebar.title("Display selection: ")
page = st.sidebar.selectbox("View", ["Leaderboard", "Fixtures", "Match History"])

# Show Standings
if page == "Standings":
    standings = get_standings()
    st.table(standings)

# Show Fixtures
elif page == "Fixtures":
    st.write("Fixtures will be listed here")

# Show Match History
elif page == "Match History":
    match_results = get_match_results()
    st.table(match_results)

# In the main section
st.sidebar.metric(label="Players", value="34", delta="5")

# In the sidebar
st.sidebar.metric(label="Matches played", value="70%", delta="-3%")
