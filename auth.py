# auth.py
import streamlit as st

def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if username == "admin" and password == "secret":  # Replace with secure method
        return True
    else:
        return False
