import sqlite3
import streamlit as st

def create_tables():
    conn = sqlite3.connect('backgammon.db')  # Connect to the database file (or create it if it doesn't exist)
    cursor = conn.cursor()

    # SQL for creating Players table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Players (
            PlayerID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            HeroesNickname TEXT,
            Email TEXT UNIQUE,
            GamesPlayed INTEGER DEFAULT 0,
            TotalWins INTEGER DEFAULT 0,
            TotalLosses INTEGER DEFAULT 0,
            WinPercentage REAL AS (CASE WHEN GamesPlayed > 0 THEN (TotalWins * 100.0) / GamesPlayed ELSE 0 END) STORED,
            AveragePR REAL DEFAULT 0.0,
            MedianPR REAL DEFAULT 0.0,
            HighestLuck REAL DEFAULT 0.0,
            LowestLuck REAL DEFAULT 0.0,
            AverageLuck REAL DEFAULT 0.0,
            CurrentLeague TEXT,
            DaysIdle INTEGER DEFAULT 0
        )
    ''')

    # SQL for creating Matches table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Matches (
            MatchID INTEGER PRIMARY KEY AUTOINCREMENT,
            MatchDate DATE DEFAULT (CURRENT_DATE),
            TimeCompleted TIME DEFAULT (CURRENT_TIME),
            MatchTypeID INTEGER,
            Player1ID INTEGER,
            Player2ID INTEGER,
            Player1Points INTEGER,
            Player2Points INTEGER,
            Player1PR REAL,
            Player2PR REAL,
            Player1Luck REAL,
            Player2Luck REAL,
            FOREIGN KEY (Player1ID) REFERENCES Players(PlayerID),
            FOREIGN KEY (Player2ID) REFERENCES Players(PlayerID),
            FOREIGN KEY (MatchTypeID) REFERENCES MatchTypes(MatchTypeID)
        )
    ''')

    # SQL for creating MatchTypes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MatchTypes (
            MatchTypeID INTEGER PRIMARY KEY AUTOINCREMENT,
            MatchTypeTitle TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

    st.success("Tables created successfully!")

# Call the function to create the tables
if st.button("Create Database"):
    create_tables()
