import mysql.connector
import streamlit as st

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

# Create the Matches table
def create_matches_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Matches (
            MatchID INT AUTO_INCREMENT PRIMARY KEY,
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

# Example function to retrieve matches
def get_matches():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Matches")
        matches = cursor.fetchall()
        conn.close()

        if not matches:
            st.error("No matches found.")
        
        return matches
    except Exception as e:
        st.error(f"Error retrieving matches: {e}")
        return []

# Example function to retrieve leaderboard
def get_leaderboard():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Name, GamesPlayed, TotalWins, WinPercentage, AveragePR
            FROM Players
            ORDER BY WinPercentage DESC
            LIMIT 10
        ''')
        leaderboard = cursor.fetchall()
        conn.close()

        if not leaderboard:
            st.error("Leaderboard is empty or not found.")
        
        return leaderboard
    except Exception as e:
        st.error(f"Error retrieving leaderboard: {e}")
        return []

# Function to check existing tables
def check_tables():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    conn.close()

    st.write("Tables in the database:", tables)
