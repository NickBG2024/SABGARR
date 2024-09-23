import streamlit as st
import bcrypt

# Define your password
password = "Chregan123@"

# Hash the password
hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Display the hashed password using Streamlit
st.write(f"Hashed password: {hashed_password}")
