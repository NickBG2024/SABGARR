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
    name, authentication_status, username = authenticator.login("Login", "sidebar")

    if authentication_status:
        st.success(f"Welcome {name}!")
    elif authentication_status is False:
        st.error("Username or password is incorrect.")
    elif authentication_status is None:
        st.warning("Please enter your username and password.")
        
    return authentication_status

