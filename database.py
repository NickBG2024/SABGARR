import mysql.connector
import email
import imaplib
import streamlit as st
import datetime
import pandas as pd

# Create a connection to the database
def create_connection():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["database"]["host"],
            user=st.secrets["database"]["user"],
            password=st.secrets["database"]["password"],
            database=st.secrets["database"]["database"]
        )
        if conn.is_connected():
            return conn
    except mysql.connector.Error as e:
        st.error(f"Error connecting to the database: {e}")
        return None

def list_players_alphabetically():
    try:
        # Establish connection
        conn = create_connection()
        cursor = conn.cursor()

        # Query to get players sorted by name
        query = "SELECT Name FROM Players ORDER BY Name ASC;"
        cursor.execute(query)

        # Fetch all results
        players = [row[0] for row in cursor.fetchall()]
        return players

    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return []

    finally:
        # Ensure the connection is closed
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

# Function to Check for Duplicates
def is_duplicate_player(player_name, heroes_nickname, email):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM Players 
        WHERE Name = %s OR Nickname = %s OR Email = %s
    """, (player_name, heroes_nickname, email))
    duplicate_count = cursor.fetchone()[0]
    conn.close()
    return duplicate_count > 0

def get_remaining_fixtures(match_type_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
        SELECT
            p1.Name AS Player1,
            p2.Name AS Player2
        FROM
            Fixtures f
        LEFT JOIN Players p1 ON f.Player1ID = p1.PlayerID
        LEFT JOIN Players p2 ON f.Player2ID = p2.PlayerID
        WHERE
            f.MatchTypeID = %s AND f.Completed = 0
        """

        cursor.execute(query, (match_type_id,))
        remaining_fixtures = cursor.fetchall()
        conn.close()

        return remaining_fixtures
    except Exception as e:
        st.error(f"Error retrieving remaining fixtures: {e}")
        return []

def display_match_grid(match_type_id):
    # Fetch match results for the specified match type
    match_results = get_match_results_for_grid(match_type_id)
    if match_results:
        # Create a list of unique player names
        player_names = set()
        for result in match_results:
            player_names.add(result[1])  # Player 1
            player_names.add(result[3])  # Player 2

        # Sort player names for consistent order
        player_names = sorted(player_names)

        # Initialize an empty DataFrame with player names as both rows and columns
        score_df = pd.DataFrame(
            "–",  # Default value
            index=player_names,
            columns=player_names
        )

        # Populate the DataFrame with match results
        for result in match_results:
            player1_name = result[1]
            player2_name = result[3]
            player1_points = result[4]
            player2_points = result[5]

            if player1_points is not None and player2_points is not None:
                score_df.at[player1_name, player2_name] = f"{player1_points} - {player2_points}"
                score_df.at[player2_name, player1_name] = f"{player2_points} - {player1_points}"

        def highlight_diagonal(df):
            # Create a blank style DataFrame with the same shape as the input DataFrame
            style = pd.DataFrame("", index=df.index, columns=df.columns)
            # Loop through the diagonal and apply the style
            for i in range(min(len(df), len(df.columns))):  # Handle rectangular DataFrames gracefully
                style.iloc[i, i] = "background-color: #505050; color: #505050;"  # Dark gray with invisible text

            return style

        # Apply the styling function
        styled_df = score_df.style.apply(highlight_diagonal, axis=None)

        # Display the styled DataFrame
        st.subheader("Match Results Grid:")
        st.dataframe(styled_df)  # Use st.dataframe for styling support
    else:
        st.write("No match results available for this match type.")
        
def list_remaining_fixtures(match_type_id):
    # Fetch remaining fixtures for the selected match type
    remaining_fixtures = get_remaining_fixtures(match_type_id)
    if remaining_fixtures:
        st.subheader("Remaining Fixtures:")
        for fixture in remaining_fixtures:
            player1, player2 = fixture
            st.write(f"- **{player1}** vs **{player2}**")
    else:
        st.write("No remaining fixtures for this match type.")

