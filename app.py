import streamlit as st
import re
from auth import authenticate_user
from database import create_connection, insert_match, get_leaderboard, get_matches, insert_player

# Connect to the database
conn = create_connection()

# Authenticate the user
is_admin = authenticate_user()

# Streamlit title
st.title("Backgammon Match Results")

if is_admin:
    st.sidebar.title("Admin Dashboard")
    option = st.sidebar.selectbox("Choose an option", ["Player Management", "Match Management"])
    
    if option == "Player Management":
        st.subheader("Player Management")
        player_name = st.text_input("Player Name")
        player_email = st.text_input("Player Email")
        if st.button("Add Player"):
            insert_player(conn, player_name, player_email)
            st.success(f"Player {player_name} added successfully!")
        
        # Display existing players
        st.write("### Existing Players")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players")
        players = cursor.fetchall()
        st.table(players)
    
    elif option == "Match Management":
        st.subheader("Match Management")
        subject = st.text_input("Email Subject")
        if st.button("Process Match"):
            match = re.search(r"\(([^)]+)\)\s*and\s*[^\(]+\(([^)]+)\)", subject.replace("\r\n", " "))
            if match:
                player_1_values = match.group(1)
                player_2_values = match.group(2)
                player_1_stats = player_1_values.split()
                player_2_stats = player_2_values.split()
                insert_match(conn, player_1_stats, player_2_stats)
                st.success("Match data has been saved to the database!")
            else:
                st.error("No match found in the subject.")
else:
    # Public sections
    st.sidebar.title("Backgammon Community")
    page = st.sidebar.selectbox("View", ["Leaderboard", "Round Tables", "Match History"])
    
    if page == "Leaderboard":
        st.title("Leaderboard")
        leaderboard = get_leaderboard()
        st.table(leaderboard)
    elif page == "Round Tables":
        st.title("Round Tables")
        # Implement Round Tables View
    elif page == "Match History":
        st.title("Match History")
        matches = get_matches()
        st.table(matches)
        
