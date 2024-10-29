import mysql.connector
import email
import imaplib
import streamlit as st

# Create a connection to the database
def create_connection():
    try:
        conn = mysql.connector.connect(
            host="sql58.jnb2.host-h.net",
            user="sabga_admin",
            password="6f5f73102v7Y1A",
            database="sabga_test"
        )
        if conn.is_connected():
            st.success("Connected to the database!")
        return conn
    except mysql.connector.Error as e:
        st.error(f"Error connecting to the database: {e}")
        return None

# Check for new emails
def check_for_new_emails():
    # Get email credentials from Streamlit Secrets
    EMAIL = st.secrets["imap"]["email"]
    PASSWORD = st.secrets["imap"]["password"]
    
    # Try connecting to the email server
    try:
        mail = imaplib.IMAP4_SSL('mail.sabga.co.za', 993)
        mail.login(EMAIL, PASSWORD)
        mail.select('inbox')
        st.write("Login successful")
    except imaplib.IMAP4.error as e:
        st.error(f"IMAP login failed: {str(e)}")
    
    # Search for emails with "Admin: A league match was played" in the subject
    status, messages = mail.search(None, '(SUBJECT "Admin: A league match was played")')
    
    # Check the number of emails found
    email_ids = messages[0].split()
    
    # Display how many emails were found
    if email_ids:
        st.write(f"Found {len(email_ids)} emails with 'Admin: A league match was played' in the subject.")
    else:
        st.write("No emails found with this search term in the subject.")
    # Logout from the email server
    mail.logout()
    
# Retrieve the email checker status
def get_email_checker_status():
    conn = create_connection()
    cursor = conn.cursor()
    
    # Ensure the AppSettings table has at least one row
    cursor.execute("SELECT EmailCheckerEnabled FROM AppSettings LIMIT 1")
    result = cursor.fetchone()
    
    # If no row is found, insert default value (enabled) into AppSettings
    if result is None:
        cursor.execute("INSERT INTO AppSettings (EmailCheckerEnabled) VALUES (TRUE)")
        conn.commit()
        status = True  # Default to enabled if no record exists
    else:
        status = result[0]
    
    conn.close()
    return status

# Update the email checker status
def set_email_checker_status(status):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE AppSettings SET EmailCheckerEnabled = %s", (status,))
    conn.commit()
    conn.close()

def add_active_to_matchtype():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        ALTER TABLE MatchType 
        ADD COLUMN Active BOOLEAN DEFAULT TRUE;
    ''')
    conn.commit()
    conn.close()
    
    
# Create the Players table
def create_players_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Players (
            PlayerID INT AUTO_INCREMENT PRIMARY KEY,
            Name VARCHAR(255) NOT NULL,
            Nickname VARCHAR(255),
            Email VARCHAR(255),
            GamesPlayed INT DEFAULT 0,
            TotalWins INT DEFAULT 0,
            TotalLosses INT DEFAULT 0,
            WinPercentage FLOAT DEFAULT 0.0,
            AveragePR FLOAT DEFAULT 0.0,
            MedianPR FLOAT DEFAULT 0.0,
            HighestLuck FLOAT DEFAULT 0.0,
            LowestLuck FLOAT DEFAULT 0.0,
            AverageLuck FLOAT DEFAULT 0.0,
            CurrentLeague VARCHAR(255),
            DaysIdle INT DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Create the Fixtures table
def create_fixtures_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
     CREATE TABLE IF NOT EXISTS Fixtures (
            FixtureID INT AUTO_INCREMENT PRIMARY KEY,
            MatchTypeID INT,
            Player1ID INT,
            Player2ID INT,
            FOREIGN KEY (Player1ID) REFERENCES Players(PlayerID),
            FOREIGN KEY (Player2ID) REFERENCES Players(PlayerID),
            FOREIGN KEY (MatchTypeID) REFERENCES MatchType(MatchTypeID)
        )
    ''')
    conn.commit()
    conn.close()
    
