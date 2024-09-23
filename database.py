import sqlite3

def create_connection():
    conn = sqlite3.connect("backgammon_matches.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_1_points REAL,
            player_1_length REAL,
            player_1_pr REAL,
            player_1_luck REAL,
            player_2_points REAL,
            player_2_length REAL,
            player_2_pr REAL,
            player_2_luck REAL
        )
    ''')
    conn.commit()
    return conn

def insert_match(conn, p1_stats, p2_stats):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO matches 
        (player_1_points, player_1_length, player_1_pr, player_1_luck,
         player_2_points, player_2_length, player_2_pr, player_2_luck)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (p1_stats[0], p1_stats[1], p1_stats[2], p1_stats[3],
          p2_stats[0], p2_stats[1], p2_stats[2], p2_stats[3]))
    conn.commit()
