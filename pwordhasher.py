import streamlit as st
import bcrypt

# Password to be hashed
password = "Rambiz123@".encode()

# Hash the password
hashed = bcrypt.hashpw(password, bcrypt.gensalt())

# Print the hashed password
print("Hashed password:", hashed.decode())  # Ensure it's printed as a single string

# Display the hashed password using Streamlit
st.write(f"Hashed password: {hashed.decode()}")
