import streamlit as st

# Content outside the tabs (above)
st.title("SABGA Backgammon Dashboard")
st.write("General stats and announcements can go here.")

# Create tabs in a section
tab1, tab2, tab3 = st.tabs(["Leaderboard", "Match History", "Standings"])

# Content for each tab
with tab1:
    st.header("Leaderboard")
    st.write("This is the leaderboard tab content.")

with tab2:
    st.header("Match History")
    st.write("This is the match history tab content.")

with tab3:
    st.header("Standings")
    st.write("This is the standings tab content.")

# Content outside the tabs (below)
st.write("Footer or additional information can go here.")
