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

# Initialize session state for form inputs
if 'player_name' not in st.session_state:
    st.session_state['player_name'] = ""
if 'player_nickname' not in st.session_state:
    st.session_state['player_nickname'] = ""
if 'player_email' not in st.session_state:
    st.session_state['player_email'] = ""

if 'match_type' not in st.session_state:
    st.session_state['match_type'] = ""

# Streamlit admin panel
st.sidebar.title("Admin Only")
st.sidebar.write("Populate the database.")

# Add player section
with st.sidebar.form(key="add_player_form"):
    st.write("Add a new player")
    player_name = st.text_input("Player Name", value=st.session_state['player_name'])
    player_nickname = st.text_input("Nickname", value=st.session_state['player_nickname'])
    player_email = st.text_input("Email", value=st.session_state['player_email'])
    submit_player = st.form_submit_button(label="Add Player")

    if submit_player and player_name and player_email:
        add_player(player_name, player_nickname, player_email)
        # Clear the form inputs after submission
        st.session_state['player_name'] = ""
        st.session_state['player_nickname'] = ""
        st.session_state['player_email'] = ""
        st.experimental_rerun()  # This will refresh the form

# Add match type section
with st.sidebar.form(key="add_match_type_form"):
    st.write("Add a new match type")
    match_type = st.text_input("Match Type Title", value=st.session_state['match_type'])
    submit_match_type = st.form_submit_button(label="Add Match Type")

    if submit_match_type and match_type:
        add_match_type(match_type)
        # Clear the form input after submission
        st.session_state['match_type'] = ""
        st.experimental_rerun()  # This will refresh the form
