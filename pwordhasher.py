import bcrypt

password = "rainyday"
hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

print(f"Hashed password: {hashed_password}")
