import streamlit as st
import streamlit_authenticator as stauth

def authenticate_user():
    authenticator = stauth.Authenticate(
        st.secrets["credentials"],
        st.secrets["cookie"]["name"],
        st.secrets["cookie"]["key"],
        st.secrets["cookie"]["expiry_days"],
        st.secrets["preauthorized"]
    )
    
    name, authentication_status, username = authenticator.login('Login', 'main')
    
    if authentication_status:
        authenticator.logout('Logout', 'sidebar')
        st.sidebar.write(f'Welcome *{name}*')
        return True
    elif authentication_status == False:
        st.error('Username/password is incorrect')
        return False
    elif authentication_status == None:
        st.warning('Please enter your username and password')
        return False