def display_series_table_completedonly(series_id):
    player_stats = get_player_stats_by_series_completedonly(series_id)
    if player_stats:
        st.subheader("Latest Series Standings:")
        formatted_stats = []
        for stat in player_stats:
            name_with_nickname = f"{stat[1]} ({stat[2]})"
            wins = int(stat[3] or 0)  # Ensure it's an integer
            losses = int(stat[4] or 0)  # Ensure it's an integer
            played = wins + losses
            win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
            avg_pr = f"{stat[6]:.2f}" if stat[6] is not None else "-"
            avg_luck = f"{stat[7]:.2f}" if stat[7] is not None else "-"
            formatted_stats.append([name_with_nickname, played, wins, losses, win_percentage, avg_pr, avg_luck])  
        
        # Create a DataFrame
        df = pd.DataFrame(
            formatted_stats, 
            columns=["Name (Nickname)", "Played", "Wins", "Losses", "Win%", "Average PR", "Average Luck"]
        )
        
        # Set the index to None to remove the index column
        df = df.reset_index(drop=True)
        
        # Display DataFrame without the index column
        st.dataframe(df)  # Streamlit

    else:
        st.subheader("No series matches scheduled yet.")
    
def display_series_table(series_id):
    player_stats = get_player_stats_by_series(series_id)  
    if player_stats:
        st.subheader("Latest Series Standings:")
        formatted_stats = []
        for stat in player_stats:
            name_with_nickname = f"{stat[1]} ({stat[2]})"
            wins = int(stat[3] or 0)  # Ensure it's an integer
            losses = int(stat[4] or 0)  # Ensure it's an integer
            played = wins + losses
            win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
            avg_pr = f"{stat[6]:.2f}" if stat[6] is not None else "-"
            avg_luck = f"{stat[7]:.2f}" if stat[7] is not None else "-"
            formatted_stats.append([name_with_nickname, played, wins, losses, win_percentage, avg_pr, avg_luck])  
        
        # Create a DataFrame
        df = pd.DataFrame(
            formatted_stats, 
            columns=["Name (Nickname)", "Played", "Wins", "Losses", "Win%", "Averaged PR", "Average Luck"]
        )
        
        # Set the index to None to remove the index column
        df = df.reset_index(drop=True)
        
        # Display DataFrame without the index column
        st.dataframe(df)  # Streamlit

    else:
        st.subheader("No series matches scheduled yet.")
        
def display_group_table(match_type_id):
    player_stats = get_player_stats_with_fixtures(match_type_id)  
    if player_stats:
        st.subheader("Latest standings:")
        formatted_stats = []
        for stat in player_stats:
            name_with_nickname = f"{stat[1]} ({stat[2]})"
            wins = int(stat[3] or 0)  # Ensure it's an integer
            losses = int(stat[4] or 0)  # Ensure it's an integer
            played = wins + losses
            win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
            avg_pr = f"{stat[6]:.2f}" if stat[6] is not None else "-"
            avg_luck = f"{stat[7]:.2f}" if stat[7] is not None else "-"
            formatted_stats.append([name_with_nickname, played, wins, losses, win_percentage, avg_pr, avg_luck])  
        
        # Create a DataFrame
        df = pd.DataFrame(
            formatted_stats, 
            columns=["Name (Nickname)", "Played", "Wins", "Losses", "Win%", "Averaged PR", "Average Luck"]
        )
        
        # Set the index to None to remove the index column
        df = df.reset_index(drop=True)
        
        # Display DataFrame without the index column
        st.dataframe(df)  # Streamlit
        #st.markdown(df.style.hide(axis="index").to_html(), unsafe_allow_html=True)

    else:
        st.subheader("No matches scheduled yet.")

