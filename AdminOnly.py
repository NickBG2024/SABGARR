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

# Streamlit admin panel
st.sidebar.title("Admin Only")
st.sidebar.write("Populate the database.")

# Add player section
with st.sidebar.form(key="add_player_form"):
    st.write("Add a new player")
    player_name = st.text_input("Player Name")
    player_nickname = st.text_input("Nickname")
    player_email = st.text_input("Email")
    submit_player = st.form_submit_button(label="Add Player")

    if submit_player and player_name and player_email:
        add_player(player_name, player_nickname, player_email)

# Add match type section
with st.sidebar.form(key="add_match_type_form"):
    st.write("Add a new match type")
    match_type = st.text_input("Match Type Title")
    submit_match_type = st.form_submit_button(label="Add Match Type")

    if submit_match_type and match_type:
        add_match_type(match_type)
