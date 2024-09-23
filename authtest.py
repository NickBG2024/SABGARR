import streamlit as st
import streamlit_authenticator as stauth

st.write("Welcome to the authentication app!")

def authenticate_user():
    credentials = {
        "usernames": {
            "admin_user": {
                "name": st.secrets["admin"]["name"],
                "password": st.secrets["admin"]["password"]
            }
        }
    }

    # Display the credentials for debugging (excluding sensitive info)
    st.write("Credentials being used:")
    st.json(credentials)  # This will format it nicely in JSON

    authenticator = stauth.Authenticate(
        credentials,
        "myapp",
        "auth",
        cookie_expiry_days=30
    )

    try:
        st.write("Attempting to log in...")
        # Test different locations
        name, authentication_status, username = authenticator.login("Login", "main")
        
        st.write(f"Authentication status: {authentication_status}")
        
        if authentication_status:
            st.write(f"Welcome {name}!")
        elif authentication_status is False:
            st.error("Username/password is incorrect.")
        else:
            st.warning("Please log in.")
        return authentication_status
    except ValueError as e:
        st.error(f"Login error: {e}")
        return False

# Call the authentication function
is_admin = authenticate_user()

if is_admin:
    st.write("You are authenticated and logged in!")