def show_matches_completed(match_type_id):
    # Connect to the database
    conn = create_connection()
    cursor = conn.cursor()

    # Query to fetch completed matches for the given MatchTypeID
    query = """
    SELECT 
        MatchResults.Date AS MatchDate,
        p1.Name AS WinnerName, 
        p1.Nickname AS WinnerNickname, 
        p2.Name AS LoserName, 
        p2.Nickname AS LoserNickname, 
        MatchResults.Player1Points AS Player1Points,
        MatchResults.Player2Points AS Player2Points,
        MatchResults.Player1PR AS Player1PR, 
        MatchResults.Player1Luck AS Player1Luck, 
        MatchResults.Player2PR AS Player2PR, 
        MatchResults.Player2Luck AS Player2Luck
    FROM MatchResults
    JOIN Fixtures ON MatchResults.FixtureID = Fixtures.FixtureID
    JOIN Players p1 ON MatchResults.Player1ID = p1.PlayerID
    JOIN Players p2 ON MatchResults.Player2ID = p2.PlayerID
    WHERE Fixtures.MatchTypeID = %s AND Fixtures.Completed = 1
    ORDER BY MatchResults.Date DESC;
    """
    
    cursor.execute(query, (match_type_id,))
    results = cursor.fetchall()

    conn.close()

    # If no matches found
    if not results:
        st.warning("No completed matches found for this match type.")
        return

    # Prepare data for display
    data = []
    for row in results:
        match_date = row[0].strftime("%Y-%m-%d")
        
        # Extract values from the row
        player1_points, player2_points = row[5], row[6]
        player1_pr, player2_pr = row[7], row[9]
        player1_luck, player2_luck = row[8], row[10]
        
        # Determine winner and loser based on points
        if player1_points > player2_points:
            winner_info = f"{row[1]} ({row[2]})"
            loser_info = f"{row[3]} ({row[4]})"
            score = f"{player1_points}-{player2_points}"
            winner_pr, winner_luck = player1_pr, player1_luck
            loser_pr, loser_luck = player2_pr, player2_luck
        else:
            winner_info = f"{row[3]} ({row[4]})"
            loser_info = f"{row[1]} ({row[2]})"
            score = f"{player2_points}-{player1_points}"
            winner_pr, winner_luck = player2_pr, player2_luck
            loser_pr, loser_luck = player1_pr, player1_luck
    
        # Append to the data list
        data.append(
            [
                match_date,
                f"{winner_info} beat {loser_info}",
                score,
                f"{winner_pr:.2f}",  # Winner PR rounded to 2 decimals
                f"{winner_luck:.2f}",  # Winner Luck rounded to 2 decimals
                f"{loser_pr:.2f}",  # Loser PR rounded to 2 decimals
                f"{loser_luck:.2f}",  # Loser Luck rounded to 2 decimals
            ]
        )

    # Display results in a table
    st.subheader(f"Completed Matches:")
    st.table(
        {
            "Date Completed": [row[0] for row in data],
            "Result": [row[1] for row in data],
            "Score": [row[2] for row in data],
            "Winner PR": [row[3] for row in data],
            "Winner Luck": [row[4] for row in data],
            "Loser PR": [row[5] for row in data],
            "Loser Luck": [row[6] for row in data],
        }
    )

