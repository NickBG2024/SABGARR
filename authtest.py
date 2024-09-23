import streamlit as st
import streamlit_authenticator as stauth

st.write("welcome")

def authenticate_user():
    credentials = {
        "usernames": {
            "admin_user": {
                "name": st.secrets["admin"]["name"],
                "password": st.secrets["admin"]["password"]
            }
        }
    }

    authenticator = stauth.Authenticate(
        credentials,
        "myapp",
        "auth",
        cookie_expiry_days=30
    )

    try:
        name, authentication_status, username = authenticator.login("Login", "main")
        if authentication_status:
            st.write(f"Welcome {name}!")
        elif authentication_status is False:
            st.error("Username/password is incorrect.")
        return authentication_status
    except ValueError as e:
        st.error(f"Login error: {e}")
        return False
