import sqlite3

def get_connection():
    conn = sqlite3.connect("backgammon_matches.db")
    return conn

def create_connection():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        player_1_points REAL,
                        player_1_length REAL,
                        player_1_pr REAL,
                        player_1_luck REAL,
                        player_2_points REAL,
                        player_2_length REAL,
                        player_2_pr REAL,
                        player_2_luck REAL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL
                    )''')
    conn.commit()
    return conn

def insert_match(conn, p1_stats, p2_stats):
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO matches 
                      (player_1_points, player_1_length, player_1_pr, player_1_luck,
                       player_2_points, player_2_length, player_2_pr, player_2_luck)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (float(p1_stats[0]), float(p1_stats[1]), float(p1_stats[2]), float(p1_stats[3]),
                       float(p2_stats[0]), float(p2_stats[1]), float(p2_stats[2]), float(p2_stats[3])))
    conn.commit()

def get_leaderboard():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT players.name, 
                             COUNT(matches.id) as matches_played, 
                             SUM(matches.player_1_points + matches.player_2_points) as total_points
                      FROM players
                      LEFT JOIN matches ON players.id = matches.id  # Adjust based on actual relationship
                      GROUP BY players.name
                      ORDER BY total_points DESC''')
    results = cursor.fetchall()
    conn.close()
    return results

def get_matches():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM matches ORDER BY id DESC''')
    results = cursor.fetchall()
    conn.close()
    return results

def insert_player(conn, name, email):
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO players (name, email) VALUES (?, ?)''', (name, email))
    conn.commit()

def edit_player(conn, player_id, name, email):
    cursor = conn.cursor()
    cursor.execute('''UPDATE players SET name = ?, email = ? WHERE id = ?''', (name, email, player_id))
    conn.commit()

def delete_player(conn, player_id):
    cursor = conn.cursor()
    cursor.execute('''DELETE FROM players WHERE id = ?''', (player_id,))
    conn.commit()
