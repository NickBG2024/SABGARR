import mysql.connector
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
            MatchTypeTitle VARCHAR(255) NOT NULL
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