def get_match_results_for_grid(match_type_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # SQL query to fetch match results for a specific match type
        query = """
        SELECT
            p1.PlayerID AS Player1ID,
            p1.Name AS Player1Name,
            p2.PlayerID AS Player2ID,
            p2.Name AS Player2Name,
            mr.Player1Points AS Player1Points,
            mr.Player2Points AS Player2Points
        FROM Fixtures f
        JOIN Players p1 ON f.Player1ID = p1.PlayerID
        JOIN Players p2 ON f.Player2ID = p2.PlayerID
        LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
        WHERE f.MatchTypeID = %s
        ORDER BY p1.Name, p2.Name;
        """
        cursor.execute(query, (match_type_id,))
        match_results = cursor.fetchall()
        conn.close()

        return match_results
    except Exception as e:
        st.error(f"Error retrieving match results: {e}")
        return []

def get_player_stats_with_fixtures(match_type_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT
    p.PlayerID,
    p.Name,
    p.Nickname,
    SUM(CASE 
            WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
            WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1
            ELSE 0 
        END) AS Wins,
    SUM(CASE 
            WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points < mr.Player2Points THEN 1
            WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points < mr.Player1Points THEN 1
            ELSE 0 
        END) AS Losses,
    COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
    AVG(CASE 
            WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
            WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR
            ELSE NULL 
        END) AS AveragePR,
    AVG(CASE 
            WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
            WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck
            ELSE NULL 
        END) AS AverageLuck
FROM
    Players p
LEFT JOIN Fixtures f 
    ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
LEFT JOIN MatchResults mr 
    ON (f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID)
WHERE
    f.MatchTypeID = %s
GROUP BY
    p.PlayerID, p.Name, p.Nickname
ORDER BY
    CASE 
        WHEN AVG(CASE 
                    WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
                    WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR
                    ELSE NULL 
                END) IS NULL THEN 1
        ELSE 0 
    END ASC,
    AVG(CASE 
            WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
            WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR
            ELSE NULL 
        END) ASC;

        """
        cursor.execute(query, (match_type_id,))
        player_stats = cursor.fetchall()
        conn.close()

        return player_stats
    except Exception as e:
        st.error(f"Error retrieving player stats: {e}")
        return []

def get_player_id_by_nickname(nickname):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT PlayerID FROM Players WHERE Nickname = %s", (nickname,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        else:
            st.warning(f"No PlayerID found for nickname '{nickname}'")
            return None
    except Exception as e:
        st.error(f"Error retrieving PlayerID for nickname '{nickname}': {e}")
        return None

def reset_fixtures_completed():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Fixtures SET Completed = 0")  # Reset all 'Completed' columns to 0
        conn.commit()
        conn.close()
        st.success("All 'Completed' columns in Fixtures table have been reset to 0.")
    except Exception as e:
        st.error(f"Error resetting 'Completed' columns in Fixtures table: {e}")
        
def reset_match_results():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM MatchResults")  # Delete all records in MatchResults
        conn.commit()
        conn.close()
        st.success("MatchResults table has been reset to empty.")
    except Exception as e:
        st.error(f"Error resetting MatchResults table: {e}")

def empty_all_tables():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM MatchResults")  # Delete all records in MatchResults
        cursor.execute("DELETE FROM Fixtures")  # Delete all records in MatchResults
        cursor.execute("DELETE FROM Players")  # Delete all records in MatchResults
        cursor.execute("DELETE FROM MatchType")  # Delete all records in MatchResults
        cursor.execute("DELETE FROM Series")  # Delete all records in MatchResults
        cursor.execute("DELETE FROM SeriesMatchTypes")  # Delete all records in MatchResults
        conn.commit()
        conn.close()
        st.success("All tables have been reset to empty.")
    except Exception as e:
        st.error(f"Error resetting tables: {e}")

def get_fixture(match_type_id, player1_id, player2_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT FixtureID, Completed
            FROM Fixtures
            WHERE MatchTypeID = %s AND 
                  ((Player1ID = %s AND Player2ID = %s) OR 
                   (Player1ID = %s AND Player2ID = %s))
        ''', (match_type_id, player1_id, player2_id, player2_id, player1_id))
        fixture = cursor.fetchone()
        conn.close()
        
        if fixture:
            fixture_id, completed = fixture
            return {"FixtureID": fixture_id, "Completed": completed}
        else:
            st.warning("No matching fixture found.")
            return None
    except Exception as e:
        st.error(f"Error retrieving fixture: {e}")
        return None

def get_match_type_id_by_identifier(identifier):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MatchTypeID FROM MatchType WHERE Identifier = %s", (identifier,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        else:
            st.warning(f"No MatchTypeID found for identifier '{identifier}'")
            return None
    except Exception as e:
        st.error(f"Error retrieving MatchTypeID for identifier '{identifier}': {e}")
        return None

def get_nickname_to_full_name_map():
    """
    Returns a dictionary mapping player nicknames to their full names.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Nickname, FullName FROM Players")
        name_map = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return name_map
    except Exception as e:
        st.error(f"Error retrieving player names: {e}")
        return {}

def print_table_structure():
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Fetch table structure for MySQL
        cursor.execute("DESCRIBE MatchResults")
        columns = cursor.fetchall()

        # Display column details in Streamlit
        st.write("Structure of MatchResults table:")
        for column in columns:
            st.write(column)

    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        conn.close()

# Function to check if a result already exists in the MatchResults table
def check_result_exists(player_1_points, player_1_length, player_2_points, player_2_length):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Query to check for existing results
        query = """
            SELECT COUNT(*) FROM MatchResults
            WHERE Player1Points = %s AND Player1MatchLength = %s
            AND Player2Points = %s AND Player2MatchLength = %s
        """
        cursor.execute(query, (player_1_points, player_1_length, player_2_points, player_2_length))
        count = cursor.fetchone()[0]

        conn.close()
        return count > 0  # Returns True if a result already exists
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return False

# Function to insert a new match result into the MatchResults table
def insert_match_result(fixture_id, player1_points, player1_pr, player1_luck,
                        player2_points, player2_pr, player2_luck, match_type_id,
                        player1_id, player2_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Get the current date and time for insertion
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')  # Format date as 'YYYY-MM-DD'
        current_time = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%H:%M")
        
        # Insert match result
        cursor.execute('''
            INSERT INTO MatchResults (Date, TimeCompleted, MatchTypeID, Player1ID, Player2ID,
                                      Player1Points, Player2Points, Player1PR, Player2PR, 
                                      Player1Luck, Player2Luck, FixtureID)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (current_date,
              current_time,
              match_type_id,
              player1_id,
              player2_id,
              player1_points,  # Player1Points
              player2_points,  # Player2Points
              player1_pr,
              player2_pr,
              player1_luck,
              player2_luck,
              fixture_id))

        # Mark fixture as completed
        cursor.execute("UPDATE Fixtures SET Completed = 1 WHERE FixtureID = %s", (fixture_id,))

        conn.commit()
        conn.close()
        st.success("Match result successfully added and fixture marked as completed.")
    except Exception as e:
        st.error(f"Error inserting match result or updating fixture: {e}")
        
# Generating Fixtures in table from MatchTypeID and PlayerIDs
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
                INSERT INTO Fixtures (MatchTypeID, Player1ID, Player2ID, Completed)
                VALUES (%s, %s, %s, %s)
                """,
                (match_type_id, player1_id, player2_id, 0),  # Set Completed to 0 by default
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

def remove_match_type_from_series(series_id, match_type_id):
    """
    Removes the specified match type from the series in the database.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Remove the match type from the series
        cursor.execute("""
            DELETE FROM SeriesMatchTypes 
            WHERE SeriesID = %s AND MatchTypeID = %s
        """, (series_id, match_type_id))
        
        conn.commit()
        conn.close()
        st.success(f"Match Type ID {match_type_id} removed from Series ID {series_id} successfully.")
    except Exception as e:
        st.error(f"Error removing match type from series: {e}")

def add_match_type_to_series(series_id, match_type_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO SeriesMatchTypes (SeriesID, MatchTypeID)
        VALUES (%s, %s)
    ''', (series_id, match_type_id))
    conn.commit()
    conn.close()

def update_player(player_id, name, nickname, email):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE Players
        SET Name = %s, Nickname = %s, Email = %s
        WHERE PlayerID = %s
    ''', (name, nickname, email, player_id))
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
            Completed TINYINT DEFAULT 0,
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

# Fetch data from Crontest2
def get_crontest2():
    try:
        conn = create_connection()
        query = "SELECT CronID, DateTimeCompleted FROM Crontest2"
        data = pd.read_sql(query, conn)
        
        conn.close()
        return data
    except mysql.connector.Error as e:
        st.write(f"Database connection error: {e}")
        return pd.DataFrame()  # Return an empty DataFrame if there's an error
        
# Add table for Crontest
def crontest2_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Crontest2 (
            CronID INT AUTO_INCREMENT PRIMARY KEY,
            DateTimeCompleted DATETIME
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
def add_match_type(match_type_title, match_type_identifier, active):
    conn = create_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO MatchType (MatchTypeTitle, Identifier, Active)
        VALUES (%s, %s, %s)
    ''', (match_type_title, match_type_identifier, active))
    
    conn.commit()
    cursor.close()
    conn.close()

# Insert a new match result with a check for duplicates
def add_match_result(player1_id, player2_id, player1_points, player2_points, match_type_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Check if a match result with the same players and match type exists (in either order)
        cursor.execute('''
            SELECT MatchResultID FROM MatchResults
            WHERE MatchTypeID = %s AND 
                  ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
        ''', (match_type_id, player1_id, player2_id, player2_id, player1_id))
        
        existing_result = cursor.fetchone()
        
        if existing_result:
            st.warning("This match result already exists with these players and match type.")
        else:
            # Insert the new match result if no duplicate is found
            cursor.execute('''
                INSERT INTO MatchResults 
                (Date, Player1ID, Player2ID, Player1Points, Player2Points, MatchTypeID) 
                VALUES (NOW(), %s, %s, %s, %s, %s)
            ''', (player1_id, player2_id, player1_points, player2_points, match_type_id))
            conn.commit()
            st.success("Match result added successfully!")
        
        conn.close()
    except Exception as e:
        st.error(f"Error adding match result: {e}")

def add_fixture(match_type_id, player1_id, player2_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Check for existing fixture with same match type and players in either order
        cursor.execute(
            '''
            SELECT FixtureID FROM Fixtures
            WHERE MatchTypeID = %s AND 
                  ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
            ''',
            (match_type_id, player1_id, player2_id, player2_id, player1_id)
        )
        
        existing_fixture = cursor.fetchone()
        
        if existing_fixture:
            st.warning("This fixture already exists with these players and match type.")
        else:
            # Insert fixture with Completed set to 0 by default
            cursor.execute(
                "INSERT INTO Fixtures (MatchTypeID, Player1ID, Player2ID, Completed) VALUES (%s, %s, %s, %s)",
                (match_type_id, player1_id, player2_id, 0)  # Set Completed to 0 by default
            )
            conn.commit()
            st.success("Fixture added successfully!")
        
        conn.close()
    except Exception as e:
        st.error(f"Error adding fixture: {e}")

def get_match_results_nicely_formatted():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # SQL query with JOINs to replace IDs with names
        query = """
            SELECT 
                mr.MatchResultID, 
                mr.Date, 
                mr.TimeCompleted, 
                mt.MatchTypeTitle, 
                p1.Name AS Player1Name, 
                p2.Name AS Player2Name, 
                mr.Player1Points, 
                mr.Player2Points, 
                mr.Player1PR, 
                mr.Player2PR, 
                mr.Player1Luck, 
                mr.Player2Luck
            FROM 
                MatchResults mr
            JOIN 
                MatchType mt ON mr.MatchTypeID = mt.MatchTypeID
            JOIN 
                Players p1 ON mr.Player1ID = p1.PlayerID
            JOIN 
                Players p2 ON mr.Player2ID = p2.PlayerID
        """
        
        cursor.execute(query)
        match_results = cursor.fetchall()
        conn.close()

        if not match_results:
            st.error("No match results found.")

        # Format results
        formatted_results = []
        for mr in match_results:
            match_result = list(mr)
            time_completed = match_result[2]  # Assuming 'TimeCompleted' is the third column
            
            # Format TimeCompleted as HH:MM:SS
            if isinstance(time_completed, datetime.timedelta):
                total_seconds = time_completed.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                seconds = int(total_seconds % 60)
                time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
                match_result[2] = time_str  # Update TimeCompleted

            formatted_results.append(tuple(match_result))

        return formatted_results  # Return formatted results as a list of tuples
    except Exception as e:
        st.error(f"Error retrieving match results: {e}")
        return []

def get_fixtures_with_names_by_match_type(match_type):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Use JOINs to get player names and match type title
        cursor.execute('''
            SELECT  
                m.MatchTypeTitle,
                p1.Name AS Player1Name, 
                p2.Name AS Player2Name,
                f.Completed
            FROM Fixtures f
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            JOIN MatchType m ON f.MatchTypeID = m.MatchTypeID
            WHERE m.MatchTypeTitle = %s
        ''', (match_type,))  # Use a parameterized query here
        
        fixtures = cursor.fetchall()
        conn.close()

        if not fixtures:
            st.error("No fixtures found.")
        
        return fixtures
    except Exception as e:
        st.error(f"Error retrieving fixtures with names by match type: {e}")
        return []
        
def get_fixtures_with_names():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Use JOINs to get player names and match type title
        cursor.execute('''
            SELECT 
                f.FixtureID, 
                m.MatchTypeTitle,
                p1.Name AS Player1Name, 
                p2.Name AS Player2Name,
                f.Completed
            FROM Fixtures f
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            JOIN MatchType m ON f.MatchTypeID = m.MatchTypeID
        ''')
        
        fixtures = cursor.fetchall()
        conn.close()

        if not fixtures:
            st.error("No fixtures found.")
        
        return fixtures
    except Exception as e:
        st.error(f"Error retrieving fixtures with names: {e}")
        return []

def get_fixtures():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT FixtureID, MatchTypeID, Player1ID, Player2ID, Completed
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

def get_players_by_match_type(match_type_title):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = '''
        SELECT 
            p.Name,
            p.Nickname,
            p.TotalWins,
            p.TotalLosses,
            p.WinPercentage,
            p.AveragePR,
            p.AverageLuck
        FROM 
            Players p
        JOIN 
            MatchResults mr ON p.PlayerID IN (mr.Player1ID, mr.Player2ID)
        JOIN
            MatchType mt ON mr.MatchTypeID = mt.MatchTypeID
        WHERE 
            mt.MatchTypeTitle = %s
        ORDER BY 
            p.AveragePR ASC;
        '''
        cursor.execute(query, (match_type_title,))
        players = cursor.fetchall()
        conn.close()

        return players
    except Exception as e:
        st.error(f"Error retrieving players by match type: {e}")
        return []

def get_players_full():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        # Include the Email column in the query
        cursor.execute("""
            SELECT 
                PlayerID, Name, Nickname, Email, GamesPlayed, AveragePR, CurrentLeague, DaysIdle 
            FROM 
                Players
            ORDER BY 
                Name ASC
        """)
        players = cursor.fetchall()
        conn.close()

        if not players:
            st.error("No players found.")
        
        # Adjust the tuple structure to include Email
        return [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]) for p in players]
    except Exception as e:
        st.error(f"Error retrieving players: {e}")
        return []

    
# Function to retrieve all players' ID, Name, Nickname
def get_players_simple():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT PlayerID, Name, Nickname FROM Players ORDER by Name ASC")
        players = cursor.fetchall()
        conn.close()

        if not players:
            st.error("No players found.")
        
        return [(p[0], p[1], p[2]) for p in players]  # Ensure tuples with (ID, Name, Nickname)
    except Exception as e:
        st.error(f"Error retrieving players: {e}")
        return []

def get_player_stats_by_series_completedonly(series_id):
    try:
        # Step 1: Fetch match types associated with the series
        match_types = get_series_match_types(series_id)
        if not match_types:
            return []  # No match types found for the series

        # Step 2: Extract match type IDs from the result
        match_type_ids = [mt[0] for mt in match_types]

        # Step 3: Prepare the query to fetch player stats
        conn = create_connection()
        cursor = conn.cursor()
        query = f'''
            SELECT
                p.PlayerID,
                p.Name,
                p.Nickname,
                COUNT(CASE WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
                           WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1 END) AS Wins,
                COUNT(CASE WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points < mr.Player2Points THEN 1
                           WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points < mr.Player1Points THEN 1 END) AS Losses,
                COUNT(mr.MatchResultID) AS GamesPlayed,
                AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
                         WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) AS AveragePR,
                AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
                         WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck END) AS AverageLuck
            FROM
                Players p
            LEFT JOIN MatchResults mr ON (mr.Player1ID = p.PlayerID OR mr.Player2ID = p.PlayerID)
            GROUP BY
                p.PlayerID, p.Name, p.Nickname
            ORDER BY
                CASE WHEN AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
                                   WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) IS NULL THEN 1 ELSE 0 END,
                AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
                         WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) ASC;
        '''
        
        # Step 4: Execute the query with match type IDs
        cursor.execute(query, tuple(match_type_ids))
        results = cursor.fetchall()

        # Close the connection
        conn.close()

        return results

    except Exception as e:
        st.error(f"Error fetching player stats by series: {e}")
        return []

def get_player_stats_by_series(series_id):
    try:
        # Step 1: Fetch match types associated with the series
        match_types = get_series_match_types(series_id)
        if not match_types:
            return []  # No match types found for the series

        # Step 2: Extract match type IDs from the result
        match_type_ids = [mt[0] for mt in match_types]

        # Step 3: Prepare the query to fetch player stats
        conn = create_connection()
        cursor = conn.cursor()
        query = f'''
            SELECT
    p.PlayerID,
    p.Name,
    p.Nickname,
    COUNT(CASE WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
               WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1 END) AS Wins,
    COUNT(CASE WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points < mr.Player2Points THEN 1
               WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points < mr.Player1Points THEN 1 END) AS Losses,
    COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
    AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
             WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) AS AveragePR,
    AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
             WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck END) AS AverageLuck
FROM
    Players p
LEFT JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
LEFT JOIN MatchResults mr ON (mr.MatchTypeID = f.MatchTypeID AND 
                               (mr.Player1ID = p.PlayerID OR mr.Player2ID = p.PlayerID))
WHERE
    f.MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))})
GROUP BY
    p.PlayerID, p.Name, p.Nickname
ORDER BY
    CASE WHEN AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
                       WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) IS NULL THEN 1 ELSE 0 END,
    AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
             WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) ASC;
        '''
        
        # Step 4: Execute the query with match type IDs
        cursor.execute(query, tuple(match_type_ids))
        results = cursor.fetchall()

        # Close the connection
        conn.close()

        return results

    except Exception as e:
        st.error(f"Error fetching player stats by series: {e}")
        return []

def get_player_stats_by_matchtype(match_type_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        query = '''
            SELECT
    p.PlayerID,
    p.Name,
    p.Nickname,
    COUNT(CASE WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
               WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1 END) AS Wins,
    COUNT(CASE WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points < mr.Player2Points THEN 1
               WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points < mr.Player1Points THEN 1 END) AS Losses,
    COUNT(mr.MatchResultID) AS GamesPlayed,
    AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
             WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) AS AveragePR,
    AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
             WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck END) AS AverageLuck
FROM
    Players p
LEFT JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
LEFT JOIN MatchResults mr ON (mr.MatchTypeID = f.MatchTypeID AND 
                               (mr.Player1ID = p.PlayerID OR mr.Player2ID = p.PlayerID))
WHERE
    f.MatchTypeID = %s
GROUP BY
    p.PlayerID, p.Name, p.Nickname
ORDER BY
    CASE WHEN AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
                       WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) IS NULL THEN 1 ELSE 0 END,
    AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
             WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) ASC;
        '''
        cursor.execute(query, (match_type_id,))
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        st.error(f"Error fetching player stats: {e}")
        return []

# Function to retrieve all match types
def get_match_types():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MatchTypeID, MatchTypeTitle, Identifier, Active FROM MatchType")
        match_types = cursor.fetchall()
        conn.close()

        if not match_types:
            st.error("No match types found.")
        
        return [(mt[0], mt[1], mt[2], mt[3]) for mt in match_types]  # Ensure tuples with (ID, Title, Identifier, Active)
    except Exception as e:
        st.error(f"Error retrieving match types: {e}")
        return []

def update_fixture(fixture_id, match_type_id, player1_id, player2_id, completed):
    """
    Update fixture details in the database.

    Args:
        fixture_id (int): ID of the fixture to update.
        match_type_id (int): New match type ID.
        player1_id (int): New Player 1 ID.
        player2_id (int): New Player 2 ID.
        completed (bool): Completion status of the fixture.
    """
    try:
        conn = create_connection()  # Establish database connection
        cursor = conn.cursor()
        
        # Update the fixture details
        cursor.execute('''
            UPDATE Fixtures 
            SET MatchTypeID = %s, Player1ID = %s, Player2ID = %s, Completed = %s 
            WHERE FixtureID = %s
        ''', (match_type_id, player1_id, player2_id, int(completed), fixture_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        st.error(f"Error updating fixture: {e}")

def update_match_type_status(match_type_id, active, identifier):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE MatchType 
            SET Active = %s, Identifier = %s 
            WHERE MatchTypeID = %s
        ''', (active, identifier, match_type_id))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error updating match type: {e}")

# Function to retrieve all matches with specific fields as tuples
def get_match_results():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                MatchResultID, 
                Date, 
                TimeCompleted, 
                MatchTypeID, 
                Player1ID, 
                Player2ID, 
                Player1Points, 
                Player2Points, 
                Player1PR, 
                Player2PR, 
                Player1Luck, 
                Player2Luck
            FROM 
                MatchResults
        """)
        match_results = cursor.fetchall()
        conn.close()
        
        return match_results if match_results else []  # Ensures an empty list is returned if no results
    except Exception as e:
        st.error(f"Error retrieving match results: {e}")
        return []  # Return an empty list in case of error


# Retrieving Sorting Standings
def get_sorting_standings():
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Name, GamesPlayed, TotalWins, WinPercentage, AveragePR
            FROM Players
            ORDER BY AveragePR DESC;
        ''')
        sortingstandings = cursor.fetchall()
        conn.close()

        if not sortingstandings:
            st.error("Sorting standings is empty or not found.")
        
        return sortingstandings
    except Exception as e:
        st.error(f"Error retrieving sorting standings: {e}")
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
