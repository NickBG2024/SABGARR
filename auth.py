import streamlit as st
import streamlit_authenticator as stauth

# Authenticate user
def authenticate_user():
    # Load credentials from Streamlit secrets
    credentials = {
        "usernames": {
            "admin_user": {
                "name": st.secrets["credentials"]["usernames.admin_user.name"],
                "password": st.secrets["credentials"]["usernames.admin_user.password"]
            }
        }
    }

    # Use streamlit_authenticator to create an authenticator object
    authenticator = stauth.Authenticate(
        credentials,
        "myapp_cookie",
        "auth_key",
        cookie_expiry_days=30
    )

    # Call the authentication method
    name, authentication_status, username = authenticator.login("Login", "main")

    # Display welcome message and logout option
    if authentication_status:
        st.sidebar.write(f"Welcome, {name}!")
        authenticator.logout("Logout", "sidebar")

    return authentication_status, username
