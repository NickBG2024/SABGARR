import streamlit as st

st.title("Tab Test Example")

# Create tabs in a section
tab1, tab2, tab3 = st.tabs(["Leaderboard", "Match History", "Standings"])

# Content for each tab
with tab1:
    st.header("Leaderboard")
    st.write("Display the leaderboard here.")

with tab2:
    st.header("Match History")
    st.write("Display the match history here.")

with tab3:
    st.header("Standings")
    st.write("Display the standings here.")