# Create the MatchResults table
def create_match_results_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MatchResults (
            MatchResultID INT AUTO_INCREMENT PRIMARY KEY,
            Date DATE NOT NULL,
            TimeCompleted TIME,
            MatchTypeID INT,
            Player1ID INT,
            Player2ID INT,
            Player1Points INT,
            Player2Points INT,
            Player1PR FLOAT,
            Player2PR FLOAT,
            Player1Luck FLOAT,
            Player2Luck FLOAT,
            FOREIGN KEY (Player1ID) REFERENCES Players(PlayerID),
            FOREIGN KEY (Player2ID) REFERENCES Players(PlayerID),
            FOREIGN KEY (MatchTypeID) REFERENCES MatchType(MatchTypeID)
        )
    ''')
    conn.commit()
    conn.close()

# Create the MatchType table
def create_match_type_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MatchType (
            MatchTypeID INT AUTO_INCREMENT PRIMARY KEY,
            MatchTypeTitle VARCHAR(255) NOT NULL,
            Active BOOLEAN DEFAULT TRUE
        )
    ''')
    conn.commit()
    conn.close()

# Add table for AppSettings
def create_appsettings_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
         CREATE TABLE IF NOT EXISTS AppSettings (
            SettingID INT AUTO_INCREMENT PRIMARY KEY,
            EmailCheckerEnabled BOOLEAN DEFAULT TRUE
        )
    ''')
    conn.commit()
    conn.close()
    
# Insert a new player
def add_player(name, nickname, email):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Players (Name, Nickname, Email) 
        VALUES (%s, %s, %s)
    ''', (name, nickname, email))
    conn.commit()
    conn.close()

# Insert a new match type
def add_match_type(match_type_title):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO MatchType (MatchTypeTitle) 
        VALUES (%s)
    ''', (match_type_title,))
    conn.commit()
    conn.close()

# Insert a new match result
def add_match_result(player1_id, player2_id, player1_points, player2_points, match_type_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO MatchResults 
        (Date, Player1ID, Player2ID, Player1Points, Player2Points, MatchTypeID) 
        VALUES (NOW(), %s, %s, %s, %s, %s)
    ''', (player1_id, player2_id, player1_points, player2_points, match_type_id))
    conn.commit()
    conn.close()

def add_fixture(match_type_id, player1_id, player2_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Fixtures (MatchTypeID, Player1ID, Player2ID)
        VALUES (%s, %s, %s)
    ''', (match_type_id, player1_id, player2_id))
    conn.commit()
    conn.close()

def get_fixtures():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT FixtureID, MatchTypeID, Player1ID, Player2ID 
            FROM Fixtures
        ''')
        fixtures = cursor.fetchall()
        conn.close()

        if not fixtures:
            st.error("No fixtures found.")
        
        return fixtures
    except Exception as e:
        st.error(f"Error retrieving fixtures: {e}")
        return []

# Function to retrieve all players
def get_players():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Players")
        players = cursor.fetchall()
        conn.close()

        if not players:
            st.error("No players found.")
        
        return players
    except Exception as e:
        st.error(f"Error retrieving players: {e}")
        return []

# Function to retrieve all match types
def get_match_types():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM MatchType")
        match_types = cursor.fetchall()
        conn.close()

        if not match_types:
            st.error("No match types found.")
        
        return match_types
    except Exception as e:
        st.error(f"Error retrieving match types: {e}")
        return []

# Function to retrieve all matches
def get_match_results():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM MatchResults")
        matchresults = cursor.fetchall()
        conn.close()

        if not matchresults:
            st.error("No match results found.")
        
        return matchresults
    except Exception as e:
        st.error(f"Error retrieving match results: {e}")
        return []
        
# Retrieve standings
def get_standings():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Name, GamesPlayed, TotalWins, WinPercentage, AveragePR
            FROM Players
            ORDER BY WinPercentage DESC
            LIMIT 10
        ''')
        standings = cursor.fetchall()
        conn.close()

        if not standings:
            st.error("Standings is empty or not found.")
        
        return standings
    except Exception as e:
        st.error(f"Error retrieving standings: {e}")
        return []

# Function to check existing tables
def check_tables():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    conn.close()

    st.write("Tables in the database:", tables)
