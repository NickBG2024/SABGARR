import streamlit as st
import streamlit_authenticator as stauth

def authenticate_user():
    credentials = {
        "usernames": {
            "admin_user": {
                "name": st.secrets["credentials"]["usernames.admin_user.name"],
                "password": st.secrets["credentials"]["usernames.admin_user.password"]
            }
        }
    }

    authenticator = stauth.Authenticate(
        credentials,
        "myapp",
        "auth",
        cookie_expiry_days=30
    )

    name, authentication_status, username = authenticator.login("Login", "main")

    return authentication_status
