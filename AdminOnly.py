import streamlit as st
from database import create_connection

# Add a player to the Players table
def add_player(name, nickname, email):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Players (Name, Nickname, Email) 
        VALUES (%s, %s, %s)
    ''', (name, nickname, email))
    conn.commit()
    conn.close()
    st.success(f"Player {name} added to the database.")

# Add a match type to the MatchType table
def add_match_type(match_type_title):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO MatchType (MatchTypeTitle) 
        VALUES (%s)
    ''', (match_type_title,))
    conn.commit()
    conn.close()
    st.success(f"Match type '{match_type_title}' added to the database.")

# Add match result (this is a placeholder function, implement actual logic if needed)
def add_match_result(player1_id, player2_id, player1_points, player2_points):
    st.write(f"Result added: Player 1 (ID {player1_id}) scored {player1_points}, Player 2 (ID {player2_id}) scored {player2_points}.")
    # Implement actual match result saving to DB here

# Sidebar buttons to choose which form to display
st.sidebar.title("Admin Only")
option = st.sidebar.radio(
    "Select an option:",
    ("Add Player", "Add Match Type", "Add Match Result")
)

# Main section
st.title("SABGA Admin Only")

# Display the form based on sidebar selection
if option == "Add Player":
    st.header("Add a New Player")

    # Initialize session state for player form
    if 'player_name' not in st.session_state:
        st.session_state['player_name'] = ""
    if 'player_nickname' not in st.session_state:
        st.session_state['player_nickname'] = ""
    if 'player_email' not in st.session_state:
        st.session_state['player_email'] = ""

    with st.form(key="add_player_form"):
        player_name = st.text_input("Player Name", value=st.session_state['player_name'], key="player_name_input")
        player_nickname = st.text_input("Nickname", value=st.session_state['player_nickname'], key="player_nickname_input")
        player_email = st.text_input("Email", value=st.session_state['player_email'], key="player_email_input")
        submit_player = st.form_submit_button(label="Add Player")

        if submit_player and player_name and player_email:
            add_player(player_name, player_nickname, player_email)
            st.session_state['player_name'] = ""
            st.session_state['player_nickname'] = ""
            st.session_state['player_email'] = ""

elif option == "Add Match Type":
    st.header("Add a New Match Type")

    # Initialize session state for match type form
    if 'match_type' not in st.session_state:
        st.session_state['match_type'] = ""

    with st.form(key="add_match_type_form"):
        match_type = st.text_input("Match Type Title", value=st.session_state['match_type'], key="match_type_input")
        submit_match_type = st.form_submit_button(label="Add Match Type")

        if submit_match_type and match_type:
            add_match_type(match_type)
            st.session_state['match_type'] = ""

elif option == "Add Match Result":
    st.header("Add a Match Result")

    with st.form(key="add_match_result_form"):
        player1_id = st.text_input("Player 1 ID")
        player2_id = st.text_input("Player 2 ID")
        player1_points = st.text_input("Player 1 Points")
        player2_points = st.text_input("Player 2 Points")
        submit_match_result = st.form_submit_button(label="Add Match Result")

        if submit_match_result and player1_id and player2_id and player1_points and player2_points:
            add_match_result(player1_id, player2_id, player1_points, player2_points)
