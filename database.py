import sqlite3
import pandas as pd

# Function to create a database connection
def create_connection(db_file="backgammon.db"):
    """Create a connection to the SQLite database specified by db_file."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)
    
    return conn

# Function to get leaderboard data
def get_leaderboard(conn):
    """Retrieve leaderboard data from the database."""
    query = "SELECT * FROM leaderboard ORDER BY points DESC"
    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return pd.DataFrame()

# Function to get match history
def get_matches(conn):
    """Retrieve match data from the database."""
    query = "SELECT * FROM matches ORDER BY match_date DESC"
    try:
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"Error fetching matches: {e}")
        return pd.DataFrame()

# Function to insert a player into the database
def insert_player(conn, name, email):
    """Insert a player into the players table."""
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO players (name, email) VALUES (?, ?)", (name, email))
        conn.commit()
    except Exception as e:
        print(f"Error inserting player: {e}")

# Function to insert match data into the database
def insert_match(conn, player_1_values, player_2_values):
    """Insert match data into the matches table."""
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO matches (player_1, player_1_points, player_1_pr, player_1_luck, player_2, player_2_points, player_2_pr, player_2_luck) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                player_1_values[0], player_1_values[1], player_1_values[2], player_1_values[3],
                player_2_values[0], player_2_values[1], player_2_values[2], player_2_values[3],
            )
        )
        conn.commit()
    except Exception as e:
        print(f"Error inserting match data: {e}")
