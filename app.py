import streamlit as st
import re
from auth import authenticate_user
from database import create_connection, insert_match

# Connect to the database
conn = create_connection()

# Authenticate the user
is_admin = authenticate_user()

# Streamlit title
st.title("Backgammon Match Results")

if is_admin:
    st.sidebar.title("Admin Dashboard")
    subject = st.text_input("Email Subject")
    
    if st.button("Process Match"):
        match = re.search(r"\(([^)]+)\)\s*and\s*[^\(]+\(([^)]+)\)", subject.replace("\r\n", " "))
        if match:
            player_1_values = match.group(1).split()
            player_2_values = match.group(2).split()
            insert_match(conn, player_1_values, player_2_values)
            st.success("Match data has been saved to the database!")
        else:
            st.error("No match found in the subject.")
else:
    st.sidebar.title("Public Section")
    st.write("Welcome to the Backgammon Community!")
