import streamlit as st
import streamlit_authenticator as stauth

# Authenticate user
def authenticate_user():
    # Load credentials from Streamlit secrets
    credentials = {
        "usernames": {
            "admin_user": {
                "name": st.secrets["admin"]["name"],
                "password": st.secrets["admin"]["password"]
            }
        }
    }

    # Use streamlit_authenticator to create an authenticator object
    authenticator = stauth.Authenticate(
        credentials,
        "myapp",
        "auth",
        cookie_expiry_days=30
    )

    # Call the authentication method
    name, authentication_status, username = authenticator.login("Login", "mail")  # Keep 'main' or change to 'sidebar'

    return authentication_status
