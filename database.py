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

# In database.py
def generate_fixture_entries(match_type_id, player_ids):
    conn = create_connection()
    cursor = conn.cursor()

    # Generate fixtures for each unique pair of players
    for i in range(len(player_ids)):
        for j in range(i + 1, len(player_ids)):
            player1_id = player_ids[i]
            player2_id = player_ids[j]
            cursor.execute(
                """
                INSERT INTO Fixtures (MatchTypeID, Player1ID, Player2ID)
                VALUES (%s, %s, %s)
                """,
                (match_type_id, player1_id, player2_id),
            )

    conn.commit()
    conn.close()

def add_series(series_title):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Series (SeriesTitle)
        VALUES (%s)
    ''', (series_title,))
    conn.commit()
    conn.close()

def get_series():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SeriesID, SeriesTitle
        FROM Series
    ''')
    series = cursor.fetchall()
    conn.close()
    return series

def get_series_match_types(series_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT MT.MatchTypeID, MT.MatchTypeTitle
        FROM SeriesMatchTypes SMT
        JOIN MatchType MT ON SMT.MatchTypeID = MT.MatchTypeID
        WHERE SMT.SeriesID = %s
    ''', (series_id,))
    match_types = cursor.fetchall()
    conn.close()
    return match_types

def add_match_type_to_series(series_id, match_type_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO SeriesMatchTypes (SeriesID, MatchTypeID)
        VALUES (%s, %s)
    ''', (series_id, match_type_id))
    conn.commit()
    conn.close()

def update_match_type_in_series(series_id, match_type_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE SeriesMatchTypes
        SET MatchTypeID = %s
        WHERE SeriesID = %s
    ''', (match_type_id, series_id))
    conn.commit()
    conn.close()

def update_series_title(series_id, series_title):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE Series
        SET SeriesTitle = %s
        WHERE SeriesID = %s
    ''', (series_title, series_id))
    conn.commit()
    conn.close()

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

def alter_matchresults():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            ALTER TABLE MatchResults
            CHANGE COLUMN MatchID MatchResultID INT PRIMARY KEY,
            ADD COLUMN FixtureID INT,
            ADD CONSTRAINT FK_FixtureID FOREIGN KEY (FixtureID) REFERENCES Fixtures(FixtureID);
        ''')
        conn.commit()
        print("MatchResults table altered successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

# Create Series table
def create_series_table():
    conn = create_connection()
    cursor = conn.cursor()
    
    # Create Series table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Series (
            SeriesID INT PRIMARY KEY AUTO_INCREMENT,
            SeriesTitle VARCHAR(100) NOT NULL
        );
    ''')
    
    # Create SeriesMatchTypes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS SeriesMatchTypes (
            SeriesMatchTypeID INT PRIMARY KEY AUTO_INCREMENT,
            SeriesID INT,
            MatchTypeID INT,
            FOREIGN KEY (SeriesID) REFERENCES Series(SeriesID) ON DELETE CASCADE,
            FOREIGN KEY (MatchTypeID) REFERENCES MatchType(MatchTypeID) ON DELETE CASCADE
        );
    ''')
    
    conn.commit()
    print("Series and SeriesMatchTypes tables created successfully.")
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

def get_players_full():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT PlayerID, Name, Nickname, GamesPlayed,AveragePR,CurrentLeague,DaysIdle FROM Players")
        players = cursor.fetchall()
        conn.close()

        if not players:
            st.error("No players found.")
        
        return [(p[0], p[1], p[2], p[3], p[4], p[5],p[6]) for p in players]  # Ensure tuples with (ID, Name, Nickname, GamesPlayed,AvePR,CurrentLeague,DaysIdle)
    except Exception as e:
        st.error(f"Error retrieving players: {e}")
        return []
    
# Function to retrieve all players' ID, Name, Nickname
def get_players_simple():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT PlayerID, Name, Nickname FROM Players")
        players = cursor.fetchall()
        conn.close()

        if not players:
            st.error("No players found.")
        
        return [(p[0], p[1], p[2]) for p in players]  # Ensure tuples with (ID, Name, Nickname)
    except Exception as e:
        st.error(f"Error retrieving players: {e}")
        return []

# Function to retrieve all match types
def get_match_types():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MatchTypeID, MatchTypeTitle, Active FROM MatchType")
        match_types = cursor.fetchall()
        conn.close()

        if not match_types:
            st.error("No match types found.")
        
        return [(mt[0], mt[1], mt[2]) for mt in match_types]  # Ensure tuples with (ID, Title, Active)
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
