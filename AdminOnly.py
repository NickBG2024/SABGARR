import streamlit as st
import streamlit_authenticator as stauth
from database import create_connection, insert_match, insert_player

# Authenticate the user (only admins)
def authenticate_user():
    credentials = {
        "usernames": {
            "admin_user": {
                "name": "Admin",
                "password": "$2b$12$EF2tc/IEF0fRw6hj06gft.5A1Ojs3KcV5lpehzf4RkDzBI43dbvCW"  # Your hashed password
            }
        }
    }
    
    authenticator = stauth.Authenticate(
        credentials, 
        "myapp", 
        "auth", 
        cookie_expiry_days=30
    )
    
    name, authentication_status, username = authenticator.login("Admin Login", "sidebar")
    
    if authentication_status:
        st.write(f"Welcome, {name}!")
        return True
    elif authentication_status is False:
        st.error("Invalid username/password")
        return False
    else:
        return False

# Main Admin functionality
def admin_panel():
    # Database connection
    conn = create_connection()

    # Admin only controls
    st.title("Admin Dashboard")

    # Example of player management section
    st.subheader("Player Management")
    player_name = st.text_input("Player Name")
    player_email = st.text_input("Player Email")
    
    if st.button("Add Player"):
        insert_player(conn, player_name, player_email)
        st.success(f"Player {player_name} added successfully!")

    # You can add more admin functionalities as needed (match management, etc.)
    
# Entry point for the app
if authenticate_user():
    admin_panel()
