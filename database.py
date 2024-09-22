# database.py
import sqlite3

def get_connection():
    conn = sqlite3.connect("backgammon.db")
    return conn

def get_leaderboard():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leaderboard ORDER BY points DESC")
    results = cursor.fetchall()
    conn.close()
    return results

def get_matches():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches ORDER BY date DESC")
    results = cursor.fetchall()
    conn.close()
    return results

# Insert or update functions for players and matches go here
