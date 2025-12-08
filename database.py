import mysql.connector
import email
import imaplib
import sys
import streamlit as st
import datetime
import plotly.express as px
import pandas as pd
from decimal import Decimal
from datetime import datetime

def log_debug(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("sabga_debug_log.txt", "a") as f:
        f.write(f"[{timestamp}] {message}\n")

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

def safe_float(value):
    """Convert Decimal or string to float safely and format to 2 decimal places."""
    try:
        if isinstance(value, Decimal):  # Convert Decimal to float
            value = float(value)
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return "-"

def get_player_pr_for_season(season_id):
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            WITH PlayerPR AS (
                -- Player1 rows
                SELECT 
                    mr.MatchResultID,
                    mr.MatchTypeID,
                    smt.SeriesID,
                    s.SeriesTitle,
                    ss.SeasonID,
                    mr.Player1ID AS PlayerID,
                    mr.Player1PR AS PlayerPR
                FROM MatchResults mr
                JOIN SeriesMatchTypes smt ON smt.MatchTypeID = mr.MatchTypeID
                JOIN SeasonSeries ss ON ss.SeriesID = smt.SeriesID
                JOIN Series s ON s.SeriesID = smt.SeriesID
                WHERE mr.Player1PR IS NOT NULL

                UNION ALL

                -- Player2 rows
                SELECT 
                    mr.MatchResultID,
                    mr.MatchTypeID,
                    smt.SeriesID,
                    s.SeriesTitle,
                    ss.SeasonID,
                    mr.Player2ID AS PlayerID,
                    mr.Player2PR AS PlayerPR
                FROM MatchResults mr
                JOIN SeriesMatchTypes smt ON smt.MatchTypeID = mr.MatchTypeID
                JOIN SeasonSeries ss ON ss.SeriesID = smt.SeriesID
                JOIN Series s ON s.SeriesID = smt.SeriesID
                WHERE mr.Player2PR IS NOT NULL
            )

            SELECT
                p.PlayerID,
                p.Name AS PlayerName,
                pp.SeriesID,
                pp.SeriesTitle,
                pp.PlayerPR,
                pp.SeasonID
            FROM PlayerPR pp
            JOIN Players p ON p.PlayerID = pp.PlayerID
            WHERE pp.SeasonID = %s
            ORDER BY p.Name, pp.SeriesID;
        """, (season_id,))

        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=[
            "PlayerID", "PlayerName", 
            "SeriesID", "SeriesTitle", 
            "PlayerPR", "SeasonID"
        ])
        return df

    except Exception as e:
        print("Error fetching Player PR for Season:", e)
        return pd.DataFrame()

    finally:
        cursor.close()
        conn.close()

def get_average_pr_by_league_and_series():
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 
                sm.SeriesID,
                s.SeriesTitle,
                mt.MatchTypeTitle,
                ROUND(AVG(
                    CASE 
                        WHEN mr.Player1PR IS NOT NULL AND mr.Player2PR IS NOT NULL 
                        THEN (mr.Player1PR + mr.Player2PR) / 2 
                        ELSE NULL 
                    END
                ), 2) AS AveragePR
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID AND mr.MatchTypeID = f.MatchTypeID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            JOIN SeriesMatchTypes sm ON sm.MatchTypeID = f.MatchTypeID
            JOIN Series s ON sm.SeriesID = s.SeriesID
            WHERE mr.Player1PR IS NOT NULL AND mr.Player2PR IS NOT NULL
            GROUP BY sm.SeriesID, s.SeriesTitle, mt.MatchTypeTitle
            ORDER BY mt.MatchTypeTitle, sm.SeriesID
        """)
        rows = cursor.fetchall()
        # returned rows are tuples: (SeriesID, SeriesTitle, MatchTypeTitle, AveragePR)
        df = pd.DataFrame(rows, columns=["SeriesID", "SeriesTitle", "MatchTypeTitle", "AveragePR"])
        # Ensure AveragePR is numeric and rounded (defensive)
        if not df.empty:
            df["AveragePR"] = pd.to_numeric(df["AveragePR"], errors="coerce").round(2)
        return df

    except Exception as e:
        print("Error fetching average PRs by league and series:", e)
        return pd.DataFrame(columns=["SeriesID", "SeriesTitle", "MatchTypeTitle", "AveragePR"])

    finally:
        cursor.close()
        conn.close()

def get_average_pr_by_league_and_seriess():
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 
                sm.SeriesID,
                s.SeriesName,
                mt.MatchTypeTitle,
                ROUND(AVG(CASE 
                    WHEN mr.Player1PR IS NOT NULL AND mr.Player2PR IS NOT NULL 
                    THEN (mr.Player1PR + mr.Player2PR) / 2 
                    ELSE NULL END), 2) AS AveragePR
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID AND mr.MatchTypeID = f.MatchTypeID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            JOIN SeriesMatchTypes sm ON sm.MatchTypeID = f.MatchTypeID
            JOIN Series s ON sm.SeriesID = s.SeriesID
            WHERE mr.Player1PR IS NOT NULL AND mr.Player2PR IS NOT NULL
            GROUP BY sm.SeriesID, f.MatchTypeID
            ORDER BY mt.MatchTypeTitle, sm.SeriesID
        """)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=["SeriesID", "SeriesName", "MatchTypeTitle", "AveragePR"])
        return df

    except Exception as e:
        print("Error fetching average PRs by league and series:", e)
        return pd.DataFrame()

    finally:
        cursor.close()
        conn.close()

def get_annual_pr_and_luck_leaders(min_matches=5):
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Player of the Year - lowest average PR
        cursor.execute("""
            SELECT PlayerName, COUNT(*) as Matches, AVG(
                CASE 
                    WHEN Player1ID = p.PlayerID THEN Player1PR 
                    WHEN Player2ID = p.PlayerID THEN Player2PR 
                END
            ) as AvgPR
            FROM CompletedMatchesCache c
            JOIN Players p ON p.PlayerID IN (c.Player1ID, c.Player2ID)
            WHERE (p.PlayerID = c.Player1ID OR p.PlayerID = c.Player2ID)
            GROUP BY PlayerName
            HAVING Matches >= %s
            ORDER BY AvgPR ASC
            LIMIT 10
        """, (min_matches,))
        pr_leaders = pd.DataFrame(cursor.fetchall(), columns=["Player", "Matches", "Avg PR"])

        # Unluckiest Player - lowest average Luck
        cursor.execute("""
            SELECT PlayerName, COUNT(*) as Matches, AVG(
                CASE 
                    WHEN Player1ID = p.PlayerID THEN Player1Luck 
                    WHEN Player2ID = p.PlayerID THEN Player2Luck 
                END
            ) as AvgLuck
            FROM CompletedMatchesCache c
            JOIN Players p ON p.PlayerID IN (c.Player1ID, c.Player2ID)
            WHERE (p.PlayerID = c.Player1ID OR p.PlayerID = c.Player2ID)
            GROUP BY PlayerName
            HAVING Matches >= %s
            ORDER BY AvgLuck ASC
            LIMIT 10
        """, (min_matches,))
        luck_leaders = pd.DataFrame(cursor.fetchall(), columns=["Player", "Matches", "Avg Luck"])

        # League Champion - best A-League PR (matchtype_ids to define!)
        A_LEAGUE_IDS = [19, 30, 39]  # Update based on actual MatchTypeIDs for A-League
        format_ids = ','.join(str(mid) for mid in A_LEAGUE_IDS)
        cursor.execute(f"""
            SELECT PlayerName, COUNT(*) as Matches, AVG(
                CASE 
                    WHEN Player1ID = p.PlayerID THEN Player1PR 
                    WHEN Player2ID = p.PlayerID THEN Player2PR 
                END
            ) as AvgPR
            FROM CompletedMatchesCache c
            JOIN Players p ON p.PlayerID IN (c.Player1ID, c.Player2ID)
            WHERE MatchTypeID IN ({format_ids})
              AND (p.PlayerID = c.Player1ID OR p.PlayerID = c.Player2ID)
            GROUP BY PlayerName
            HAVING Matches >= %s
            ORDER BY AvgPR ASC
            LIMIT 10
        """, (min_matches,))
        aleague_champion = pd.DataFrame(cursor.fetchall(), columns=["Player", "Matches", "Avg PR"])

        return pr_leaders, luck_leaders, aleague_champion

    except Exception as e:
        st.error(f"❌ Error loading award leaders: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    finally:
        cursor.close()
        conn.close()

def show_trophies_awards_page():
    import streamlit as st

    st.title("🏆 SABGA Trophies & Awards")

    st.markdown("""
    Welcome to the **SABGA Round Robin Leagues Hall of Fame**.  
    This section celebrates outstanding achievements, prize winners, and the spirit of backgammon excellence in South Africa.

    ---
    ## 💰 Cash Prizes

    **Cash prizes are awarded for each Series to the winners and, from Series 2, also to the runner-ups in a 60/40 split** across the top four leagues (A–D) as follows:

    | League | Series 1 | Series 2 | Series 3 | Series 4 |
    |--------|----------|----------|----------|----------|
    | **A-League** | R2100 to Winner | R1260 / R840 | R1260 / R840 | R1260 / R840 |
    | **B-League** | R1600 to Winner | R960 / R640 | R960 / R640 | R960 / R640 |
    | **C-League** | R1100 to Winner | R660 / R440 | R660 / R440 | R660 / R440 |
    | **D-League** | R600 to Winner | R360 / R240 | R360 / R240 | R360 / R240 |

    ---
    ## 🏅 Annual Trophies & Awards

    These trophies are awarded **annually**, at the conclusion of the fourth Series:

    - 🥇 **Player of the Year**  
      Awarded to the player with the **lowest average PR** over all League matches for the year.

    - 👑 **League Champion**  
      Awarded to the **A-League player** with the best combined PR across **all four Series**.

    - 📈 **Most Improved Player**  
      Selected by the League Director, recognising the greatest improvement over the calendar year.

    - 🍀 **Unluckiest Player**  
      Awarded to the most statistically unlucky player (lowest average luck score) with significant participation.

    - 💖 **Justin Goldman Memorial Trophy**  
      Voted for by club members, in honour of Justin Goldman (1985–2016), recognising the player who best exemplifies:
      - Integrity
      - Honour
      - Politeness
      - Respect

    - 🏆 **SABGA League Knockout Cup**  
      A knockout cup competition held in the **second half of every year**, open to all SABGA League players.

    ---
    ## 📜 Past Winners

    🕒 *No historical data yet. Past winners will be added here from the conclusion of the 2025 season.*

    """, unsafe_allow_html=True)

def show_season_statistics_page(season_choice):
    season_year = season_choice
    st.write(f"Season {season_year} data under construction")

    st.subheader("Average PR by League Across Series")
    pr_trend_df = get_average_pr_by_league_and_series()

    # Debug columns & sample — safe to leave in for a short while
    st.write("PR trend columns:", pr_trend_df.columns.tolist())
    st.write(pr_trend_df.head())

    # Map of which series (by SeriesID) belong to which season year
    relevant_series_ids = {
        "2025": [5, 6, 7],   # Series 1, 2, 3
        "2024": [4]          # Sorting League
    }
    selected_ids = relevant_series_ids.get(str(season_year), [])

    if not selected_ids:
        st.warning(f"No Series found for Season {season_year}")
        return

    df = pr_trend_df.copy()

    # Normalize possible series-name column names to 'SeriesName'
    if "SeriesName" not in df.columns:
        if "SeriesTitle" in df.columns:
            df = df.rename(columns={"SeriesTitle": "SeriesName"})
            st.info("Renamed 'SeriesTitle' -> 'SeriesName' for pivoting.")
        else:
            # try to auto-detect a series-like column
            candidates = [c for c in df.columns if "series" in c.lower() and "name" in c.lower() or "title" in c.lower()]
            if candidates:
                df = df.rename(columns={candidates[0]: "SeriesName"})
                st.info(f"Using '{candidates[0]}' as SeriesName for pivot.")
            else:
                st.error("No SeriesName/SeriesTitle column found in PR data. Cannot build pivot.")
                return

    # Ensure other required columns exist
    for col in ("MatchTypeTitle", "AveragePR", "SeriesID"):
        if col not in df.columns:
            st.error(f"PR data missing required column '{col}'. Found columns: {df.columns.tolist()}")
            return

    # Filter for the chosen series ids
    filtered = df[df["SeriesID"].isin(selected_ids)]
    if filtered.empty:
        st.warning(f"No PR data for Season {season_year} (series {selected_ids}).")
        return

    # Pivot (index = MatchTypeTitle, columns = SeriesName, values = AveragePR)
    try:
        pivot_df = filtered.pivot(index="MatchTypeTitle", columns="SeriesName", values="AveragePR")
        pivot_df = pivot_df.sort_index()
    except Exception as e:
        st.error(f"Error pivoting PR data: {e}")
        st.write("Filtered data sample:", filtered.head())
        return

    st.dataframe(pivot_df, width="stretch")

def show_series_statistics_page(series_choice):
    series_map = {
        "2025 - Series 4": 8,
        "2025 - Series 3": 7,
        "2025 - Series 2": 6,
        "2025 - Series 1": 5,
        "2024 - Sorting League": 4
    }
    series_id = series_map.get(series_choice)

    if series_id is None:
        st.error("Invalid series selected.")
        return

    st.subheader(f"📊 Series Statistics for {series_choice}")
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # 1️⃣ Top 10 by Points%
        cursor.execute("""
            SELECT p.Name, sps.GamesPlayed, sps.Points,
                   ROUND((sps.Points / (sps.GamesPlayed * 3)) * 100, 2) AS PointsPercent
            FROM SeriesPlayerStats sps
            JOIN Players p ON sps.PlayerID = p.PlayerID
            WHERE sps.SeriesID = %s AND sps.GamesPlayed > 0
            ORDER BY PointsPercent DESC, sps.GamesPlayed DESC
            LIMIT 10
        """, (series_id,))
        df_points_pct = pd.DataFrame(cursor.fetchall(), columns=["Player", "Played", "Points", "Points%"])
        df_points_pct.insert(0, "Rank", range(1, len(df_points_pct) + 1))
        df_points_pct["Points%"] = df_points_pct["Points%"].map(lambda x: f"{x:.1f}%")
        st.markdown(f"### 🥇 Top 10 Players by Points% - {series_choice}")
        st.dataframe(df_points_pct, hide_index=True)

        # 2️⃣ Top 10 Avg PR
        cursor.execute("""
            SELECT p.Name, mt.MatchTypeTitle, COUNT(mr.MatchResultID) AS Games, ROUND(AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR
                                          WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR ELSE NULL END), 2) AS AvgPR
            FROM MatchResults mr
            JOIN MatchType mt ON mr.MatchTypeID = mt.MatchTypeID
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN Players p ON (p.PlayerID = f.Player1ID OR p.PlayerID = f.Player2ID)
            WHERE f.MatchTypeID IN (
                SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s
            )
            GROUP BY p.PlayerID
            HAVING COUNT(*) >= 2
            ORDER BY AvgPR ASC
            LIMIT 10;
        """, (series_id,))
        df_pr = pd.DataFrame(cursor.fetchall(), columns=["Player", "League", "Played", "Average PR"])
        df_pr.insert(0,"Rank", range(1, len(df_pr)+1))
        
        st.markdown(f"### 🧠 Top 10 Players by Average PR - {series_choice}")
        st.dataframe(df_pr, hide_index=True)

        # 3️⃣ Top 10 individual PRs (best single-game performance)
        cursor.execute("""
            SELECT p.Name, mt.MatchTypeTitle, mr.Date,
                   CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR ELSE mr.Player2PR END AS PR
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN Players p ON (p.PlayerID = mr.Player1ID OR p.PlayerID = mr.Player2ID)
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            WHERE f.MatchTypeID IN (
                SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s
            )
            ORDER BY PR ASC
            LIMIT 10
        """, (series_id,))
        df_top_pr = pd.DataFrame(cursor.fetchall(), columns=["Player", "League", "Date", "PR"])
        df_top_pr.insert(0,"Rank", range(1, len(df_top_pr)+1))
        st.markdown(f"### 🏅 Top 10 Match Performances - {series_choice}")
        st.dataframe(df_top_pr, hide_index=True)

        # 4️⃣ Luckiest players
        cursor.execute("""
            SELECT p.Name, mt.MatchTypeTitle, count(mr.MatchResultID) as Played, ROUND(AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                                          WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END), 2) AS AvgLuck
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN Players p ON (p.PlayerID = f.Player1ID OR p.PlayerID = f.Player2ID)
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            WHERE f.MatchTypeID IN (
                SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s
            )
            GROUP BY p.PlayerID
            HAVING COUNT(*) >= 2
            ORDER BY AvgLuck DESC
            LIMIT 10
        """, (series_id,))
        df_luckiest = pd.DataFrame(cursor.fetchall(), columns=["Player", "League","Played", "Average Luck"])
        df_luckiest.insert(0,"Rank", range(1, len(df_luckiest)+1))
        st.markdown(f"### 🍀 Top 10 Luckiest Players - {series_choice}")
        st.dataframe(df_luckiest, hide_index=True)

        # 5️⃣ Unluckiest players
        cursor.execute("""
            SELECT p.Name, mt.MatchTypeTitle, count(mr.MatchResultID) as Played, ROUND(AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                                          WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END), 2) AS AvgLuck
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN Players p ON (p.PlayerID = f.Player1ID OR p.PlayerID = f.Player2ID)
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            WHERE f.MatchTypeID IN (
                SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s
            )
            GROUP BY p.PlayerID
            HAVING COUNT(*) >= 2
            ORDER BY AvgLuck ASC
            LIMIT 10
        """, (series_id,))
        df_unluckiest = pd.DataFrame(cursor.fetchall(), columns=["Player", "League","Played", "Average Luck"])
        df_unluckiest.insert(0,"Rank", range(1, len(df_unluckiest)+1))
        
        st.markdown(f"### 😵 Top 10 Unluckiest Players - {series_choice}")
        st.dataframe(df_unluckiest, hide_index=True)

        # 6️⃣ Visual: Average PR per MatchType (Group)
        cursor.execute("""
            SELECT mt.MatchTypeTitle,
                   ROUND(AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                                  WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END), 2) AS AvgPR
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN Players p ON (p.PlayerID = mr.Player1ID OR p.PlayerID = mr.Player2ID)
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            WHERE f.MatchTypeID IN (
                SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s
            )
            GROUP BY mt.MatchTypeTitle
            ORDER BY AvgPR ASC
        """, (series_id,))
        df_pr_by_league = pd.DataFrame(cursor.fetchall(), columns=["League", "Average PR"])
        st.markdown("### 📉 Average PR by League (Match Type)")
        fig = px.bar(df_pr_by_league, x="League", y="Average PR", color="Average PR", color_continuous_scale="blues")
        st.plotly_chart(fig, width='stretch')

    except Exception as e:
        st.error(f"Error loading league statistics: {e}")
    finally:
        cursor.close()
        conn.close()
        
def show_player_summary_tab():
    """
    Displays Player Statistics - Summary Page:
    - Form (last 5)
    - This Year
    - Career
    - Completed Matches (clean display)
    - Per MatchType summary
    - PR Over Time plot
    """
    st.header("👤 Player Statistics - Summary Page")

    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Player selector
        cursor.execute("SELECT PlayerID, Name, Nickname FROM Players ORDER BY Name")
        players = cursor.fetchall()
        player_options = {f"{name} ({nickname})": pid for pid, name, nickname in players}
        selected_player = st.selectbox("Select a player:", list(player_options.keys()))
        player_id = player_options[selected_player]

        # 1️⃣ Current Form (Last 5)
        cursor.execute("""
            SELECT
                CASE WHEN Player1ID = %s THEN Player1PR ELSE Player2PR END,
                CASE WHEN Player1ID = %s THEN Player1Luck ELSE Player2Luck END,
                CASE WHEN (Player1ID = %s AND Player1Points > Player2Points) OR
                          (Player2ID = %s AND Player2Points > Player1Points) THEN 1 ELSE 0 END
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
            ORDER BY Date DESC, MatchResultID DESC
            LIMIT 5
        """, (player_id, player_id, player_id, player_id, player_id, player_id))
        last5 = cursor.fetchall()
        pr_last5 = [float(row[0]) for row in last5 if isinstance(row[0], (int, float))]
        luck_last5 = [float(row[1]) for row in last5 if isinstance(row[1], (int, float))]
        wins_last5 = sum(row[2] for row in last5)

        avg_pr_last5 = f"{(sum(pr_last5) / len(pr_last5)):.2f}" if pr_last5 else "-"
        avg_luck_last5 = f"{(sum(luck_last5) / len(luck_last5)):.2f}" if luck_last5 else "-"

        with st.container():
            st.markdown("### ⚡ Current Form (Last 5 Matches)")
            col1, col2, col3 = st.columns(3)
            col1.metric("Average PR (last 5)", avg_pr_last5)
            col2.metric("Average Luck (last 5)", avg_luck_last5)
            col3.metric("Wins in last 5", f"{wins_last5}/5")

        # 2️⃣ This Year Summary
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN (Player1ID = %s AND Player1Points > Player2Points) OR
                                 (Player2ID = %s AND Player2Points > Player1Points) THEN 1 ELSE 0 END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1PR WHEN Player2ID = %s THEN Player2PR END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1Luck WHEN Player2ID = %s THEN Player2Luck END)
            FROM MatchResults
            WHERE (Player1ID = %s OR Player2ID = %s) AND YEAR(Date) = YEAR(CURDATE())
        """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id))
        year_matches, year_wins, year_avg_pr, year_avg_luck = cursor.fetchone()
        year_matches = int(year_matches or 0)
        year_wins = int(year_wins or 0)
        year_avg_pr_str = f"{float(year_avg_pr):.2f}" if year_avg_pr is not None else "-"
        year_avg_luck_str = f"{float(year_avg_luck):.2f}" if year_avg_luck is not None else "-"
        year_win_pct = f"{(year_wins / year_matches * 100):.2f}%" if year_matches else "0.00%"

        with st.container():
            st.markdown("### 🗓️ This Year")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Matches", year_matches)
            col2.metric("Wins", year_wins)
            col3.metric("Win %", year_win_pct)
            col4.metric("Avg PR", year_avg_pr_str)

        # 3️⃣ Career Summary
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN (Player1ID = %s AND Player1Points > Player2Points) OR
                                 (Player2ID = %s AND Player2Points > Player1Points) THEN 1 ELSE 0 END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1PR WHEN Player2ID = %s THEN Player2PR END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1Luck WHEN Player2ID = %s THEN Player2Luck END)
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
        """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id))
        career_matches, career_wins, career_avg_pr, career_avg_luck = cursor.fetchone()
        career_matches = int(career_matches or 0)
        career_wins = int(career_wins or 0)
        career_avg_pr_str = f"{float(career_avg_pr):.2f}" if career_avg_pr is not None else "-"
        career_avg_luck_str = f"{float(career_avg_luck):.2f}" if career_avg_luck is not None else "-"
        career_win_pct = f"{(career_wins / career_matches * 100):.2f}%" if career_matches else "0.00%"

        with st.container():
            st.markdown("### 🏆 Career")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Matches", career_matches)
            col2.metric("Wins", career_wins)
            col3.metric("Win %", career_win_pct)
            col4.metric("Avg PR", career_avg_pr_str)

        # 5️⃣ Per MatchType Summary Table
        cursor.execute("""
            SELECT mt.MatchTypeTitle,
                   COUNT(mr.MatchResultID) AS Games,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) OR
                                (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points) THEN 1 ELSE 0 END) AS Wins,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1Points < mr.Player2Points) OR
                                (mr.Player2ID = %s AND mr.Player2Points < mr.Player1Points) THEN 1 ELSE 0 END) AS Losses,
                   ROUND(AVG(CASE WHEN mr.Player1ID = %s THEN mr.Player1PR WHEN mr.Player2ID = %s THEN mr.Player2PR END), 2) AS AvgPR,
                   ROUND(AVG(CASE WHEN mr.Player1ID = %s THEN mr.Player1Luck WHEN mr.Player2ID = %s THEN mr.Player2Luck END), 2) AS AvgLuck,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1PR < mr.Player2PR) OR
                                (mr.Player2ID = %s AND mr.Player2PR < mr.Player1PR) THEN 1 ELSE 0 END) AS PRWins
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            WHERE mr.Player1ID = %s OR mr.Player2ID = %s
            GROUP BY mt.MatchTypeTitle
            ORDER BY Games DESC
        """, (player_id,) * 12)
        per_mt = cursor.fetchall()
        if per_mt:
            per_mt_df = pd.DataFrame(per_mt, columns=[
                "MatchType", "Games", "Wins", "Losses", "Avg PR", "Avg Luck", "PR Wins"
            ])
            per_mt_df["Win %"] = per_mt_df.apply(
                lambda row: f"{(row['Wins'] / row['Games'] * 100):.2f}%" if row["Games"] > 0 else "0.00%",
                axis=1
            )
            per_mt_df["PR Win %"] = per_mt_df.apply(
                lambda row: f"{(row['PR Wins'] / row['Games'] * 100):.2f}%" if row["Games"] > 0 else "0.00%",
                axis=1
            )
            st.subheader("🏅 Performance by Match Type")
            st.dataframe(per_mt_df, hide_index=True)
            
        # 6️⃣ PR Over Time with Rolling Avg
        cursor.execute("""
            SELECT Date, MatchResultID,
                   CASE WHEN Player1ID = %s THEN Player1PR ELSE Player2PR END
            FROM MatchResults
            WHERE (Player1ID = %s OR Player2ID = %s) AND Date IS NOT NULL
            ORDER BY Date ASC, MatchResultID ASC
        """, (player_id, player_id, player_id))
        pr_data = cursor.fetchall()
        if pr_data:
            pr_df = pd.DataFrame([
                {"Date": pd.to_datetime(row[0]), "MatchResultID": row[1], "PR": float(row[2])}
                for row in pr_data if row[0] is not None and isinstance(row[2], (int, float, float))
            ])
            if not pr_df.empty:
                pr_df["RollingAvgPR"] = pr_df["PR"].rolling(window=5, min_periods=1).mean()
                fig = px.scatter(
                    pr_df,
                    x="Date",
                    y="PR",
                    title="PR Over Time (with Rolling Avg)",
                    hover_data={"Date": True, "PR": ":.2f", "MatchResultID": True}
                )
                fig.add_traces(px.line(pr_df, x="Date", y="RollingAvgPR").data)
                fig.update_traces(marker=dict(size=8, opacity=0.6))
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("No PR data available for plotting.")
        else:
            st.info("No PR data available for plotting.")


        # 4️⃣ Completed Matches Table
        params = (player_id,) * 9   # <- corrected to 9, because the query has 9 %s placeholders
        assert len(params) == 9, f"Expected 9 params, got {len(params)}: {params}"
        cursor.execute("""
            SELECT
                mr.Date,
                mt.MatchTypeTitle,
                CASE WHEN (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) OR
                          (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points) THEN 'Won' ELSE 'Lost' END AS Result,
                CASE WHEN mr.Player1ID = %s THEN p2.Name ELSE p1.Name END AS Opponent,
                CONCAT(
                    '11-',
                    CASE WHEN (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) THEN mr.Player2Points
                         WHEN (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points) THEN mr.Player1Points
                         ELSE LEAST(mr.Player1Points, mr.Player2Points) END
                ) AS Score,
                ROUND(CASE WHEN mr.Player1ID = %s THEN mr.Player1PR ELSE mr.Player2PR END, 2) AS PR,
                ROUND(CASE WHEN mr.Player1ID = %s THEN mr.Player1Luck ELSE mr.Player2Luck END, 2) AS Luck
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            JOIN Players p1 ON mr.Player1ID = p1.PlayerID
            JOIN Players p2 ON mr.Player2ID = p2.PlayerID
            WHERE mr.Player1ID = %s OR mr.Player2ID = %s
            ORDER BY mr.Date DESC
            LIMIT 50
        """, params)

        matches = cursor.fetchall()
        if matches:
            matches_df = pd.DataFrame(matches, columns=[
                "Date", "Match Type", "Result", "Opponent", "Score", "PR", "Luck"
            ])
            # Ensure correct dtypes
            matches_df["Date"] = pd.to_datetime(matches_df["Date"])
            matches_df["PR"] = pd.to_numeric(matches_df["PR"], errors="coerce").round(2)
            matches_df["Luck"] = pd.to_numeric(matches_df["Luck"], errors="coerce").round(2)
        
            st.subheader("📜 Recent Completed Matches")
            st.dataframe(matches_df, hide_index=True)
        else:
            st.info("No completed matches found for this player.")

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Error loading player stats: {e}")

def show_player_summary_tab6():
    """
    Displays Player Statistics - Summary Page:
    - Form (last 5)
    - This Year
    - Career
    - Completed Matches (clean display)
    - Per MatchType summary
    - PR Over Time plot
    """
    import pandas as pd
    import plotly.express as px

    st.header("👤 Player Statistics - Summary Page")

    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Player selector
        cursor.execute("SELECT PlayerID, Name, Nickname FROM Players ORDER BY Name")
        players = cursor.fetchall()
        player_options = {f"{name} ({nickname})": pid for pid, name, nickname in players}
        selected_player = st.selectbox("Select a player:", list(player_options.keys()))
        player_id = player_options[selected_player]

        # 1️⃣ Current Form (Last 5)
        cursor.execute("""
            SELECT
                CASE WHEN Player1ID = %s THEN Player1PR ELSE Player2PR END,
                CASE WHEN Player1ID = %s THEN Player1Luck ELSE Player2Luck END,
                CASE WHEN (Player1ID = %s AND Player1Points > Player2Points) OR
                          (Player2ID = %s AND Player2Points > Player1Points) THEN 1 ELSE 0 END
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
            ORDER BY Date DESC, MatchResultID DESC
            LIMIT 5
        """, (player_id, player_id, player_id, player_id, player_id, player_id))
        last5 = cursor.fetchall()
        pr_last5 = [float(row[0]) for row in last5 if isinstance(row[0], (int, float))]
        luck_last5 = [float(row[1]) for row in last5 if isinstance(row[1], (int, float))]
        wins_last5 = sum(row[2] for row in last5)

        avg_pr_last5 = f"{(sum(pr_last5) / len(pr_last5)):.2f}" if pr_last5 else "-"
        avg_luck_last5 = f"{(sum(luck_last5) / len(luck_last5)):.2f}" if luck_last5 else "-"

        with st.container():
            st.markdown("### ⚡ Current Form (Last 5 Matches)")
            col1, col2, col3 = st.columns(3)
            col1.metric("Average PR (last 5)", avg_pr_last5)
            col2.metric("Average Luck (last 5)", avg_luck_last5)
            col3.metric("Wins in last 5", f"{wins_last5}/5")

        # 2️⃣ This Year Summary
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN (Player1ID = %s AND Player1Points > Player2Points) OR
                                 (Player2ID = %s AND Player2Points > Player1Points) THEN 1 ELSE 0 END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1PR WHEN Player2ID = %s THEN Player2PR END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1Luck WHEN Player2ID = %s THEN Player2Luck END)
            FROM MatchResults
            WHERE (Player1ID = %s OR Player2ID = %s) AND YEAR(Date) = YEAR(CURDATE())
        """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id))
        year_matches, year_wins, year_avg_pr, year_avg_luck = cursor.fetchone()
        year_matches = int(year_matches or 0)
        year_wins = int(year_wins or 0)
        year_avg_pr_str = f"{float(year_avg_pr):.2f}" if year_avg_pr is not None else "-"
        year_avg_luck_str = f"{float(year_avg_luck):.2f}" if year_avg_luck is not None else "-"
        year_win_pct = f"{(year_wins / year_matches * 100):.2f}%" if year_matches else "0.00%"

        with st.container():
            st.markdown("### 🗓️ This Year")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Matches", year_matches)
            col2.metric("Wins", year_wins)
            col3.metric("Win %", year_win_pct)
            col4.metric("Avg PR", year_avg_pr_str)

        # 3️⃣ Career Summary
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN (Player1ID = %s AND Player1Points > Player2Points) OR
                                 (Player2ID = %s AND Player2Points > Player1Points) THEN 1 ELSE 0 END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1PR WHEN Player2ID = %s THEN Player2PR END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1Luck WHEN Player2ID = %s THEN Player2Luck END)
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
        """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id))
        career_matches, career_wins, career_avg_pr, career_avg_luck = cursor.fetchone()
        career_matches = int(career_matches or 0)
        career_wins = int(career_wins or 0)
        career_avg_pr_str = f"{float(career_avg_pr):.2f}" if career_avg_pr is not None else "-"
        career_avg_luck_str = f"{float(career_avg_luck):.2f}" if career_avg_luck is not None else "-"
        career_win_pct = f"{(career_wins / career_matches * 100):.2f}%" if career_matches else "0.00%"

        with st.container():
            st.markdown("### 🏆 Career")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Matches", career_matches)
            col2.metric("Wins", career_wins)
            col3.metric("Win %", career_win_pct)
            col4.metric("Avg PR", career_avg_pr_str)

        # 4️⃣ Completed Matches Table
        cursor.execute("""
            SELECT
                mr.Date,
                mt.MatchTypeTitle,
                CASE WHEN (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) OR
                          (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points) THEN 'Won' ELSE 'Lost' END AS Result,
                CASE WHEN mr.Player1ID = %s THEN p2.Name ELSE p1.Name END AS Opponent,
                CONCAT(
                    '11-',
                    CASE WHEN (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) THEN mr.Player2Points
                         WHEN (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points) THEN mr.Player1Points
                         ELSE LEAST(mr.Player1Points, mr.Player2Points) END
                ) AS Score,
                ROUND(CASE WHEN mr.Player1ID = %s THEN mr.Player1PR ELSE mr.Player2PR END, 2) AS PR,
                ROUND(CASE WHEN mr.Player1ID = %s THEN mr.Player1Luck ELSE mr.Player2Luck END, 2) AS Luck
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            JOIN Players p1 ON mr.Player1ID = p1.PlayerID
            JOIN Players p2 ON mr.Player2ID = p2.PlayerID
            WHERE mr.Player1ID = %s OR mr.Player2ID = %s
            ORDER BY mr.Date DESC
            LIMIT 50
        """, (player_id,) * 10)
        matches = cursor.fetchall()
        if matches:
            matches_df = pd.DataFrame(matches, columns=[
                "Date", "Match Type", "Result", "Opponent", "Score", "PR", "Luck"
            ])
            st.subheader("📜 Recent Completed Matches")
            st.dataframe(matches_df, hide_index=True)

        # 5️⃣ Per MatchType Summary Table
        cursor.execute("""
            SELECT mt.MatchTypeTitle,
                   COUNT(mr.MatchResultID) AS Games,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) OR
                                (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points) THEN 1 ELSE 0 END) AS Wins,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1Points < mr.Player2Points) OR
                                (mr.Player2ID = %s AND mr.Player2Points < mr.Player1Points) THEN 1 ELSE 0 END) AS Losses,
                   ROUND(AVG(CASE WHEN mr.Player1ID = %s THEN mr.Player1PR WHEN mr.Player2ID = %s THEN mr.Player2PR END), 2) AS AvgPR,
                   ROUND(AVG(CASE WHEN mr.Player1ID = %s THEN mr.Player1Luck WHEN mr.Player2ID = %s THEN mr.Player2Luck END), 2) AS AvgLuck,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1PR < mr.Player2PR) OR
                                (mr.Player2ID = %s AND mr.Player2PR < mr.Player1PR) THEN 1 ELSE 0 END) AS PRWins
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            WHERE mr.Player1ID = %s OR mr.Player2ID = %s
            GROUP BY mt.MatchTypeTitle
            ORDER BY Games DESC
        """, (player_id,) * 12)
        per_mt = cursor.fetchall()
        if per_mt:
            per_mt_df = pd.DataFrame(per_mt, columns=[
                "MatchType", "Games", "Wins", "Losses", "Avg PR", "Avg Luck", "PR Wins"
            ])
            per_mt_df["Win %"] = per_mt_df.apply(
                lambda row: f"{(row['Wins'] / row['Games'] * 100):.2f}%" if row["Games"] > 0 else "0.00%",
                axis=1
            )
            per_mt_df["PR Win %"] = per_mt_df.apply(
                lambda row: f"{(row['PR Wins'] / row['Games'] * 100):.2f}%" if row["Games"] > 0 else "0.00%",
                axis=1
            )
            st.subheader("🏅 Performance by Match Type")
            st.dataframe(per_mt_df, hide_index=True)

        # 6️⃣ PR Over Time with Rolling Avg
        cursor.execute("""
            SELECT Date, MatchResultID,
                   CASE WHEN Player1ID = %s THEN Player1PR ELSE Player2PR END
            FROM MatchResults
            WHERE (Player1ID = %s OR Player2ID = %s) AND Date IS NOT NULL
            ORDER BY Date ASC, MatchResultID ASC
        """, (player_id, player_id, player_id))
        pr_data = cursor.fetchall()
        if pr_data:
            pr_df = pd.DataFrame([
                {"Date": pd.to_datetime(row[0]), "MatchResultID": row[1], "PR": float(row[2])}
                for row in pr_data if row[0] is not None and isinstance(row[2], (int, float, float))
            ])
            if not pr_df.empty:
                pr_df["RollingAvgPR"] = pr_df["PR"].rolling(window=5, min_periods=1).mean()
                fig = px.scatter(
                    pr_df,
                    x="Date",
                    y="PR",
                    title="PR Over Time (with Rolling Avg)",
                    hover_data={"Date": True, "PR": ":.2f", "MatchResultID": True}
                )
                fig.add_traces(px.line(pr_df, x="Date", y="RollingAvgPR").data)
                fig.update_traces(marker=dict(size=8, opacity=0.6))
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("No PR data available for plotting.")
        else:
            st.info("No PR data available for plotting.")

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Error loading player stats: {e}")

def show_player_summary_tab5():

    st.header("👤 Player Statistics - Summary Page")

    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Fetch players for selection
        cursor.execute("SELECT PlayerID, Name, Nickname FROM Players ORDER BY Name")
        players = cursor.fetchall()
        player_options = {f"{name} ({nickname})": pid for pid, name, nickname in players}

        selected_player = st.selectbox("Select a player:", list(player_options.keys()), key="player_summary_select")
        player_id = player_options[selected_player]

        # 1️⃣ Player Ranking by Average PR
        cursor.execute("""
            SELECT p.PlayerID, AVG(CASE WHEN mr.Player1ID = p.PlayerID THEN mr.Player1PR WHEN mr.Player2ID = p.PlayerID THEN mr.Player2PR END) as AvgPR
            FROM Players p
            JOIN MatchResults mr ON p.PlayerID = mr.Player1ID OR p.PlayerID = mr.Player2ID
            GROUP BY p.PlayerID
            HAVING AvgPR IS NOT NULL
            ORDER BY AvgPR ASC
        """)
        rankings = cursor.fetchall()
        ranking_list = [(pid, avgpr) for pid, avgpr in rankings]
        total_players = len(ranking_list)
        player_rank = next((i + 1 for i, (pid, _) in enumerate(ranking_list) if pid == player_id), None)

        # 2️⃣ Current Form (Last 5 Matches)
        cursor.execute("""
            SELECT Date, Player1ID, Player2ID, Player1Points, Player2Points, Player1PR, Player2PR, Player1Luck, Player2Luck, MatchTypeID
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
            ORDER BY Date DESC, MatchResultID DESC
            LIMIT 5
        """, (player_id, player_id))
        last5 = cursor.fetchall()
        wins_last5 = 0
        pr_list = []
        luck_list = []
        mini_table = []

        for row in last5:
            date, p1_id, p2_id, p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck, mt_id = row
            opponent_id = p2_id if p1_id == player_id else p1_id
            cursor.execute("SELECT Name FROM Players WHERE PlayerID = %s", (opponent_id,))
            opponent_name = cursor.fetchone()[0]
            result = "Win" if (p1_id == player_id and p1_pts > p2_pts) or (p2_id == player_id and p2_pts > p1_pts) else "Loss"
            if result == "Win":
                wins_last5 += 1
            pr = p1_pr if p1_id == player_id else p2_pr
            luck = p1_luck if p1_id == player_id else p2_luck
            pr_list.append(pr)
            luck_list.append(luck)
            cursor.execute("SELECT MatchTypeTitle FROM MatchType WHERE MatchTypeID = %s", (mt_id,))
            mt_title = cursor.fetchone()[0] if cursor.rowcount else "-"
            mini_table.append([date, mt_title, opponent_name, result, pr, luck])

        avg_pr_last5 = round(sum(pr_list) / len(pr_list), 2) if pr_list else "-"
        avg_luck_last5 = round(sum(luck_list) / len(luck_list), 2) if luck_list else "-"

        st.subheader(f"🏆 Player Rank: #{player_rank} out of {total_players}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Average PR (last 5)", avg_pr_last5)
        col2.metric("Average Luck (last 5)", avg_luck_last5)
        col3.metric("Wins in last 5", f"{wins_last5}/5")

        mini_df = pd.DataFrame(mini_table, columns=["Date", "MatchType", "Opponent", "Result", "PR", "Luck"])
        st.subheader("🎲🎲 Last 5 Matches")
        st.dataframe(mini_df, hide_index=True)

        # 3️⃣ Enhanced Completed Matches Table
        cursor.execute("""
            SELECT mr.Date, mt.MatchTypeTitle,
                   CASE WHEN mr.Player1ID = %s THEN p2.Name ELSE p1.Name END as Opponent,
                   CASE WHEN (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) OR (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points)
                        THEN 'Win' ELSE 'Loss' END as Result,
                   CONCAT(mr.Player1Points, '-', mr.Player2Points) as Score,
                   CASE WHEN mr.Player1ID = %s THEN mr.Player1PR ELSE mr.Player2PR END as PR,
                   CASE WHEN mr.Player1ID = %s THEN mr.Player1Luck ELSE mr.Player2Luck END as Luck
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            JOIN Players p1 ON mr.Player1ID = p1.PlayerID
            JOIN Players p2 ON mr.Player2ID = p2.PlayerID
            WHERE mr.Player1ID = %s OR mr.Player2ID = %s
            ORDER BY mr.Date DESC
        """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id))
        matches = cursor.fetchall()
        match_df = pd.DataFrame(matches, columns=["Date", "MatchType", "Opponent", "Result", "Score", "PR", "Luck"])
        st.subheader("📄 Completed Matches")
        st.dataframe(match_df, hide_index=True)

        # 4️⃣ Per MatchType Summary Table
        cursor.execute("""
            SELECT mt.MatchTypeTitle,
                   COUNT(mr.MatchResultID) as Games,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) OR
                                (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points) THEN 1 ELSE 0 END) as Wins,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1Points < mr.Player2Points) OR
                                (mr.Player2ID = %s AND mr.Player2Points < mr.Player1Points) THEN 1 ELSE 0 END) as Losses,
                   AVG(CASE WHEN mr.Player1ID = %s THEN mr.Player1PR WHEN mr.Player2ID = %s THEN mr.Player2PR END) as AvgPR,
                   AVG(CASE WHEN mr.Player1ID = %s THEN mr.Player1Luck WHEN mr.Player2ID = %s THEN mr.Player2Luck END) as AvgLuck,
                   SUM(CASE WHEN (mr.Player1ID = %s AND mr.Player1PR < mr.Player2PR) OR
                                (mr.Player2ID = %s AND mr.Player2PR < mr.Player1PR) THEN 1 ELSE 0 END) as PRWins
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            WHERE mr.Player1ID = %s OR mr.Player2ID = %s
            GROUP BY mt.MatchTypeTitle
            ORDER BY Games DESC
        """, (
            player_id, player_id, player_id, player_id,
            player_id, player_id, player_id, player_id,
            player_id, player_id, player_id, player_id
        ))
        per_mt = cursor.fetchall()
        per_mt_df = pd.DataFrame(per_mt, columns=[
            "MatchType", "Games", "Wins", "Losses", "Avg PR", "Avg Luck", "PR Wins"
        ])
        
        # Ensure correct dtypes
        for col in ["Games", "Wins", "Losses", "PR Wins"]:
            per_mt_df[col] = pd.to_numeric(per_mt_df[col], errors="coerce").fillna(0).astype(int)
        
        for col in ["Avg PR", "Avg Luck"]:
            per_mt_df[col] = pd.to_numeric(per_mt_df[col], errors="coerce").fillna(0.0)
        
        # Compute Win % and PR Win %
        per_mt_df["Win %"] = round(
            (per_mt_df["Wins"] / per_mt_df["Games"].replace(0, pd.NA) * 100), 2
        ).fillna(0.0)
        
        per_mt_df["PR Win %"] = round(
            (per_mt_df["PR Wins"] / per_mt_df["Games"].replace(0, pd.NA) * 100), 2
        ).fillna(0.0)
        
        # Reorder columns for clarity
        per_mt_df = per_mt_df[
            ["MatchType", "Games", "Wins", "Losses", "Win %", "PR Wins", "PR Win %", "Avg PR", "Avg Luck"]
        ]
        
        # Display with clear % formatting
        st.subheader("🏅 Performance by Match Type")
        st.dataframe(
            per_mt_df.style.format({
                "Win %": "{:.2f}%",
                "PR Win %": "{:.2f}%",
                "Avg PR": "{:.2f}",
                "Avg Luck": "{:.2f}"
            }),
            hide_index=True
        )

        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Error loading player stats: {e}")

def show_player_summary_tab1():
    """
    Displays Player Summary tab with robust type handling for Plotly trendlines,
    smoothed rolling average PR, and hover tooltips.
    """
    import plotly.express as px
    import pandas as pd

    st.header("👤 Player Statistics - Summary Page")
    st.caption("Summary of a selected player's stats, performance, and series participation.")

    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Fetch players
        cursor.execute("SELECT PlayerID, Name, Nickname FROM Players ORDER BY Name")
        players = cursor.fetchall()
        player_options = {f"{name} ({nickname})": pid for pid, name, nickname in players}

        selected_player = st.selectbox("Select a player:", list(player_options.keys()), key="player_summary_select")
        player_id = player_options[selected_player]

        # Total matches, wins, losses
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN (Player1ID = %s AND Player1Points > Player2Points) OR
                                 (Player2ID = %s AND Player2Points > Player1Points) THEN 1 ELSE 0 END),
                   SUM(CASE WHEN (Player1ID = %s AND Player1Points < Player2Points) OR
                                 (Player2ID = %s AND Player2Points < Player1Points) THEN 1 ELSE 0 END)
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
        """, (player_id, player_id, player_id, player_id, player_id, player_id))
        total_matches, wins, losses = cursor.fetchone()
        total_matches = int(total_matches or 0)
        wins = int(wins or 0)
        losses = int(losses or 0)
        win_pct = (wins / total_matches) * 100 if total_matches else 0

        # PR Wins
        cursor.execute("""
            SELECT SUM(CASE WHEN (Player1ID = %s AND Player1PR < Player2PR) OR
                                  (Player2ID = %s AND Player2PR < Player1PR) THEN 1 ELSE 0 END)
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
        """, (player_id, player_id, player_id, player_id))
        pr_wins = int(cursor.fetchone()[0] or 0)
        pr_win_pct = (pr_wins / total_matches) * 100 if total_matches else 0

        # Avg PR and Luck
        cursor.execute("""
            SELECT AVG(CASE WHEN Player1ID = %s THEN Player1PR WHEN Player2ID = %s THEN Player2PR END),
                   AVG(CASE WHEN Player1ID = %s THEN Player1Luck WHEN Player2ID = %s THEN Player2Luck END)
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
        """, (player_id, player_id, player_id, player_id, player_id, player_id))
        avg_pr, avg_luck = cursor.fetchone()
        avg_pr = float(avg_pr) if avg_pr is not None else None
        avg_luck = float(avg_luck) if avg_luck is not None else None

        # Last 10 matches PR and Luck
        cursor.execute("""
            SELECT
                CASE WHEN Player1ID = %s THEN Player1PR ELSE Player2PR END,
                CASE WHEN Player1ID = %s THEN Player1Luck ELSE Player2Luck END
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
            ORDER BY Date DESC, MatchResultID DESC
            LIMIT 10
        """, (player_id, player_id, player_id, player_id))
        last_10 = cursor.fetchall()
        valid_pr = [float(row[0]) for row in last_10 if isinstance(row[0], (int, float))]
        valid_luck = [float(row[1]) for row in last_10 if isinstance(row[1], (int, float))]
        last_10_pr = round(sum(valid_pr) / len(valid_pr), 2) if valid_pr else None
        last_10_luck = round(sum(valid_luck) / len(valid_luck), 2) if valid_luck else None

        # Luckiest and Unluckiest game (unchanged for now)
        cursor.execute("""
            SELECT Date,
                   CASE WHEN Player1ID = %s THEN Player1Luck ELSE Player2Luck END,
                   CASE WHEN Player1ID = %s THEN Player1PR ELSE Player2PR END
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
            ORDER BY CASE WHEN Player1ID = %s THEN Player1Luck ELSE Player2Luck END DESC
            LIMIT 1
        """, (player_id, player_id, player_id, player_id, player_id))
        luckiest = cursor.fetchone()
        luckiest_str = "-"
        if luckiest:
            date_str = luckiest[0].strftime("%Y-%m-%d") if hasattr(luckiest[0], "strftime") else str(luckiest[0])
            luck_val = round(float(luckiest[1]), 2) if isinstance(luckiest[1], (int, float)) else "-"
            pr_val = round(float(luckiest[2]), 2) if isinstance(luckiest[2], (int, float)) else "-"
            luckiest_str = f"{date_str} | Luck: {luck_val} | PR: {pr_val}"

        cursor.execute("""
            SELECT Date,
                   CASE WHEN Player1ID = %s THEN Player1Luck ELSE Player2Luck END,
                   CASE WHEN Player1ID = %s THEN Player1PR ELSE Player2PR END
            FROM MatchResults
            WHERE Player1ID = %s OR Player2ID = %s
            ORDER BY CASE WHEN Player1ID = %s THEN Player1Luck ELSE Player2Luck END ASC
            LIMIT 1
        """, (player_id, player_id, player_id, player_id, player_id))
        unluckiest = cursor.fetchone()
        unluckiest_str = "-"
        if unluckiest:
            date_str = unluckiest[0].strftime("%Y-%m-%d") if hasattr(unluckiest[0], "strftime") else str(unluckiest[0])
            luck_val = round(float(unluckiest[1]), 2) if isinstance(unluckiest[1], (int, float)) else "-"
            pr_val = round(float(unluckiest[2]), 2) if isinstance(unluckiest[2], (int, float)) else "-"
            unluckiest_str = f"{date_str} | Luck: {luck_val} | PR: {pr_val}"

        # PR Over Time with smoothed rolling average and hover tooltips
        cursor.execute("""
            SELECT Date, MatchResultID,
                   CASE WHEN Player1ID = %s THEN Player1PR ELSE Player2PR END
            FROM MatchResults
            WHERE (Player1ID = %s OR Player2ID = %s) AND Date IS NOT NULL
            ORDER BY Date ASC, MatchResultID ASC
        """, (player_id, player_id, player_id))
        pr_data = cursor.fetchall()
        if pr_data:
            pr_df = pd.DataFrame([
                {"Date": pd.to_datetime(row[0]), "MatchResultID": row[1], "PR": float(row[2])}
                for row in pr_data if row[0] is not None and isinstance(row[2], (int, float))
            ])

            if not pr_df.empty:
                pr_df["RollingAvgPR"] = pr_df["PR"].rolling(window=5, min_periods=1).mean()

                fig = px.scatter(
                    pr_df,
                    x="Date",
                    y="PR",
                    title="PR Over Time with Rolling Average",
                    hover_data={"Date": True, "PR": ":.2f", "MatchResultID": True}
                )
                fig.add_traces(
                    px.line(
                        pr_df,
                        x="Date",
                        y="RollingAvgPR"
                    ).data
                )
                fig.update_traces(marker=dict(size=8, opacity=0.6))

                st.plotly_chart(fig, width='stretch')
            else:
                st.info("No PR data available for graph.")
        else:
            st.info("No PR data available for graph.")

        # Metrics Display
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Matches", total_matches)
        col2.metric("Wins", wins)
        col3.metric("Losses", losses)
        col4.metric("Win %", f"{win_pct:.2f}%")

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("PR Wins", pr_wins)
        col6.metric("PR Win %", f"{pr_win_pct:.2f}%")
        col7.metric("Avg PR", f"{avg_pr:.2f}" if avg_pr is not None else "-")
        col8.metric("Last 10 Avg PR", f"{last_10_pr:.2f}" if last_10_pr is not None else "-")

        col9, col10 = st.columns(2)
        col9.metric("Avg Luck", f"{avg_luck:.2f}" if avg_luck is not None else "-")
        col10.metric("Last 10 Avg Luck", f"{last_10_luck:.2f}" if last_10_luck is not None else "-")

        st.subheader("🎲 Luckiest and Unluckiest Games")
        st.write(f"**Luckiest:** {luckiest_str}")
        st.write(f"**Unluckiest:** {unluckiest_str}")

            # --- Add completed matches table ---
        st.subheader("📜 Completed Matches for Selected Player")

        cursor.execute("""
            SELECT 
                mr.Date,
                mr.MatchResultID,
                CASE WHEN mr.Player1ID = %s THEN p2.Name ELSE p1.Name END AS OpponentName,
                CASE WHEN mr.Player1ID = %s THEN p2.Nickname ELSE p1.Nickname END AS OpponentNickname,
                CASE WHEN mr.Player1ID = %s THEN mr.Player1Points ELSE mr.Player2Points END AS PlayerPoints,
                CASE WHEN mr.Player1ID = %s THEN mr.Player2Points ELSE mr.Player1Points END AS OpponentPoints,
                CASE WHEN mr.Player1ID = %s THEN mr.Player1PR ELSE mr.Player2PR END AS PlayerPR,
                CASE WHEN mr.Player1ID = %s THEN mr.Player1Luck ELSE mr.Player2Luck END AS PlayerLuck,
                CASE WHEN 
                    (mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points) OR 
                    (mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points) 
                    THEN 'Win' ELSE 'Loss' END AS Result
            FROM MatchResults mr
            JOIN Players p1 ON mr.Player1ID = p1.PlayerID
            JOIN Players p2 ON mr.Player2ID = p2.PlayerID
            WHERE mr.Player1ID = %s OR mr.Player2ID = %s
            ORDER BY mr.Date DESC, mr.MatchResultID DESC
        """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id))

        matches = cursor.fetchall()
        if matches:
            df = pd.DataFrame(matches, columns=[
                "Date", "MatchResultID", "Opponent", "OpponentNickname",
                "PlayerPoints", "OpponentPoints", "PlayerPR", "PlayerLuck", "Result"
            ])
            df["Date"] = pd.to_datetime(df["Date"])
            df["Opponent"] = df["Opponent"] + " (" + df["OpponentNickname"] + ")"
            df = df.drop(columns=["OpponentNickname"])
            df = df[
                ["Date", "MatchResultID", "Opponent", "PlayerPoints", "OpponentPoints", "PlayerPR", "PlayerLuck", "Result"]
            ]
            df = df.rename(columns={
                "Date": "📅 Date",
                "MatchResultID": "🆔 Match ID",
                "Opponent": "🆚 Opponent",
                "PlayerPoints": "🏓 Player Points",
                "OpponentPoints": "🏓 Opponent Points",
                "PlayerPR": "📈 Player PR",
                "PlayerLuck": "🍀 Player Luck",
                "Result": "✅ Result"
            })

            st.dataframe(
                df.style.format({
                    "📈 Player PR": "{:.2f}",
                    "🍀 Player Luck": "{:.2f}"
                }),
                width='stretch',
                hide_index=True
            )
        else:
            st.info("No matches found for this player yet.")
            
        cursor.close()
        conn.close()

    except Exception as e:
        st.error(f"Error loading player stats: {e}")

def update_remaining_fixtures_by_series(series_id):
    import datetime
    conn = create_connection()
    cursor = conn.cursor()
    try:
        print(f"[{datetime.datetime.now()}] Updating SeriesRemainingFixturesCache for SeriesID {series_id}...")

        cursor.execute("DELETE FROM SeriesRemainingFixturesCache WHERE SeriesID = %s", (series_id,))

        cursor.execute("SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s", (series_id,))
        matchtypes = cursor.fetchall()

        if not matchtypes:
            print(f"No match types found for SeriesID {series_id}.")
            return

        insert_query = """
            INSERT INTO SeriesRemainingFixturesCache (
                SeriesID, MatchTypeID, Player1Name, Player2Name, LastUpdated
            ) VALUES (%s, %s, %s, %s, NOW())
        """

        for (matchtype_id,) in matchtypes:
            cursor.execute("""
                SELECT p1.Name, p2.Name
                FROM Fixtures f
                JOIN Players p1 ON f.Player1ID = p1.PlayerID
                JOIN Players p2 ON f.Player2ID = p2.PlayerID
                WHERE f.MatchTypeID = %s AND f.Completed = 0
            """, (matchtype_id,))
            fixtures = cursor.fetchall()

            for row in fixtures:
                cursor.execute(insert_query, (series_id, matchtype_id, row[0], row[1]))

        conn.commit()
        print(f"✅ SeriesRemainingFixturesCache updated for SeriesID {series_id}.")

    except Exception as e:
        print(f"❌ Error in update_remaining_fixtures_by_series: {e}")
    finally:
        cursor.close()
        conn.close()

def show_cached_remaining_fixtures_by_series(series_id):
    """
    Display cached remaining fixtures for a given series using SeriesRemainingFixturesCache.
    Groups fixtures by MatchTypeTitle.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                srf.MatchTypeID,
                mt.MatchTypeTitle,
                srf.Player1Name,
                srf.Player2Name
            FROM SeriesRemainingFixturesCache srf
            JOIN MatchType mt ON srf.MatchTypeID = mt.MatchTypeID
            WHERE srf.SeriesID = %s
            ORDER BY mt.MatchTypeTitle, srf.Player1Name, srf.Player2Name
        """
        cursor.execute(query, (series_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            st.subheader("No remaining fixtures for this series.")
            return

        from collections import defaultdict
        
        grouped = defaultdict(list)
        for matchtype_id, matchtype_title, p1, p2 in rows:
            grouped[matchtype_title].append((p1, p2))
        
        # Calculate total remaining matches
        total_remaining = sum(len(matches) for matches in grouped.values())
        
        # Build formatted output string
        output_lines = []
        output_lines.append(f"*Remaining Fixtures (by Match Type) ({total_remaining}):*\n")
        
        for matchtype_title, matches in grouped.items():
            match_count = len(matches)
            output_lines.append(f"*{matchtype_title} ({match_count}):*")
            for p1, p2 in matches:
                output_lines.append(f"{p1} vs {p2}")
            output_lines.append("")  # Blank line between groups
        
        formatted_output = "\n".join(output_lines)
        
        # Display in text area
        st.text_area("Copy-paste-friendly fixtures:", formatted_output, height=400, key="fixtures_output")
        
        # Add a copy to clipboard button using streamlit-copy-paste pattern
        import streamlit.components.v1 as components
        
        copy_button_code = f"""
        <button onclick="navigator.clipboard.writeText(`{formatted_output}`); alert('Copied to clipboard!');">
        Copy to Clipboard
        </button>
        """
        
        components.html(copy_button_code, height=50)
     
   

    except Exception as e:
        st.error(f"Error displaying cached remaining fixtures: {e}")

def show_cached_matches_completed(match_type_id):
    """
    Displays completed matches for a given MatchTypeID using the MatchTypeCompletedCache table.
    Uses the Winner field to determine match orientation accurately.
    """
    conn = create_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            Date,
            Player1Name,
            Player1ID,
            Player2Name,
            Player2ID,
            Player1Points,
            Player2Points,
            Player1PR,
            Player1Luck,
            Player2PR,
            Player2Luck,
            Winner
        FROM MatchTypeCompletedCache
        WHERE MatchTypeID = %s
        ORDER BY Date DESC
    """
    cursor.execute(query, (match_type_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        st.warning("No completed matches found for this match type.")
        return

    # Fetch nicknames once
    nickname_lookup = {}
    try:
        conn = create_connection()
        cur = conn.cursor()
        cur.execute("SELECT PlayerID, Nickname FROM Players")
        for pid, nick in cur.fetchall():
            nickname_lookup[pid] = nick
    finally:
        cur.close()
        conn.close()

    data = []
    for row in rows:
        (date, p1_name, p1_id, p2_name, p2_id,
         p1_pts, p2_pts, p1_pr, p1_luck, p2_pr, p2_luck, winner_name) = row

        match_date = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
        p1_nick = nickname_lookup.get(p1_id, "")
        p2_nick = nickname_lookup.get(p2_id, "")
        p1_full = f"{p1_name} ({p1_nick})"
        p2_full = f"{p2_name} ({p2_nick})"

        # Use Winner field reliably
        if winner_name == p1_name:
            winner = p1_full
            loser = p2_full
            score = f"{p1_pts}-{p2_pts}"
            winner_pr, winner_luck = p1_pr, p1_luck
            loser_pr, loser_luck = p2_pr, p2_luck
        elif winner_name == p2_name:
            winner = p2_full
            loser = p1_full
            score = f"{p2_pts}-{p1_pts}"
            winner_pr, winner_luck = p2_pr, p2_luck
            loser_pr, loser_luck = p1_pr, p1_luck
        else:
            # Defensive fallback if Winner is NULL
            winner = p1_full
            loser = p2_full
            score = f"{p1_pts}-{p2_pts}"
            winner_pr, winner_luck = p1_pr, p1_luck
            loser_pr, loser_luck = p2_pr, p2_luck

        data.append([
            match_date,
            f"{winner} beat {loser}",
            score,
            round(winner_pr, 2) if winner_pr is not None else "-",
            round(winner_luck, 2) if winner_luck is not None else "-",
            round(loser_pr, 2) if loser_pr is not None else "-",
            round(loser_luck, 2) if loser_luck is not None else "-"
        ])

    st.subheader("Completed Matches:")

    df = pd.DataFrame(data, columns=[
        "Date Completed", "Result", "Score",
        "Winner PR", "Winner Luck", "Loser PR", "Loser Luck"
    ])

    if not df.empty:
        st.dataframe(
            df.style.format({
                "Winner PR": "{:.2f}",
                "Winner Luck": "{:.2f}",
                "Loser PR": "{:.2f}",
                "Loser Luck": "{:.2f}"
            }),
            hide_index=True
        )
    else:
        st.info("No completed matches found for this match type.")

def get_active_series_ids():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SeriesID FROM Series WHERE IsActive = 1")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row[0] for row in rows]

def refresh_matchtype_stats(match_type_id):
    import datetime, sys
    from collections import defaultdict
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"⚡ Refreshing MatchType stats for MatchTypeID {match_type_id}...")

        # Clear existing stats
        cursor.execute("DELETE FROM MatchTypePlayerStats WHERE MatchTypeID = %s", (match_type_id,))

        # Step 1: Calculate base stats for all players with Fixtures in this MatchType
        base_query = """
            SELECT
                p.PlayerID,
                COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Wins,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Losses,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END) AS AvgPR,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END) AS AvgLuck,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                         THEN 1 ELSE 0 END) AS PRWins
            FROM Players p
            JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
            LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
            WHERE f.MatchTypeID = %s
            GROUP BY p.PlayerID
        """
        cursor.execute(base_query, (match_type_id,))
        player_stats = cursor.fetchall()

        # Build stats dictionary
        stats_dict = {}
        for row in player_stats:
            player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
            points = (wins * 2) + (pr_wins or 0)
            win_pct = (wins / games) * 100 if games > 0 else 0
            stats_dict[player_id] = {
                "GamesPlayed": games,
                "Wins": wins,
                "Losses": losses,
                "AvgPR": avg_pr,
                "AvgLuck": avg_luck,
                "PRWins": pr_wins,
                "Points": points,
                "WinPct": win_pct,
                "HeadToHeadScore": 0
            }

        print(f"✅ Calculated base stats for {len(stats_dict)} players.")

        # Step 1b: Include walkovers
        cursor.execute("""
            SELECT WinnerID, LoserID
            FROM Walkovers
            WHERE MatchTypeID = %s
        """, (match_type_id,))
        walkovers = cursor.fetchall()

        for winner_id, loser_id in walkovers:
            # Ensure winner entry exists
            if winner_id not in stats_dict:
                stats_dict[winner_id] = {
                    "GamesPlayed": 0, "Wins": 0, "Losses": 0,
                    "AvgPR": None, "AvgLuck": None, "PRWins": 0,
                    "Points": 0, "WinPct": 0, "HeadToHeadScore": 0
                }
            stats_dict[winner_id]["Points"] += 2
            stats_dict[winner_id]["GamesPlayed"] += 1

            # Ensure loser entry exists
            if loser_id not in stats_dict:
                stats_dict[loser_id] = {
                    "GamesPlayed": 0, "Wins": 0, "Losses": 0,
                    "AvgPR": None, "AvgLuck": None, "PRWins": 0,
                    "Points": 0, "WinPct": 0, "HeadToHeadScore": 0
                }
            stats_dict[loser_id]["GamesPlayed"] += 1

        # Step 2: Identify clusters for H2H tiebreaking
        clusters = defaultdict(list)
        for pid, stats in stats_dict.items():
            key = (stats["Points"], stats["Wins"], stats["PRWins"])
            clusters[key].append(pid)

        tied_clusters = {k: v for k, v in clusters.items() if len(v) >= 2}
        print(f"🎯 {len(tied_clusters)} clusters have ties requiring H2H calculation")

        # Step 3: Calculate H2H Scores
        for key, player_ids in tied_clusters.items():
            print(f"🔍 Calculating H2H for tied cluster: {key} | Players: {player_ids}")
            for player_id in player_ids:
                h2h_score = 0
                for opponent_id in player_ids:
                    if player_id == opponent_id:
                        continue
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN Player1ID = %s AND Player1Points > Player2Points THEN 1
                                WHEN Player2ID = %s AND Player2Points > Player1Points THEN 1
                                ELSE 0
                            END AS Win
                        FROM MatchResults
                        WHERE MatchTypeID = %s
                          AND ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
                    """, (player_id, player_id, match_type_id, player_id, opponent_id, opponent_id, player_id))
                    wins = sum([row[0] for row in cursor.fetchall()])
                    h2h_score += wins
                stats_dict[player_id]["HeadToHeadScore"] = h2h_score
                print(f"🧮 Player {player_id} H2H Score: {h2h_score}")

        # Step 4: Insert into MatchTypePlayerStats
        insert_query = """
            INSERT INTO MatchTypePlayerStats (
                MatchTypeID, PlayerID, GamesPlayed, Wins, Losses, Points,
                WinPercentage, PRWins, AveragePR, AverageLuck, HeadToHeadScore
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for player_id, s in stats_dict.items():
            cursor.execute(insert_query, (
                match_type_id, player_id, s["GamesPlayed"], s["Wins"], s["Losses"], s["Points"],
                s["WinPct"], s["PRWins"], s["AvgPR"], s["AvgLuck"], s["HeadToHeadScore"]
            ))

        # Step 5: Refresh MatchTypeCompletedCache
        cursor.execute("DELETE FROM MatchTypeCompletedCache WHERE MatchTypeID = %s", (match_type_id,))
        match_query = """
            SELECT 
                mr.FixtureID, f.Player1ID, f.Player2ID, p1.Name, p2.Name,
                mr.Player1Points, mr.Player2Points,
                mr.Player1PR, mr.Player2PR,
                mr.Player1Luck, mr.Player2Luck,
                mr.Date, mr.TimeCompleted
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID AND mr.MatchTypeID = f.MatchTypeID
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            WHERE mr.MatchTypeID = %s
        """
        cursor.execute(match_query, (match_type_id,))
        completed_matches = cursor.fetchall()

        insert_completed_query = """
            INSERT INTO MatchTypeCompletedCache (
                MatchTypeID, FixtureID, Player1ID, Player2ID,
                Player1Name, Player2Name,
                Player1Points, Player2Points,
                Player1PR, Player2PR,
                Player1Luck, Player2Luck,
                Winner, Date, TimeCompleted, LastUpdated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """
        for row in completed_matches:
            (
                fixture_id, p1_id, p2_id, p1_name, p2_name,
                p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
                date, time_completed
            ) = row
            winner = p1_name if p1_pts > p2_pts else p2_name if p2_pts > p1_pts else "Draw"
            cursor.execute(insert_completed_query, (
                match_type_id, fixture_id, p1_id, p2_id,
                p1_name, p2_name,
                p1_pts, p2_pts,
                p1_pr, p2_pr,
                p1_luck, p2_luck,
                winner, date, time_completed
            ))

        conn.commit()
        print(f"✅ MatchTypePlayerStats and MatchTypeCompletedCache updated for MatchTypeID {match_type_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_matchtype_stats({match_type_id}): {e}")

    finally:
        cursor.close()
        conn.close()


def refresh_matchtype_stats0210(match_type_id):
    import datetime, sys
    from collections import defaultdict
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"⚡ Refreshing MatchType stats for MatchTypeID {match_type_id}...")

        # Clear existing stats
        cursor.execute("DELETE FROM MatchTypePlayerStats WHERE MatchTypeID = %s", (match_type_id,))

        # Step 1: Calculate base stats for all players with Fixtures in this MatchType
        base_query = """
            SELECT
                p.PlayerID,
                COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Wins,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Losses,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END) AS AvgPR,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END) AS AvgLuck,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                         THEN 1 ELSE 0 END) AS PRWins
            FROM Players p
            JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
            LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
            WHERE f.MatchTypeID = %s
            GROUP BY p.PlayerID
        """
        cursor.execute(base_query, (match_type_id,))
        player_stats = cursor.fetchall()

        # Build stats dictionary
        stats_dict = {}
        for row in player_stats:
            player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
            points = (wins * 2) + (pr_wins or 0)
            win_pct = (wins / games) * 100 if games > 0 else 0
            stats_dict[player_id] = {
                "GamesPlayed": games,
                "Wins": wins,
                "Losses": losses,
                "AvgPR": avg_pr,
                "AvgLuck": avg_luck,
                "PRWins": pr_wins,
                "Points": points,
                "WinPct": win_pct,
                "HeadToHeadScore": 0
            }

        print(f"✅ Calculated base stats for {len(stats_dict)} players.")

        # Step 2: Identify clusters for H2H tiebreaking
        clusters = defaultdict(list)
        for pid, stats in stats_dict.items():
            key = (stats["Points"], stats["Wins"], stats["PRWins"])
            clusters[key].append(pid)

        tied_clusters = {k: v for k, v in clusters.items() if len(v) >= 2}
        print(f"🎯 {len(tied_clusters)} clusters have ties requiring H2H calculation")

        # Step 3: Calculate H2H Scores
        for key, player_ids in tied_clusters.items():
            print(f"🔍 Calculating H2H for tied cluster: {key} | Players: {player_ids}")
            for player_id in player_ids:
                h2h_score = 0
                for opponent_id in player_ids:
                    if player_id == opponent_id:
                        continue
                    # Count wins against each tied opponent
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN Player1ID = %s AND Player1Points > Player2Points THEN 1
                                WHEN Player2ID = %s AND Player2Points > Player1Points THEN 1
                                ELSE 0
                            END AS Win
                        FROM MatchResults
                        WHERE MatchTypeID = %s
                          AND ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
                    """, (player_id, player_id, match_type_id, player_id, opponent_id, opponent_id, player_id))
                    wins = sum([row[0] for row in cursor.fetchall()])
                    h2h_score += wins
                stats_dict[player_id]["HeadToHeadScore"] = h2h_score
                print(f"🧮 Player {player_id} H2H Score: {h2h_score}")

        # Step 4: Insert into MatchTypePlayerStats
        insert_query = """
            INSERT INTO MatchTypePlayerStats (
                MatchTypeID, PlayerID, GamesPlayed, Wins, Losses, Points,
                WinPercentage, PRWins, AveragePR, AverageLuck, HeadToHeadScore
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for player_id, s in stats_dict.items():
            cursor.execute(insert_query, (
                match_type_id, player_id, s["GamesPlayed"], s["Wins"], s["Losses"], s["Points"],
                s["WinPct"], s["PRWins"], s["AvgPR"], s["AvgLuck"], s["HeadToHeadScore"]
            ))

        # Step 5: Refresh MatchTypeCompletedCache
        cursor.execute("DELETE FROM MatchTypeCompletedCache WHERE MatchTypeID = %s", (match_type_id,))
        match_query = """
            SELECT 
                mr.FixtureID, f.Player1ID, f.Player2ID, p1.Name, p2.Name,
                mr.Player1Points, mr.Player2Points,
                mr.Player1PR, mr.Player2PR,
                mr.Player1Luck, mr.Player2Luck,
                mr.Date, mr.TimeCompleted
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID AND mr.MatchTypeID = f.MatchTypeID
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            WHERE mr.MatchTypeID = %s
        """
        cursor.execute(match_query, (match_type_id,))
        completed_matches = cursor.fetchall()

        insert_completed_query = """
            INSERT INTO MatchTypeCompletedCache (
                MatchTypeID, FixtureID, Player1ID, Player2ID,
                Player1Name, Player2Name,
                Player1Points, Player2Points,
                Player1PR, Player2PR,
                Player1Luck, Player2Luck,
                Winner, Date, TimeCompleted, LastUpdated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """
        for row in completed_matches:
            (
                fixture_id, p1_id, p2_id, p1_name, p2_name,
                p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
                date, time_completed
            ) = row
            winner = p1_name if p1_pts > p2_pts else p2_name if p2_pts > p1_pts else "Draw"
            cursor.execute(insert_completed_query, (
                match_type_id, fixture_id, p1_id, p2_id,
                p1_name, p2_name,
                p1_pts, p2_pts,
                p1_pr, p2_pr,
                p1_luck, p2_luck,
                winner, date, time_completed
            ))

        conn.commit()
        print(f"✅ MatchTypePlayerStats and MatchTypeCompletedCache updated for MatchTypeID {match_type_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_matchtype_stats({match_type_id}): {e}")

    finally:
        cursor.close()
        conn.close()

def refresh_matchtype_stats930(match_type_id):
    import datetime
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"⚡ Refreshing MatchType stats for MatchTypeID {match_type_id}...")

        # Clear existing stats
        cursor.execute("DELETE FROM MatchTypePlayerStats WHERE MatchTypeID = %s", (match_type_id,))

        # Step 1: Calculate base stats for all players with Fixtures in this MatchType
        base_query = """
            SELECT
                p.PlayerID,
                COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Wins,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Losses,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END) AS AvgPR,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END) AS AvgLuck,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                         THEN 1 ELSE 0 END) AS PRWins
            FROM Players p
            JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
            LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
            WHERE f.MatchTypeID = %s
            GROUP BY p.PlayerID
        """
        cursor.execute(base_query, (match_type_id,))
        player_stats = cursor.fetchall()

        # Build stats dictionary
        from collections import defaultdict
        stats_dict = {}
        for row in player_stats:
            player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
            points = (wins * 2) + (pr_wins or 0)
            win_pct = (wins / games) * 100 if games > 0 else 0
            stats_dict[player_id] = {
                "GamesPlayed": games,
                "Wins": wins,
                "Losses": losses,
                "AvgPR": avg_pr,
                "AvgLuck": avg_luck,
                "PRWins": pr_wins,
                "Points": points,
                "WinPct": win_pct,
                "HeadToHeadScore": 0
            }

        print(f"✅ Calculated base stats for {len(stats_dict)} players.")
        
        # Add this debugging section right after building stats_dict and before Step 2
        
        print(f"📊 Player stats summary:")
        for player_id, stats in stats_dict.items():
            print(f"  Player {player_id}: Points={stats['Points']}, Wins={stats['Wins']}, PRWins={stats['PRWins']}, Games={stats['GamesPlayed']}")
        
        print(f"🔍 Cluster analysis:")
        clusters = defaultdict(list)
        for pid, stats in stats_dict.items():
            key = (stats["Points"], stats["Wins"], stats["PRWins"])
            clusters[key].append(pid)
        
        print(f"Found {len(clusters)} unique combinations:")
        for key, player_ids in clusters.items():
            points, wins, pr_wins = key
            print(f"  ({points} pts, {wins} wins, {pr_wins} PR wins): {len(player_ids)} players - {player_ids}")
            if len(player_ids) >= 2:
                print(f"    ⚡ This cluster will get H2H calculations!")
        
        tied_clusters = {k: v for k, v in clusters.items() if len(v) >= 2}
        print(f"🎯 {len(tied_clusters)} clusters have ties requiring H2H calculation")
        
        # Force flush the output to make sure it appears in logs immediately
        sys.stdout.flush()
              
        # Continue with your existing Step 3 logic...

        # Step 2: Identify clusters for H2H tiebreaking
        clusters = defaultdict(list)
        for pid, stats in stats_dict.items():
            key = (stats["Points"], stats["Wins"], stats["PRWins"])
            clusters[key].append(pid)

        # Step 3: Calculate H2H Scores
        for key, player_ids in clusters.items():
            if len(player_ids) < 2:
                continue
            print(f"🔍 Calculating H2H for tied cluster: {key} | Players: {player_ids}")
            for player_id in player_ids:
                h2h_score = 0
                for opponent_id in player_ids:
                    if player_id == opponent_id:
                        continue
                    cursor.execute("""
                        SELECT Player1ID, Player2ID, Player1Points, Player2Points
                        FROM MatchResults
                        WHERE MatchTypeID = %s
                          AND ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
                    """, (match_type_id, player_id, opponent_id, opponent_id, player_id))
                    matches = cursor.fetchall()
                    for m in matches:
                        p1_id, p2_id, p1_pts, p2_pts = m
                        if p1_id == player_id and p1_pts > p2_pts:
                            h2h_score += 1
                        elif p2_id == player_id and p2_pts > p1_pts:
                            h2h_score += 1
                        elif p1_id == player_id and p1_pts < p2_pts:
                            h2h_score -= 1
                        elif p2_id == player_id and p2_pts < p1_pts:
                            h2h_score -= 1
                stats_dict[player_id]["HeadToHeadScore"] = h2h_score
                print(f"🧮 Player {player_id} H2H Score: {h2h_score}")

        # Step 4: Insert into MatchTypePlayerStats
        insert_query = """
            INSERT INTO MatchTypePlayerStats (
                MatchTypeID, PlayerID, GamesPlayed, Wins, Losses, Points,
                WinPercentage, PRWins, AveragePR, AverageLuck, HeadToHeadScore
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for player_id, s in stats_dict.items():
            cursor.execute(insert_query, (
                match_type_id, player_id, s["GamesPlayed"], s["Wins"], s["Losses"], s["Points"],
                s["WinPct"], s["PRWins"], s["AvgPR"], s["AvgLuck"], s["HeadToHeadScore"]
            ))

        # Step 5: Refresh MatchTypeCompletedCache directly from MatchResults
        cursor.execute("DELETE FROM MatchTypeCompletedCache WHERE MatchTypeID = %s", (match_type_id,))
        match_query = """
            SELECT 
                mr.FixtureID, f.Player1ID, f.Player2ID, p1.Name, p2.Name,
                mr.Player1Points, mr.Player2Points,
                mr.Player1PR, mr.Player2PR,
                mr.Player1Luck, mr.Player2Luck,
                mr.Date, mr.TimeCompleted
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID AND mr.MatchTypeID = f.MatchTypeID
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            WHERE mr.MatchTypeID = %s
        """
        cursor.execute(match_query, (match_type_id,))
        completed_matches = cursor.fetchall()

        insert_completed_query = """
            INSERT INTO MatchTypeCompletedCache (
                MatchTypeID, FixtureID, Player1ID, Player2ID,
                Player1Name, Player2Name,
                Player1Points, Player2Points,
                Player1PR, Player2PR,
                Player1Luck, Player2Luck,
                Winner, Date, TimeCompleted, LastUpdated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """
        for row in completed_matches:
            (
                fixture_id, p1_id, p2_id, p1_name, p2_name,
                p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
                date, time_completed
            ) = row
            winner = p1_name if p1_pts > p2_pts else p2_name if p2_pts > p1_pts else "Draw"
            cursor.execute(insert_completed_query, (
                match_type_id, fixture_id, p1_id, p2_id,
                p1_name, p2_name,
                p1_pts, p2_pts,
                p1_pr, p2_pr,
                p1_luck, p2_luck,
                winner, date, time_completed
            ))

        conn.commit()
        print(f"✅ MatchTypePlayerStats and MatchTypeCompletedCache updated for MatchTypeID {match_type_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_matchtype_stats({match_type_id}): {e}")

    finally:
        cursor.close()
        conn.close()

def refresh_matchtype_stats44(match_type_id):
    import datetime
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"⚡ Refreshing MatchType stats for MatchTypeID {match_type_id}...")

        # Clear existing stats
        cursor.execute("DELETE FROM MatchTypePlayerStats WHERE MatchTypeID = %s", (match_type_id,))

        # Step 1: Calculate base stats for all players with Fixtures in this MatchType
        base_query = """
            SELECT
                p.PlayerID,
                COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Wins,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Losses,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END) AS AvgPR,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END) AS AvgLuck,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                         THEN 1 ELSE 0 END) AS PRWins
            FROM Players p
            JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
            LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
            WHERE f.MatchTypeID = %s
            GROUP BY p.PlayerID
        """
        cursor.execute(base_query, (match_type_id,))
        player_stats = cursor.fetchall()

        # Build a dict to hold interim stats for easier cluster processing
        stats_dict = {}
        for row in player_stats:
            player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
            points = (wins * 2) + (pr_wins or 0)
            win_pct = (wins / games) * 100 if games > 0 else 0
            stats_dict[player_id] = {
                "GamesPlayed": games,
                "Wins": wins,
                "Losses": losses,
                "AvgPR": avg_pr,
                "AvgLuck": avg_luck,
                "PRWins": pr_wins,
                "Points": points,
                "WinPct": win_pct,
                "HeadToHeadScore": 0  # default, will update for clusters
            }

        print(f"✅ Calculated base stats for {len(stats_dict)} players.")

        # Step 2: Identify clusters tied on Points, Wins, PRWins
        from collections import defaultdict
        clusters = defaultdict(list)
        for pid, stats in stats_dict.items():
            key = (stats["Points"], stats["Wins"], stats["PRWins"])
            clusters[key].append(pid)

        # Step 3: For each cluster with more than one player, compute H2H among them
        for key, player_ids in clusters.items():
            if len(player_ids) < 2:
                continue  # skip non-tied players

            print(f"🔍 Computing H2H for tied cluster: Points={key[0]}, Wins={key[1]}, PRWins={key[2]} | Players={player_ids}")

            for player_id in player_ids:
                h2h_score = 0
                for opponent_id in player_ids:
                    if player_id == opponent_id:
                        continue

                    cursor.execute("""
                        SELECT Player1ID, Player2ID, Player1Points, Player2Points
                        FROM MatchResults
                        WHERE MatchTypeID = %s
                          AND ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
                    """, (match_type_id, player_id, opponent_id, opponent_id, player_id))
                    matches = cursor.fetchall()

                    for m in matches:
                        p1_id, p2_id, p1_pts, p2_pts = m
                        if p1_id == player_id and p1_pts > p2_pts:
                            h2h_score += 1
                        elif p2_id == player_id and p2_pts > p1_pts:
                            h2h_score += 1
                        elif p1_id == player_id and p1_pts < p2_pts:
                            h2h_score -= 1
                        elif p2_id == player_id and p2_pts < p1_pts:
                            h2h_score -= 1

                stats_dict[player_id]["HeadToHeadScore"] = h2h_score
                print(f"🧮 Player {player_id} H2H Score: {h2h_score}")

        # Step 4: Insert updated stats into MatchTypePlayerStats
        insert_query = """
            INSERT INTO MatchTypePlayerStats (
                MatchTypeID, PlayerID, GamesPlayed, Wins, Losses, Points,
                WinPercentage, PRWins, AveragePR, AverageLuck, HeadToHeadScore
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for player_id, s in stats_dict.items():
            cursor.execute(insert_query, (
                match_type_id, player_id, s["GamesPlayed"], s["Wins"], s["Losses"], s["Points"],
                s["WinPct"], s["PRWins"], s["AvgPR"], s["AvgLuck"], s["HeadToHeadScore"]
            ))

        conn.commit()
        print(f"✅ MatchTypePlayerStats updated with proper H2H tiebreaks for MatchTypeID {match_type_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_matchtype_stats({match_type_id}): {e}")
    finally:
        cursor.close()
        conn.close()

def refresh_matchtype_stats3(match_type_id):
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"Refreshing MatchType stats for MatchTypeID {match_type_id}...")

        cursor.execute("DELETE FROM MatchTypePlayerStats WHERE MatchTypeID = %s", (match_type_id,))

        standings_query = """
            SELECT
                p.PlayerID,
                COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Wins,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Losses,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END) AS AvgPR,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END) AS AvgLuck,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                         THEN 1 ELSE 0 END) AS PRWins
            FROM Players p
            JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
            LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
            WHERE f.MatchTypeID = %s
            GROUP BY p.PlayerID
        """
        cursor.execute(standings_query, (match_type_id,))
        player_stats = cursor.fetchall()

        # Gather players in this MatchType for H2H calculations
        player_ids = [row[0] for row in player_stats]

        for row in player_stats:
            player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
            points = (wins * 2) + (pr_wins or 0)
            win_pct = (wins / games) * 100 if games > 0 else 0

            # Calculate HeadToHeadScore for this player
            h2h_score = 0
            for opponent_id in player_ids:
                if opponent_id == player_id:
                    continue
                cursor.execute("""
                    SELECT Player1ID, Player2ID, Player1Points, Player2Points
                    FROM MatchResults
                    WHERE MatchTypeID = %s
                      AND ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
                """, (match_type_id, player_id, opponent_id, opponent_id, player_id))
                matches = cursor.fetchall()
                for m in matches:
                    p1_id, p2_id, p1_pts, p2_pts = m
                
                    # Identify which is 'self' and 'opponent' in the match
                    if p1_id == player_id:
                        self_pts = p1_pts
                        opp_pts = p2_pts
                    else:
                        self_pts = p2_pts
                        opp_pts = p1_pts
                
                    if self_pts > opp_pts:
                        h2h_score += 1
                    elif self_pts < opp_pts:
                        h2h_score -= 1
                    # draws do not affect h2h_score


            cursor.execute("""
                INSERT INTO MatchTypePlayerStats (
                    MatchTypeID, PlayerID, GamesPlayed, Wins, Losses, Points,
                    WinPercentage, PRWins, AveragePR, AverageLuck, HeadToHeadScore
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                match_type_id, player_id, games, wins, losses, points,
                win_pct, pr_wins, avg_pr, avg_luck, h2h_score
            ))

        conn.commit()
        print(f"✅ MatchType stats and caches updated with HeadToHeadScore for MatchTypeID {match_type_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_matchtype_stats({match_type_id}): {e}")
    finally:
        cursor.close()
        conn.close()

def refresh_matchtype_stats2(match_type_id):
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"Refreshing MatchType stats for MatchTypeID {match_type_id}...")

        # Step 1: Refresh MatchTypePlayerStats
        cursor.execute("DELETE FROM MatchTypePlayerStats WHERE MatchTypeID = %s", (match_type_id,))

        standings_query = """
            SELECT
                p.PlayerID,
                COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Wins,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                         THEN 1 ELSE 0 END) AS Losses,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END) AS AvgPR,
                AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                         WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END) AS AvgLuck,
                SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR)
                          OR (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                         THEN 1 ELSE 0 END) AS PRWins
            FROM Players p
            JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
            LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
            WHERE f.MatchTypeID = %s
            GROUP BY p.PlayerID
        """
        cursor.execute(standings_query, (match_type_id,))
        for row in cursor.fetchall():
            player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
            points = (wins * 2) + (pr_wins or 0)
            win_pct = (wins / games) * 100 if games > 0 else 0

            cursor.execute("""
                INSERT INTO MatchTypePlayerStats (
                    MatchTypeID, PlayerID, GamesPlayed, Wins, Losses, Points,
                    WinPercentage, PRWins, AveragePR, AverageLuck
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                match_type_id, player_id, games, wins, losses, points,
                win_pct, pr_wins, avg_pr, avg_luck
            ))

        # Step 2: Refresh MatchTypeCompletedCache
        cursor.execute("DELETE FROM MatchTypeCompletedCache WHERE MatchTypeID = %s", (match_type_id,))

        match_query = """
            SELECT 
                f.FixtureID,
                f.Player1ID, f.Player2ID,
                p1.Name, p2.Name,
                mr.Player1Points, mr.Player2Points,
                mr.Player1PR, mr.Player2PR,
                mr.Player1Luck, mr.Player2Luck,
                mr.Date, mr.TimeCompleted
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID AND mr.MatchTypeID = f.MatchTypeID
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            WHERE mr.MatchTypeID = %s
        """
        cursor.execute(match_query, (match_type_id,))
        insert_query = """
            INSERT INTO MatchTypeCompletedCache (
                MatchTypeID, FixtureID, Player1ID, Player2ID,
                Player1Name, Player2Name,
                Player1Points, Player2Points,
                Player1PR, Player2PR,
                Player1Luck, Player2Luck,
                Winner, Date, TimeCompleted, LastUpdated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """
        for row in cursor.fetchall():
            (fixture_id, p1_id, p2_id, p1_name, p2_name,
             p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
             date, time_completed) = row

            winner = (
                p1_name if p1_pts > p2_pts else
                p2_name if p2_pts > p1_pts else "Draw"
            )

            cursor.execute(insert_query, (
                match_type_id, fixture_id, p1_id, p2_id,
                p1_name, p2_name,
                p1_pts, p2_pts,
                p1_pr, p2_pr,
                p1_luck, p2_luck,
                winner, date, time_completed
            ))

        # Step 3: Refresh MatchTypeRemainingFixtures
        cursor.execute("DELETE FROM MatchTypeRemainingFixtures WHERE MatchTypeID = %s", (match_type_id,))

        fixture_query = """
            SELECT p1.Name, p2.Name
            FROM Fixtures f
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            WHERE f.MatchTypeID = %s AND f.Completed = 0
        """
        cursor.execute(fixture_query, (match_type_id,))
        remaining_rows = cursor.fetchall()

        insert_remaining = """
            INSERT INTO MatchTypeRemainingFixtures (
                MatchTypeID, Player1Name, Player2Name, LastUpdated
            ) VALUES (%s, %s, %s, NOW())
        """
        for row in remaining_rows:
            cursor.execute(insert_remaining, (match_type_id, row[0], row[1]))

        conn.commit()
        print(f"✅ MatchType stats and caches updated for MatchTypeID {match_type_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_matchtype_stats({match_type_id}): {e}")
    finally:
        cursor.close()
        conn.close()


def refresh_matchtype_stats1(match_type_id):
    import pymysql
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"Refreshing MatchType stats for MatchTypeID {match_type_id}...")

        # Step 1: Refresh MatchTypePlayerStats
        cursor.execute("DELETE FROM MatchTypePlayerStats WHERE MatchTypeID = %s", (match_type_id,))

        standings_query = """
            SELECT
                p.PlayerID,
                COUNT(mr.MatchResultID) AS GamesPlayed,
                SUM(
                    CASE 
                        WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points) OR
                             (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                        THEN 1 ELSE 0
                    END
                ) AS Wins,
                SUM(
                    CASE 
                        WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points) OR
                             (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                        THEN 1 ELSE 0
                    END
                ) AS Losses,
                AVG(
                    CASE
                        WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                        WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR
                    END
                ) AS AvgPR,
                AVG(
                    CASE
                        WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                        WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck
                    END
                ) AS AvgLuck,
                SUM(
                    CASE
                        WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR) OR
                             (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                        THEN 1 ELSE 0
                    END
                ) AS PRWins
            FROM Players p
            JOIN MatchResults mr ON (p.PlayerID = mr.Player1ID OR p.PlayerID = mr.Player2ID)
            WHERE mr.MatchTypeID = %s
            GROUP BY p.PlayerID
        """
        cursor.execute(standings_query, (match_type_id,))
        for row in cursor.fetchall():
            player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
            points = (wins * 2) + (pr_wins or 0)
            win_pct = (wins / games) * 100 if games > 0 else 0

            cursor.execute("""
                INSERT INTO MatchTypePlayerStats (
                    MatchTypeID, PlayerID, GamesPlayed, Wins, Losses, Points,
                    WinPercentage, PRWins, AveragePR, AverageLuck
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                match_type_id, player_id, games, wins, losses, points,
                win_pct, pr_wins, avg_pr, avg_luck
            ))

        # Step 2: Refresh MatchTypeCompletedCache
        cursor.execute("DELETE FROM MatchTypeCompletedCache WHERE MatchTypeID = %s", (match_type_id,))

        match_query = """
            SELECT
                mr.FixtureID,
                mr.Player1ID, mr.Player2ID,
                p1.Name, p2.Name,
                mr.Player1Points, mr.Player2Points,
                mr.Player1PR, mr.Player2PR,
                mr.Player1Luck, mr.Player2Luck,
                mr.Date, mr.TimeCompleted
            FROM MatchResults mr
            JOIN Players p1 ON mr.Player1ID = p1.PlayerID
            JOIN Players p2 ON mr.Player2ID = p2.PlayerID
            WHERE mr.MatchTypeID = %s
        """
        cursor.execute(match_query, (match_type_id,))
        insert_query = """
            INSERT INTO MatchTypeCompletedCache (
                MatchTypeID, FixtureID, Player1ID, Player2ID,
                Player1Name, Player2Name,
                Player1Points, Player2Points,
                Player1PR, Player2PR,
                Player1Luck, Player2Luck,
                Winner, Date, TimeCompleted, LastUpdated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """
        for row in cursor.fetchall():
            (fixture_id, p1_id, p2_id, p1_name, p2_name,
             p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
             date, time_completed) = row

            winner = (
                p1_name if p1_pts > p2_pts else
                p2_name if p2_pts > p1_pts else "Draw"
            )

            cursor.execute(insert_query, (
                match_type_id, fixture_id, p1_id, p2_id,
                p1_name, p2_name,
                p1_pts, p2_pts,
                p1_pr, p2_pr,
                p1_luck, p2_luck,
                winner, date, time_completed
            ))

        # Step 3: Refresh MatchTypeRemainingFixtures (STILL USES FIXTURES)
        cursor.execute("DELETE FROM MatchTypeRemainingFixtures WHERE MatchTypeID = %s", (match_type_id,))

        fixture_query = """
            SELECT p1.Name, p2.Name
            FROM Fixtures f
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            WHERE f.MatchTypeID = %s AND f.Completed = 0
        """
        cursor.execute(fixture_query, (match_type_id,))
        remaining_rows = cursor.fetchall()

        insert_remaining = """
            INSERT INTO MatchTypeRemainingFixtures (
                MatchTypeID, Player1Name, Player2Name, LastUpdated
            ) VALUES (%s, %s, %s, NOW())
        """
        for row in remaining_rows:
            cursor.execute(insert_remaining, (match_type_id, row[0], row[1]))

        conn.commit()
        print(f"✅ MatchType stats and caches updated for MatchTypeID {match_type_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_matchtype_stats({match_type_id}): {e}")

    finally:
        cursor.close()
        conn.close()

def list_cached_remaining_fixtures(match_type_id):
    """
    Display remaining fixtures for a given match type using cached data.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT Player1Name, Player2Name
            FROM MatchTypeRemainingFixtures
            WHERE MatchTypeID = %s
            ORDER BY Player1Name, Player2Name
        """
        cursor.execute(query, (match_type_id,))
        rows = cursor.fetchall()

        if rows:
            st.subheader("Remaining Fixtures:")
            for player1, player2 in rows:
                st.write(f"- **{player1}** vs **{player2}**")
        else:
            st.write("No remaining fixtures for this match type.")

    except Exception as e:
        st.error(f"Error loading cached remaining fixtures: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_completed_match_cache(series_id):
    import datetime
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Clear existing cache for this series
        cursor.execute("DELETE FROM CompletedMatchesCache WHERE SeriesID = %s", (series_id,))

        # Step 2: Fetch completed matches along with MatchTypeTitle
        query = """
            SELECT 
                s.SeriesID,
                f.MatchTypeID,
                f.FixtureID,
                f.Player1ID,
                f.Player2ID,
                p1.Name AS Player1Name,
                p2.Name AS Player2Name,
                mr.Player1Points,
                mr.Player2Points,
                mr.Player1PR,
                mr.Player2PR,
                mr.Player1Luck,
                mr.Player2Luck,
                mr.Date,
                mr.TimeCompleted,
                mt.MatchTypeTitle
            FROM Fixtures f
            JOIN MatchResults mr ON mr.FixtureID = f.FixtureID
            JOIN SeriesMatchTypes s ON s.MatchTypeID = f.MatchTypeID
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
            WHERE s.SeriesID = %s
        """

        cursor.execute(query, (series_id,))
        matches = cursor.fetchall()

        insert_query = """
            INSERT INTO CompletedMatchesCache (
                SeriesID, MatchTypeID, FixtureID,
                Player1ID, Player2ID, Player1Name, Player2Name,
                Player1Points, Player2Points,
                Player1PR, Player2PR,
                Player1Luck, Player2Luck,
                Winner, Date, TimeCompleted, LastUpdated,
                MatchTypeTitle
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s
            )
        """

        for row in matches:
            (
                s_id, matchtype_id, fixture_id,
                p1_id, p2_id, p1_name, p2_name,
                p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
                date, time_completed, match_type_title
            ) = row

            winner = (
                p1_name if p1_pts > p2_pts else
                p2_name if p2_pts > p1_pts else
                "Draw"
            )

            cursor.execute(insert_query, (
                s_id, matchtype_id, fixture_id,
                p1_id, p2_id, p1_name, p2_name,
                p1_pts, p2_pts,
                p1_pr, p2_pr,
                p1_luck, p2_luck,
                winner, date, time_completed, datetime.datetime.now(),
                match_type_title
            ))

        conn.commit()
        print(f"✅ Completed match cache refreshed for Series {series_id}.")

    except Exception as e:
        print(f"❌ Error in match cache refresh: {e}")
    finally:
        cursor.close()
        conn.close()

def refresh_series_stats(series_id):
    import datetime
    from collections import defaultdict
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"⚡ Refreshing Series stats for SeriesID {series_id}...")

        # Clear existing stats
        cursor.execute("DELETE FROM SeriesPlayerStats WHERE SeriesID = %s", (series_id,))

        # Get all MatchTypes in this Series
        cursor.execute("SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s", (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]
        if not match_type_ids:
            print(f"⚠️ No MatchTypes found for SeriesID {series_id}. Aborting refresh.")
            return

        # Step 1: Aggregate base stats across all match types
        stats_dict = {}
        for match_type_id in match_type_ids:
            cursor.execute("""
                SELECT
                    p.PlayerID,
                    COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
                    SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points)
                              OR (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                             THEN 1 ELSE 0 END) AS Wins,
                    SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points)
                              OR (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                             THEN 1 ELSE 0 END) AS Losses,
                    AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                             WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END) AS AvgPR,
                    AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                             WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END) AS AvgLuck,
                    SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR)
                              OR (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                             THEN 1 ELSE 0 END) AS PRWins
                FROM Players p
                JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
                LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
                WHERE f.MatchTypeID = %s
                GROUP BY p.PlayerID
            """, (match_type_id,))
            player_stats = cursor.fetchall()

            # Build/aggregate stats_dict
            for row in player_stats:
                player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
                points = (wins * 2) + (pr_wins or 0)
                if player_id not in stats_dict:
                    stats_dict[player_id] = {
                        "GamesPlayed": games,
                        "Wins": wins,
                        "Losses": losses,
                        "AvgPR": avg_pr,
                        "AvgLuck": avg_luck,
                        "PRWins": pr_wins,
                        "Points": points,
                        "WinPct": (wins / games) * 100 if games > 0 else 0,
                        "HeadToHeadScore": 0
                    }
                else:
                    # Aggregate across multiple match types
                    s = stats_dict[player_id]
                    s["GamesPlayed"] += games
                    s["Wins"] += wins
                    s["Losses"] += losses
                    s["PRWins"] += pr_wins or 0
                    s["Points"] += points
                    s["AvgPR"] = ((s["AvgPR"] or 0) + (avg_pr or 0)) / 2 if avg_pr is not None else s["AvgPR"]
                    s["AvgLuck"] = ((s["AvgLuck"] or 0) + (avg_luck or 0)) / 2 if avg_luck is not None else s["AvgLuck"]
                    s["WinPct"] = (s["Wins"] / s["GamesPlayed"]) * 100 if s["GamesPlayed"] > 0 else 0

        print(f"📊 Base stats collected for {len(stats_dict)} players.")

        # Step 2: Compute H2H for tied clusters
        clusters = defaultdict(list)
        for pid, stats in stats_dict.items():
            key = (stats["Points"], stats["Wins"], stats["PRWins"])
            clusters[key].append(pid)

        for key, player_ids in clusters.items():
            if len(player_ids) < 2:
                continue
            print(f"🔍 Calculating H2H for tied cluster: {key} | Players: {player_ids}")
            for player_id in player_ids:
                h2h_score = 0
                for opponent_id in player_ids:
                    if player_id == opponent_id:
                        continue
                    cursor.execute("""
                        SELECT 
                            CASE
                                WHEN Player1ID = %s AND Player1Points > Player2Points THEN 1
                                WHEN Player2ID = %s AND Player2Points > Player1Points THEN 1
                                ELSE 0
                            END AS Win
                        FROM MatchResults
                        WHERE MatchTypeID IN (
                            SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s
                        )
                        AND ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
                    """, (player_id, player_id, series_id, player_id, opponent_id, opponent_id, player_id))
                    h2h_score += sum(row[0] for row in cursor.fetchall())
                stats_dict[player_id]["HeadToHeadScore"] = h2h_score
                print(f"🧮 Player {player_id} H2H Score: {h2h_score}")

        # Step 3: Insert into SeriesPlayerStats
        insert_query = """
            INSERT INTO SeriesPlayerStats (
                SeriesID, PlayerID, GamesPlayed, Wins, Losses, Points,
                WinPercentage, PRWins, AveragePR, AverageLuck, HeadToHeadScore
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for player_id, s in stats_dict.items():
            cursor.execute(insert_query, (
                series_id, player_id, s["GamesPlayed"], s["Wins"], s["Losses"], s["Points"],
                s["WinPct"], s["PRWins"], s["AvgPR"], s["AvgLuck"], s["HeadToHeadScore"]
            ))

        # Step 4: Refresh CompletedMatchesCache
        cursor.execute("DELETE FROM CompletedMatchesCache WHERE SeriesID = %s", (series_id,))
        cursor.execute("""
            SELECT 
                mr.FixtureID, f.MatchTypeID, f.Player1ID, f.Player2ID,
                p1.Name, p2.Name,
                mr.Player1Points, mr.Player2Points,
                mr.Player1PR, mr.Player2PR,
                mr.Player1Luck, mr.Player2Luck,
                mr.Date, mr.TimeCompleted
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID AND mr.MatchTypeID = f.MatchTypeID
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            WHERE f.MatchTypeID IN (
                SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s
            )
        """, (series_id,))
        completed_matches = cursor.fetchall()

        insert_completed_query = """
            INSERT INTO CompletedMatchesCache (
                SeriesID, FixtureID, MatchTypeID, Player1ID, Player2ID,
                Player1Name, Player2Name,
                Player1Points, Player2Points,
                Player1PR, Player2PR,
                Player1Luck, Player2Luck,
                Winner, Date, TimeCompleted, LastUpdated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """
        for row in completed_matches:
            (
                fixture_id, match_type_id, p1_id, p2_id, p1_name, p2_name,
                p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
                date, time_completed
            ) = row
            winner = p1_name if p1_pts > p2_pts else p2_name if p2_pts > p1_pts else "Draw"
            cursor.execute(insert_completed_query, (
                series_id, fixture_id, match_type_id, p1_id, p2_id,
                p1_name, p2_name,
                p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
                winner, date, time_completed
            ))

        conn.commit()
        print(f"✅ SeriesPlayerStats and CompletedMatchesCache updated for SeriesID {series_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_series_stats({series_id}): {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def refresh_series_stats930(series_id):
    import datetime
    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"⚡ Refreshing Series stats for SeriesID {series_id}...")

        # Clear existing stats
        cursor.execute("DELETE FROM SeriesPlayerStats WHERE SeriesID = %s", (series_id,))

        # Get all MatchTypes in this Series
        cursor.execute("SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s", (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            print(f"⚠️ No MatchTypes found for SeriesID {series_id}. Aborting refresh.")
            return

        for match_type_id in match_type_ids:
            print(f"🔄 Processing MatchTypeID {match_type_id} for SeriesID {series_id}...")

            # Step 1: Calculate base stats for players with Fixtures in these MatchTypes
            cursor.execute("""
                SELECT
                    p.PlayerID,
                    COUNT(DISTINCT mr.MatchResultID) AS GamesPlayed,
                    SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points)
                              OR (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                             THEN 1 ELSE 0 END) AS Wins,
                    SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points)
                              OR (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                             THEN 1 ELSE 0 END) AS Losses,
                    AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                             WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR ELSE NULL END) AS AvgPR,
                    AVG(CASE WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                             WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck ELSE NULL END) AS AvgLuck,
                    SUM(CASE WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR)
                              OR (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                             THEN 1 ELSE 0 END) AS PRWins
                FROM Players p
                JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
                LEFT JOIN MatchResults mr ON f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID
                WHERE f.MatchTypeID = %s
                GROUP BY p.PlayerID
            """, (match_type_id,))
            player_stats = cursor.fetchall()

            # Build dict for H2H calculation
            from collections import defaultdict
            stats_dict = {}
            for row in player_stats:
                player_id, games, wins, losses, avg_pr, avg_luck, pr_wins = row
                points = (wins * 2) + (pr_wins or 0)
                win_pct = (wins / games) * 100 if games > 0 else 0
                stats_dict[player_id] = {
                    "GamesPlayed": games,
                    "Wins": wins,
                    "Losses": losses,
                    "AvgPR": avg_pr,
                    "AvgLuck": avg_luck,
                    "PRWins": pr_wins,
                    "Points": points,
                    "WinPct": win_pct,
                    "HeadToHeadScore": 0
                }

            # H2H Calculation within tied clusters
            clusters = defaultdict(list)
            for pid, stats in stats_dict.items():
                key = (stats["Points"], stats["Wins"], stats["PRWins"])
                clusters[key].append(pid)

            for key, player_ids in clusters.items():
                if len(player_ids) < 2:
                    continue
                for player_id in player_ids:
                    h2h_score = 0
                    for opponent_id in player_ids:
                        if player_id == opponent_id:
                            continue
                        cursor.execute("""
                            SELECT Player1ID, Player2ID, Player1Points, Player2Points
                            FROM MatchResults
                            WHERE MatchTypeID = %s
                              AND ((Player1ID = %s AND Player2ID = %s) OR (Player1ID = %s AND Player2ID = %s))
                        """, (match_type_id, player_id, opponent_id, opponent_id, player_id))
                        matches = cursor.fetchall()
                        for m in matches:
                            p1_id, p2_id, p1_pts, p2_pts = m
                            if p1_id == player_id and p1_pts > p2_pts:
                                h2h_score += 1
                            elif p2_id == player_id and p2_pts > p1_pts:
                                h2h_score += 1
                            elif p1_id == player_id and p1_pts < p2_pts:
                                h2h_score -= 1
                            elif p2_id == player_id and p2_pts < p1_pts:
                                h2h_score -= 1
                    stats_dict[player_id]["HeadToHeadScore"] = h2h_score

            # Insert into SeriesPlayerStats
            insert_query = """
                INSERT INTO SeriesPlayerStats (
                    SeriesID, PlayerID, GamesPlayed, Wins, Losses, Points,
                    WinPercentage, PRWins, AveragePR, AverageLuck, HeadToHeadScore
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            for player_id, s in stats_dict.items():
                cursor.execute(insert_query, (
                    series_id, player_id, s["GamesPlayed"], s["Wins"], s["Losses"], s["Points"],
                    s["WinPct"], s["PRWins"], s["AvgPR"], s["AvgLuck"], s["HeadToHeadScore"]
                ))

        # Step 2: Refresh CompletedMatchesCache
        cursor.execute("DELETE FROM CompletedMatchesCache WHERE SeriesID = %s", (series_id,))
        cursor.execute("""
            SELECT 
                mr.FixtureID, f.MatchTypeID, f.Player1ID, f.Player2ID,
                p1.Name, p2.Name,
                mr.Player1Points, mr.Player2Points,
                mr.Player1PR, mr.Player2PR,
                mr.Player1Luck, mr.Player2Luck,
                mr.Date, mr.TimeCompleted
            FROM MatchResults mr
            JOIN Fixtures f ON mr.FixtureID = f.FixtureID AND mr.MatchTypeID = f.MatchTypeID
            JOIN Players p1 ON f.Player1ID = p1.PlayerID
            JOIN Players p2 ON f.Player2ID = p2.PlayerID
            WHERE f.MatchTypeID IN (
                SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s
            )
        """, (series_id,))
        completed_matches = cursor.fetchall()

        insert_completed_query = """
            INSERT INTO CompletedMatchesCache (
                SeriesID, FixtureID, MatchTypeID, Player1ID, Player2ID,
                Player1Name, Player2Name,
                Player1Points, Player2Points,
                Player1PR, Player2PR,
                Player1Luck, Player2Luck,
                Winner, Date, TimeCompleted, LastUpdated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
        """
        for row in completed_matches:
            (
                fixture_id, match_type_id, p1_id, p2_id, p1_name, p2_name,
                p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
                date, time_completed
            ) = row
            winner = p1_name if p1_pts > p2_pts else p2_name if p2_pts > p1_pts else "Draw"
            cursor.execute(insert_completed_query, (
                series_id, fixture_id, match_type_id, p1_id, p2_id,
                p1_name, p2_name,
                p1_pts, p2_pts, p1_pr, p2_pr, p1_luck, p2_luck,
                winner, date, time_completed
            ))

        conn.commit()
        print(f"✅ SeriesPlayerStats and CompletedMatchesCache updated for SeriesID {series_id}.")

    except Exception as e:
        print(f"❌ Error in refresh_series_stats({series_id}): {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def refresh_series_stats1(series_id):
    import pymysql
    import traceback

    conn = create_connection()
    cursor = conn.cursor()

    try:
        print(f"Refreshing SeriesPlayerStats for SeriesID {series_id}...")

        # Retrieve MatchTypeIDs for this series
        cursor.execute("SELECT MatchTypeID FROM SeriesMatchTypes WHERE SeriesID = %s", (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            print(f"No MatchTypes found for SeriesID {series_id}.")
            return

        match_type_ids_tuple = tuple(match_type_ids)
        if len(match_type_ids_tuple) == 1:
            match_type_ids_clause = f"= {match_type_ids_tuple[0]}"
        else:
            match_type_ids_clause = f"IN {match_type_ids_tuple}"

        # Build query using MatchResults as source
        query = f"""
            SELECT
                p.PlayerID,
                COUNT(mr.MatchResultID) AS GamesPlayed,
                SUM(
                    CASE 
                        WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points > mr.Player2Points) OR
                             (p.PlayerID = mr.Player2ID AND mr.Player2Points > mr.Player1Points)
                        THEN 1 ELSE 0
                    END
                ) AS Wins,
                SUM(
                    CASE 
                        WHEN (p.PlayerID = mr.Player1ID AND mr.Player1Points < mr.Player2Points) OR
                             (p.PlayerID = mr.Player2ID AND mr.Player2Points < mr.Player1Points)
                        THEN 1 ELSE 0
                    END
                ) AS Losses,
                AVG(
                    CASE
                        WHEN p.PlayerID = mr.Player1ID THEN mr.Player1PR
                        WHEN p.PlayerID = mr.Player2ID THEN mr.Player2PR
                    END
                ) AS AveragePR,
                SUM(
                    CASE
                        WHEN (p.PlayerID = mr.Player1ID AND mr.Player1PR < mr.Player2PR) OR
                             (p.PlayerID = mr.Player2ID AND mr.Player2PR < mr.Player1PR)
                        THEN 1 ELSE 0
                    END
                ) AS PRWins,
                AVG(
                    CASE
                        WHEN p.PlayerID = mr.Player1ID THEN mr.Player1Luck
                        WHEN p.PlayerID = mr.Player2ID THEN mr.Player2Luck
                    END
                ) AS AverageLuck
            FROM Players p
            JOIN MatchResults mr ON (p.PlayerID = mr.Player1ID OR p.PlayerID = mr.Player2ID)
            WHERE mr.MatchTypeID {match_type_ids_clause}
            GROUP BY p.PlayerID
        """

        cursor.execute(query)
        stats = cursor.fetchall()

        # Clear existing cache
        cursor.execute("DELETE FROM SeriesPlayerStats WHERE SeriesID = %s", (series_id,))

        # Insert refreshed stats
        insert_query = """
            INSERT INTO SeriesPlayerStats
            (SeriesID, PlayerID, GamesPlayed, Wins, Losses, WinPercentage, Points, AveragePR, PRWins, AverageLuck, LastUpdated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        for row in stats:
            player_id = row[0]
            games = row[1] or 0
            wins = row[2] or 0
            losses = row[3] or 0
            avg_pr = float(row[4]) if row[4] is not None else None
            pr_wins = row[5] or 0
            avg_luck = float(row[6]) if row[6] is not None else None
            win_pct = round((wins / games) * 100, 2) if games > 0 else 0
            points = (wins * 2) + pr_wins

            cursor.execute(insert_query, (
                series_id, player_id, games, wins, losses, win_pct,
                points, avg_pr, pr_wins, avg_luck
            ))

        conn.commit()
        print(f"✅ SeriesPlayerStats refreshed successfully for SeriesID {series_id}.")

    except Exception as e:
        print(f"❌ Error refreshing SeriesPlayerStats for SeriesID {series_id}: {str(e)}")
        traceback.print_exc()

    finally:
        cursor.close()
        conn.close()

def get_completed_matches_for_series(series_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Player1Name, Player2Name, Player1Points, Player2Points,
               Player1PR, Player2PR, Winner, Date
        FROM CompletedMatchesCache
        WHERE SeriesID = %s
        ORDER BY Date DESC
    """, (series_id,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=[
        "Player 1", "Player 2", "P1 Points", "P2 Points", "P1 PR", "P2 PR", "Winner", "Date"
    ])

def fetch_series_standings(series_id):
    """
    Display standings using precomputed stats from SeriesPlayerStats for the given series.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p.Name,
                p.Nickname,
                sps.GamesPlayed,
                sps.Wins,
                sps.Losses,
                sps.Points,
                sps.WinPercentage,
                sps.AveragePR,
                sps.PRWins,
                sps.AverageLuck
            FROM SeriesPlayerStats sps
            JOIN Players p ON sps.PlayerID = p.PlayerID
            WHERE sps.SeriesID = %s
            ORDER BY sps.Points DESC, sps.WinPercentage DESC, sps.AveragePR ASC
        """
        cursor.execute(query, (series_id,))
        rows = cursor.fetchall()

        if not rows:
            st.subheader("No stats available for this series.")
            return

        formatted_stats = []
        for row in rows:
            try:
                name_nickname = f"{row[0]} ({row[1]})"
                games_played = int(row[2] or 0)
                wins = int(row[3] or 0)
                losses = int(row[4] or 0)
                points = int(row[5] or 0)
                win_pct_val = safe_float(row[6])
                win_pct = f"{win_pct_val:.2f}%" if win_pct_val is not None else "0.00%"
                avg_pr = safe_float(row[7])
                pr_wins = int(row[8] or 0)
                avg_luck = safe_float(row[9])
                points_pct = f"{(points / (games_played * 3)) * 100:.2f}%" if games_played > 0 else "0.00%"
                
                formatted_stats.append([
                    name_nickname, games_played, points, points_pct, wins, pr_wins, losses, win_pct, avg_pr, avg_luck
                ])
            except Exception as e:
                st.warning(f"Skipped row due to error: {e}")

        df = pd.DataFrame(formatted_stats, columns=[
            "Name (Nickname)", "Played", "Points", "Points%", "Wins", "PR wins", "Losses", "Win%", "Avg PR", "Avg Luck"
        ])
        
        numeric_cols = ["Played", "Points", "Wins", "PR wins", "Losses", "Avg PR", "Avg Luck"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

        styled_df = df.style.set_properties(**{"font-weight": "bold"}, subset=["Points"]).format({
            "Avg PR": "{:.2f}", "Avg Luck": "{:.2f}", "Points%": "{:.2f}", "Win%": "{:.2f}"
        })

        st.subheader("Series Standings with Pointss:")
        st.dataframe(styled_df)

    except Exception as e:
        st.error(f"Error displaying series standings: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def fetch_cached_series_standings(series_id):
    """
    Display standings using precomputed stats from SeriesPlayerStats for the given series,
    sorted by Points% DESC, then Points DESC, then Win% DESC, then Avg PR ASC.
    """
    import pandas as pd

    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p.Name,
                p.Nickname,
                sps.GamesPlayed,
                sps.Wins,
                sps.Losses,
                sps.Points,
                sps.WinPercentage,
                sps.AveragePR,
                sps.PRWins,
                sps.AverageLuck
            FROM SeriesPlayerStats sps
            JOIN Players p ON sps.PlayerID = p.PlayerID
            WHERE sps.SeriesID = %s
        """
        cursor.execute(query, (series_id,))
        rows = cursor.fetchall()

        if not rows:
            st.subheader("No stats available for this series.")
            return

        formatted_stats = []
        for row in rows:
            try:
                name_nickname = f"{row[0]} ({row[1]})"
                games_played = int(row[2] or 0)
                wins = int(row[3] or 0)
                losses = int(row[4] or 0)
                points = int(row[5] or 0)
                win_pct = float(row[6]) if row[6] is not None else 0.0
                avg_pr = float(row[7]) if row[7] is not None else None
                pr_wins = int(row[8] or 0)
                avg_luck = float(row[9]) if row[9] is not None else None
                points_pct = round((points / (games_played * 3)) * 100, 2) if games_played > 0 else 0.0

                formatted_stats.append([
                    name_nickname, games_played, points, points_pct, wins,
                    pr_wins, losses, win_pct, avg_pr, avg_luck
                ])
            except Exception as e:
                st.warning(f"Skipped row due to error: {e}")

        df = pd.DataFrame(formatted_stats, columns=[
            "Name (Nickname)", "Played", "Points", "Points%", "Wins",
            "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"
        ])

        numeric_cols = ["Played", "Points", "Points%", "Wins", "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

        # ✅ Sort by Points% DESC, Points DESC, Win% DESC, Avg PR ASC
        df = df.sort_values(
            by=["Points%", "Points", "Win%", "Avg PR"],
            ascending=[False, False, False, True]
        ).reset_index(drop=True)

        df.insert(0, "Position", range(1, len(df) + 1))

        styled = df.style.set_properties(
            **{"font-weight": "bold"}, subset=["Position"]
        ).format({
            "Points%": "{:.2f}%",
            "Win%": "{:.2f}%",
            "Avg PR": "{:.2f}",
            "Avg Luck": "{:.2f}"
        })

        st.subheader("🏆 Series Standings (sorted by Points%)")
        st.dataframe(styled, hide_index=True)

    except Exception as e:
        st.error(f"Error displaying series standings: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def fetch_cached_series_standings1(series_id):
    """
    Display standings using precomputed stats from SeriesPlayerStats for the given series.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p.Name,
                p.Nickname,
                sps.GamesPlayed,
                sps.Wins,
                sps.Losses,
                sps.Points,
                sps.WinPercentage,
                sps.AveragePR,
                sps.PRWins,
                sps.AverageLuck
            FROM SeriesPlayerStats sps
            JOIN Players p ON sps.PlayerID = p.PlayerID
            WHERE sps.SeriesID = %s
            ORDER BY sps.Points DESC, sps.WinPercentage DESC, sps.AveragePR ASC
        """
        cursor.execute(query, (series_id,))
        rows = cursor.fetchall()

        if not rows:
            st.subheader("No stats available for this series.")
            return

        formatted_stats = []
        for row in rows:
            try:
                name_nickname = f"{row[0]} ({row[1]})"
                games_played = int(row[2] or 0)
                wins = int(row[3] or 0)
                losses = int(row[4] or 0)
                points = int(row[5] or 0)
                win_pct = float(row[6]) if row[6] is not None else 0.0
                avg_pr = float(row[7]) if row[7] is not None else None
                pr_wins = int(row[8] or 0)
                avg_luck = float(row[9]) if row[9] is not None else None
                points_pct = (points / (games_played * 3)) * 100 if games_played > 0 else 0.0
                
                formatted_stats.append([
                    name_nickname, games_played, points, points_pct, wins, pr_wins, losses, win_pct, avg_pr, avg_luck
                ])
            except Exception as e:
                st.warning(f"Skipped row due to error: {e}")

        df = pd.DataFrame(formatted_stats, columns=[
            "Name (Nickname)", "Played", "Points", "Points%", "Wins", "PR wins", "Losses", "Win%", "Avg PR", "Avg Luck"
        ])
        
        numeric_cols = ["Played", "Points", "Wins", "PR wins", "Losses", "Avg PR", "Avg Luck"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

        df.insert(0, "Position", range(1, len(df) + 1))
        
        styled = df.style.set_properties(
            **{"font-weight": "bold"}, subset=["Position"]
        ).format({
            "Points%": "{:.2f}%",
            "Win%": "{:.2f}%",
            "Avg PR": "{:.2f}",
            "Avg Luck": "{:.2f}"
        })

        st.subheader("Series Standings with Pointsss:")
        st.dataframe(styled, hide_index=True)

    except Exception as e:
        st.error(f"Error displaying series standings: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
            
def display_series_standings_with_points_and_details(series_id):
    """
    Display series standings using cached stats from SeriesPlayerStats.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p.Name, p.Nickname,
                s.GamesPlayed, s.Wins, s.Losses, s.Points,
                s.WinPercentage, s.PRWins, s.AveragePR, s.AverageLuck
            FROM SeriesPlayerStats s
            JOIN Players p ON s.PlayerID = p.PlayerID
            WHERE s.SeriesID = %s
            ORDER BY s.Points DESC, s.Wins DESC, s.AveragePR ASC
        """
        cursor.execute(query, (series_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            st.subheader("No stats available for this series.")
            return

        formatted = []
        for row in rows:
            name_nickname = f"{row[0]} ({row[1]})"
            played = int(row[2] or 0)
            wins = int(row[3] or 0)
            losses = int(row[4] or 0)
            points = int(row[5] or 0)
            win_pct = float(row[6]) if row[6] is not None else 0.0
            pr_wins = int(row[7] or 0)
            avg_pr = float(row[8]) if row[8] is not None else None
            avg_luck = float(row[9]) if row[9] is not None else None
            points_pct = (points / (played * 3)) * 100 if played > 0 else 0.0

            formatted.append([
                name_nickname, played, points, points_pct, wins,
                pr_wins, losses, win_pct, avg_pr, avg_luck
            ])

        df = pd.DataFrame(formatted, columns=[
            "Name (Nickname)", "Played", "Points", "Points%", "Wins",
            "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"
        ])

        numeric_cols = ["Played", "Points", "Points%", "Wins", "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        df.insert(0, "Position", range(1, len(df) + 1))

        styled = df.style.set_properties(
            **{"font-weight": "bold"}, subset=["Position"]
        ).format({
            "Points%": "{:.2f}%",
            "Win%": "{:.2f}%",
            "Avg PR": "{:.2f}",
            "Avg Luck": "{:.2f}"
        })

        st.subheader("Series Standings with Pointsssssssssss:")
        st.dataframe(styled, hide_index=True)

    except Exception as e:
        st.error(f"Error displaying series standings: {e}")

def get_remaining_fixtures_by_series_overview(series_id):
    """
    Retrieves remaining fixtures (Player1 vs Player2) for a specific series.

    Args:
        series_id (int): The ID of the series.

    Returns:
        list: A list of tuples with Player1 and Player2 names.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Step 1: Fetch MatchTypeIDs linked to the SeriesID
        query_match_types = """
        SELECT MatchTypeID
        FROM SeriesMatchTypes
        WHERE SeriesID = %s;
        """
        cursor.execute(query_match_types, (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            return []  # No match types linked to this series

        # Step 2: Query remaining fixtures for the MatchTypeIDs
        query_remaining_fixtures = f"""
        SELECT
            p1.Name AS Player1,
            p2.Name AS Player2
        FROM
            Fixtures f
        LEFT JOIN Players p1 ON f.Player1ID = p1.PlayerID
        LEFT JOIN Players p2 ON f.Player2ID = p2.PlayerID
        WHERE
            f.MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))}) AND f.Completed = 0
        """
        cursor.execute(query_remaining_fixtures, tuple(match_type_ids))
        remaining_fixtures = cursor.fetchall()

        return remaining_fixtures
    except Exception as e:
        st.error(f"Error retrieving remaining fixtures: {e}")
        return []
    finally:
        if conn:
            conn.close()

def display_series_standings_with_points(series_id):
    """
    Fetch and display standings with points for a specific series.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Step 1: Fetch all MatchTypeIDs associated with the given SeriesID
        match_type_query = """
            SELECT MatchTypeID
            FROM SeriesMatchTypes
            WHERE SeriesID = %s;
        """
        cursor.execute(match_type_query, (series_id,))
        match_type_ids = cursor.fetchall()

        if not match_type_ids:
            st.subheader("No match types found for this series.")
            return

        # Flatten the MatchTypeIDs into a tuple for the SQL IN clause
        match_type_ids = tuple(mt[0] for mt in match_type_ids)

        # Step 2: Fetch player stats across all related match types
        standings_query = f"""
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
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS PRWins,
                AVG(CASE 
                        WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
                        WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck
                        ELSE NULL 
                    END) AS AverageLuck,
                (SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1
                        ELSE 0 
                    END) * 2) +
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS Points
            FROM
                Players p
            LEFT JOIN Fixtures f 
                ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
            LEFT JOIN MatchResults mr 
                ON (f.FixtureID = mr.FixtureID AND f.MatchTypeID = mr.MatchTypeID)
            WHERE
                f.MatchTypeID IN {match_type_ids}
            GROUP BY
                p.PlayerID, p.Name, p.Nickname
            ORDER BY
                Points DESC;
        """

        cursor.execute(standings_query)
        player_stats = cursor.fetchall()

        if not player_stats:
            st.subheader("No matches found for this series.")
            return

        # Step 3: Format and display the standings
        formatted_stats = []
        for stat in player_stats:
            try:
                name_with_nickname = f"{stat[1]} ({stat[2]})"
                played = int(stat[3] or 0) + int(stat[4] or 0)  # Wins + Losses
                wins = int(stat[3] or 0)
                losses = int(stat[4] or 0)
                points = int(stat[9] or 0)
                win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
                avg_pr = f"{stat[6]:.2f}" if stat[6] is not None else "-"
                pr_wins = int(stat[7] or 0)
                avg_luck = f"{stat[8]:.2f}" if stat[8] is not None else "-"
                formatted_stats.append([
                    name_with_nickname, played, points, wins, pr_wins, losses, win_percentage, avg_pr, avg_luck
                ])
            except IndexError as ie:
                st.warning(f"Skipping malformed row: {stat}. Error: {ie}")
            except Exception as e:
                st.error(f"Unexpected error while processing data: {e}")

        if formatted_stats:
            df = pd.DataFrame(
                formatted_stats,
                columns=["Name (Nickname)", "Played", "Points", "Wins", "PR wins", "Losses", "Win%", "Averaged PR", "Averaged Luck"]
            )
            st.subheader("Series Standings with Pointsssss:")
            st.dataframe(df)
        else:
            st.subheader("No valid matches to display.")

    except Exception as e:
        st.error(f"Error displaying series standings: {e}")
    finally:
        # Ensure resources are properly closed
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_unique_player_count_by_series(series_id):
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Get MatchTypeIDs linked to the series
        query_match_types = """
        SELECT MatchTypeID
        FROM SeriesMatchTypes
        WHERE SeriesID = %s;
        """
        cursor.execute(query_match_types, (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            return 0  # No match types for this series

        # Step 2: Get Player1ID and Player2ID from Fixtures linked to these MatchTypeIDs
        query_players = f"""
        SELECT DISTINCT Player1ID, Player2ID
        FROM Fixtures
        WHERE MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))});
        """
        cursor.execute(query_players, tuple(match_type_ids))

        # Extract unique player IDs
        players = set()
        for row in cursor.fetchall():
            players.add(row[0])  # Add Player1ID
            players.add(row[1])  # Add Player2ID

        # Exclude None (in case of incomplete data)
        players.discard(None)
        return len(players)  # Return the count of unique players

    except Exception as e:
        print(f"Error fetching player count for series {series_id}: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

def display_matchtype_standings_with_points(match_type_id):
    """
    Fetch and display standings with points for a specific match type.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # SQL Query to fetch player stats
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
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS PRWins,
                AVG(CASE 
                        WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
                        WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck
                        ELSE NULL 
                    END) AS AverageLuck,
                (SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1
                        ELSE 0 
                    END) * 2) +
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS Points
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
                Points DESC, Wins DESC;  -- ADDED WINS DESC FOR TIEBREAKERS
        """
        cursor.execute(query, (match_type_id,))
        player_stats = cursor.fetchall()

        if not player_stats:
            st.subheader("No matches found for this match type.")
            return

        # Prepare formatted stats for display
        formatted_stats = []
        for stat in player_stats:
            try:
                name_with_nickname = f"{stat[1]} ({stat[2]})"
                played = int(stat[3] or 0) + int(stat[4] or 0)  # Wins + Losses
                wins = int(stat[3] or 0)
                losses = int(stat[4] or 0)
                points = int(stat[9] or 0)  # Adjusted for the Points column
                win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
                avg_pr = safe_float(stat[6])  # Uses safe_float function
                pr_wins = int(stat[7] or 0)
                avg_luck = safe_float(stat[8])  # Uses safe_float function
                
                formatted_stats.append([
                    name_with_nickname, played, points, wins, pr_wins, losses, win_percentage, avg_pr, avg_luck
                ])
            except IndexError as ie:
                st.warning(f"Skipping malformed row: {stat}. Error: {ie}")
            except Exception as e:
                st.error(f"Unexpected error while processing data: {e}")

        # Convert to DataFrame for display
        if formatted_stats:
            df = pd.DataFrame(
                formatted_stats,
                columns=["Name (Nickname)", "Played", "Points", "Wins", "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"]
            )
            
            # Customize Table Display
            print(df.dtypes)  # Check data types of all columns
            st.subheader("Standings with Points:")
            st.dataframe(df)
            
            #st.dataframe(df.style.format({
            #    "Win%": "{:.2f}%",
            #    "Avg PR": "{:.2f}",
            #    "Avg Luck": "{:.2f}"
            #}).highlight_max(["Points", "Wins"], color="lightgreen", axis=0))  # Highlight best players

        else:
            st.subheader("No valid matches to display.")

    except Exception as e:
        st.error(f"Error displaying match type standings: {e}")
    finally:
        # Ensure resources are properly closed
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def display_matchtype_standings_withh2h(match_type_id):
    """
    Fetch and display standings with points for a specific match type, applying head-to-head tiebreakers.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Fetch player stats
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
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS PRWins,
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 2
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 2
                        ELSE 0 
                    END) +
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS Points
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
        """
        cursor.execute(query, (match_type_id,))
        player_stats = cursor.fetchall()

        if not player_stats:
            st.subheader("No matches found for this match type.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(
            player_stats,
            columns=["PlayerID", "Name", "Nickname", "Wins", "Losses", "GamesPlayed", "AveragePR", "PRWins", "Points"]
        )

        # Function to calculate head-to-head wins
        def get_head_to_head_wins(player_id, tied_group):
            head_to_head_query = """
                SELECT
                    mr.Player1ID, mr.Player2ID,
                    SUM(CASE WHEN mr.Player1ID = %s AND mr.Player1Points > mr.Player2Points THEN 1 ELSE 0 END) +
                    SUM(CASE WHEN mr.Player2ID = %s AND mr.Player2Points > mr.Player1Points THEN 1 ELSE 0 END) AS HeadToHeadWins
                FROM MatchResults mr
                WHERE (mr.Player1ID IN %s AND mr.Player2ID IN %s)
                    AND mr.MatchTypeID = %s
                GROUP BY mr.Player1ID, mr.Player2ID
            """
            player_ids = tuple(tied_group)
            cursor.execute(head_to_head_query, (player_id, player_id, player_ids, player_ids, match_type_id))
            results = cursor.fetchall()
            return sum(row[2] for row in results) if results else 0

        # Sort players using the multi-level sorting
        df.sort_values(by=["Points", "Wins"], ascending=[False, False], inplace=True)

        # Process head-to-head sorting for tied players
        final_sorted_list = []
        tied_groups = df.groupby(["Points", "Wins"])
        for (points, wins), group in tied_groups:
            if len(group) > 1:
                group["HeadToHeadWins"] = group["PlayerID"].apply(lambda pid: get_head_to_head_wins(pid, group["PlayerID"].tolist()))
                group.sort_values(by=["HeadToHeadWins", "AveragePR"], ascending=[False, True], inplace=True)
            final_sorted_list.append(group)
        df = pd.concat(final_sorted_list)

        # Reset index and add position
        df.insert(0, "Position", range(1, len(df) + 1))
        df.drop(columns=["PlayerID"], inplace=True)

        # Display in Streamlit
        st.dataframe(df)

    except Exception as e:
        st.error(f"Error displaying match type standings: {e}")
    finally:
        cursor.close()
        conn.close()

def display_cached_matchtype_standings(match_type_id):
    """
    Display standings for a match type including players with fixtures but zero matches played.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Fetch players with fixtures in this match type
        query = """
            SELECT 
                p.Name, p.Nickname,
                IFNULL(s.GamesPlayed, 0), IFNULL(s.Wins, 0), IFNULL(s.Losses, 0), IFNULL(s.Points, 0),
                IFNULL(s.WinPercentage, 0), IFNULL(s.PRWins, 0), IFNULL(s.AveragePR, NULL), IFNULL(s.AverageLuck, NULL), IFNULL(s.HeadToHeadScore, 0)
            FROM (
                SELECT DISTINCT p.PlayerID, p.Name, p.Nickname
                FROM Players p
                JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
                WHERE f.MatchTypeID = %s
            ) p
            LEFT JOIN MatchTypePlayerStats s ON s.PlayerID = p.PlayerID AND s.MatchTypeID = %s
            ORDER BY 
                s.Points DESC,
                s.Wins DESC,
                s.PRWins DESC,
                s.HeadToHeadScore DESC,
                s.AveragePR ASC,
                s.GamesPlayed DESC
        """
        cursor.execute(query, (match_type_id, match_type_id))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            st.subheader("No players found for this match type.")
            return

        formatted = []
        for row in rows:
            name_nickname = f"{row[0]} ({row[1]})"
            played = int(row[2] or 0)
            wins = int(row[3] or 0)
            losses = int(row[4] or 0)
            points = int(row[5] or 0)
            win_pct = float(row[6]) if row[6] is not None else 0.0
            pr_wins = int(row[7] or 0)
            avg_pr = float(row[8]) if row[8] is not None else None
            avg_luck = float(row[9]) if row[9] is not None else None
            h2h_score = int(row[10] or 0)
            points_pct = (points / (played * 3)) * 100 if played > 0 else 0.0

            formatted.append([
                name_nickname, played, points, points_pct, wins,
                pr_wins, h2h_score, losses, win_pct, avg_pr, avg_luck
            ])

        df = pd.DataFrame(formatted, columns=[
            "Name (Nickname)", "Played", "Points", "Points%", "Wins",
            "PR Wins", "H2H Score", "Losses", "Win%", "Avg PR", "Avg Luck"
        ])

        numeric_cols = [
            "Played", "Points", "Points%", "Wins", "PR Wins",
            "H2H Score", "Losses", "Win%", "Avg PR", "Avg Luck"
        ]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        df.insert(0, "Position", range(1, len(df) + 1))

        styled = df.style.set_properties(
            **{"font-weight": "bold"}, subset=["Position"]
        ).format({
            "Points%": "{:.2f}%",
            "Win%": "{:.2f}%",
            "Avg PR": "{:.2f}",
            "Avg Luck": "{:.2f}"
        })

        st.subheader("League Standings:")
        st.dataframe(styled, hide_index=True)

    except Exception as e:
        st.error(f"Error loading standings: {e}")

def display_cached_matchtype_standings1(match_type_id):
    """
    Display standings using precomputed data from MatchTypePlayerStats,
    sorting by Points DESC, Wins DESC, PR Wins DESC, HeadToHeadScore DESC, AveragePR ASC.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p.Name, p.Nickname,
                s.GamesPlayed, s.Wins, s.Losses, s.Points,
                s.WinPercentage, s.PRWins, s.AveragePR, s.AverageLuck, s.HeadToHeadScore
            FROM MatchTypePlayerStats s
            JOIN Players p ON s.PlayerID = p.PlayerID
            WHERE s.MatchTypeID = %s
            ORDER BY 
                s.Points DESC,
                s.Wins DESC,
                s.PRWins DESC,
                s.HeadToHeadScore DESC,
                s.AveragePR ASC
        """
        cursor.execute(query, (match_type_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            st.subheader("No cached stats available for this match type.")
            return

        formatted = []
        for row in rows:
            name_nickname = f"{row[0]} ({row[1]})"
            played = int(row[2] or 0)
            wins = int(row[3] or 0)
            losses = int(row[4] or 0)
            points = int(row[5] or 0)
            win_pct = float(row[6]) if row[6] is not None else 0.0
            pr_wins = int(row[7] or 0)
            avg_pr = float(row[8]) if row[8] is not None else None
            avg_luck = float(row[9]) if row[9] is not None else None
            h2h_score = int(row[10] or 0)
            points_pct = (points / (played * 3)) * 100 if played > 0 else 0.0

            formatted.append([
                name_nickname, played, points, points_pct, wins,
                pr_wins, h2h_score, losses, win_pct, avg_pr, avg_luck
            ])

        df = pd.DataFrame(formatted, columns=[
            "Name (Nickname)", "Played", "Points", "Points%", "Wins",
            "PR Wins", "H2H Score", "Losses", "Win%", "Avg PR", "Avg Luck"
        ])

        numeric_cols = [
            "Played", "Points", "Points%", "Wins", "PR Wins",
            "H2H Score", "Losses", "Win%", "Avg PR", "Avg Luck"
        ]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        df.insert(0, "Position", range(1, len(df) + 1))

        styled = df.style.set_properties(
            **{"font-weight": "bold"}, subset=["Position"]
        ).format({
            "Points%": "{:.2f}%",
            "Win%": "{:.2f}%",
            "Avg PR": "{:.2f}",
            "Avg Luck": "{:.2f}"
        })

        st.subheader("League Standings:")
        st.dataframe(styled, hide_index=True)

    except Exception as e:
        st.error(f"Error loading cached standings: {e}")

def display_cached_matchtype_standings2(match_type_id):
    """
    Display standings using precomputed data from MatchTypePlayerStats,
    with proper multi-level sorting: Points, Wins, PRWins, HeadToHeadScore, AveragePR.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p.Name, p.Nickname,
                s.GamesPlayed, s.Wins, s.Losses, s.Points,
                s.WinPercentage, s.PRWins, s.AveragePR, s.AverageLuck,
                s.HeadToHeadScore
            FROM MatchTypePlayerStats s
            JOIN Players p ON s.PlayerID = p.PlayerID
            WHERE s.MatchTypeID = %s
        """
        cursor.execute(query, (match_type_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            st.subheader("No cached stats available for this match type.")
            return

        formatted = []
        for row in rows:
            name_nickname = f"{row[0]} ({row[1]})"
            played = int(row[2] or 0)
            wins = int(row[3] or 0)
            losses = int(row[4] or 0)
            points = int(row[5] or 0)
            win_pct = float(row[6]) if row[6] is not None else 0.0
            pr_wins = int(row[7] or 0)
            avg_pr = float(row[8]) if row[8] is not None else 0.0
            avg_luck = float(row[9]) if row[9] is not None else 0.0
            head_to_head = int(row[10] or 0)
            points_pct = (points / (played * 3)) * 100 if played > 0 else 0.0

            formatted.append([
                name_nickname, played, points, points_pct, wins,
                pr_wins, head_to_head, losses, win_pct, avg_pr, avg_luck
            ])

        df = pd.DataFrame(formatted, columns=[
            "Name (Nickname)", "Played", "Points", "Points%", "Wins",
            "PR Wins", "HeadToHead", "Losses", "Win%", "Avg PR", "Avg Luck"
        ])

        # Ensure numeric types for sorting
        numeric_cols = ["Played", "Points", "Points%", "Wins", "PR Wins", "HeadToHead", "Losses", "Win%", "Avg PR", "Avg Luck"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        # Sort by desired tie-break order
        df.sort_values(
            by=["Points", "Wins", "PR Wins", "HeadToHead", "Avg PR"],
            ascending=[False, False, False, False, True],
            inplace=True
        )

        # Add Position
        df.insert(0, "Position", range(1, len(df) + 1))

        # Drop HeadToHead from display if not desired for end users
        df_display = df.drop(columns=["HeadToHead"])

        styled = df_display.style.set_properties(
            **{"font-weight": "bold"}, subset=["Position"]
        ).format({
            "Points%": "{:.2f}%",
            "Win%": "{:.2f}%",
            "Avg PR": "{:.2f}",
            "Avg Luck": "{:.2f}"
        })

        st.subheader("League Standings:")
        st.dataframe(styled, hide_index=True)

    except Exception as e:
        st.error(f"Error loading cached standings: {e}")

def display_cached_matchtype_standings4(match_type_id):
    """
    Display standings using precomputed data from MatchTypePlayerStats.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p.Name, p.Nickname,
                s.GamesPlayed, s.Wins, s.Losses, s.Points,
                s.WinPercentage, s.PRWins, s.AveragePR, s.AverageLuck
            FROM MatchTypePlayerStats s
            JOIN Players p ON s.PlayerID = p.PlayerID
            WHERE s.MatchTypeID = %s
            ORDER BY s.Points DESC, s.Wins DESC, s.AveragePR ASC
        """
        cursor.execute(query, (match_type_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            st.subheader("No cached stats available for this match type.")
            return

        formatted = []
        for row in rows:
            name_nickname = f"{row[0]} ({row[1]})"
            played = int(row[2] or 0)
            wins = int(row[3] or 0)
            losses = int(row[4] or 0)
            points = int(row[5] or 0)
            win_pct = float(row[6]) if row[6] is not None else 0.0
            pr_wins = int(row[7] or 0)
            avg_pr = float(row[8]) if row[8] is not None else None
            avg_luck = float(row[9]) if row[9] is not None else None
            points_pct = (points / (played * 3)) * 100 if played > 0 else 0.0

            formatted.append([
                name_nickname, played, points, points_pct, wins,
                pr_wins, losses, win_pct, avg_pr, avg_luck
            ])

        df = pd.DataFrame(formatted, columns=[
            "Name (Nickname)", "Played", "Points", "Points%", "Wins",
            "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"
        ])

        numeric_cols = ["Played", "Points", "Points%", "Wins", "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

        df.insert(0, "Position", range(1, len(df) + 1))

        styled = df.style.set_properties(
            **{"font-weight": "bold"}, subset=["Position"]
        ).format({
            "Points%": "{:.2f}%",
            "Win%": "{:.2f}%",
            "Avg PR": "{:.2f}",
            "Avg Luck": "{:.2f}"
        })

        st.subheader("League Standings:")
        st.dataframe(styled, hide_index=True)

    except Exception as e:
        st.error(f"Error loading cached standings: {e}")

def display_matchtype_standings_full_details_styled(match_type_id):
    """
    Fetch and display standings with points for a specific match type.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # SQL Query to fetch player stats
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
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS PRWins,
                AVG(CASE 
                        WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
                        WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck
                        ELSE NULL 
                    END) AS AverageLuck,
                (SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1
                        ELSE 0 
                    END) * 2) +
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS Points
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
                Points DESC, Wins DESC;  -- ADDED WINS DESC FOR TIEBREAKERS
        """
        cursor.execute(query, (match_type_id,))
        player_stats = cursor.fetchall()

        if not player_stats:
            st.subheader("No matches found for this match type.")
            return

        # Prepare formatted stats for display
        formatted_stats = []
        for stat in player_stats:
            try:
                name_with_nickname = f"{stat[1]} ({stat[2]})"
                played = int(stat[3] or 0) + int(stat[4] or 0)  # Wins + Losses
                wins = int(stat[3] or 0)
                losses = int(stat[4] or 0)
                points = int(stat[9] or 0)
                points_percentage = f"{(points/(played * 3)) * 100:.2f}%" if played > 0 else "0.00%"
                # Adjusted for the Points column
                win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
                avg_pr = safe_float(stat[6])  # Uses safe_float function
                pr_wins = int(stat[7] or 0)
                avg_luck = safe_float(stat[8])  # Uses safe_float function
                
                formatted_stats.append([
                    name_with_nickname, played, points, points_percentage, wins, pr_wins, losses, win_percentage, avg_pr, avg_luck
                ])
            except IndexError as ie:
                st.warning(f"Skipping malformed row: {stat}. Error: {ie}")
            except Exception as e:
                st.error(f"Unexpected error while processing data: {e}")

        # Convert to DataFrame for display
        if formatted_stats:
            df = pd.DataFrame(
                formatted_stats,
                columns=["Name (Nickname)", "Played", "Points", "Points%", "Wins", "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"]
            )

            # Convert numerical columns to appropriate types
            df["Avg PR"] = pd.to_numeric(df["Avg PR"], errors="coerce")
            df["Avg Luck"] = pd.to_numeric(df["Avg Luck"], errors="coerce")
            df["Played"] = pd.to_numeric(df["Played"], errors="coerce")
            df["Points"] = pd.to_numeric(df["Points"], errors="coerce")
            df["Wins"] = pd.to_numeric(df["Wins"], errors="coerce")
            df["PR Wins"] = pd.to_numeric(df["PR Wins"], errors="coerce")
            df["Losses"] = pd.to_numeric(df["Losses"], errors="coerce")

            # Add a Position column (1-based index)
            df.insert(0, "Position", range(1, len(df) + 1))

            styled_df = df.style.set_properties(
                **{"font-weight": "bold"}, subset=["Position"]
            ).format(
                {"Avg PR": "{:.2f}", "Avg Luck": "{:.2f}"}  # Example formatting
            )
            
            #Display DataFrame
            if not df.empty:
                st.dataframe(df,hide_index=True)
            else:
                st.subheader("No completed matches found.")
            
            #st.dataframe(df.style.format({
            #    "Win%": "{:.2f}%",
            #    "Avg PR": "{:.2f}",
            #    "Avg Luck": "{:.2f}"
            #}).highlight_max(["Points", "Wins"], color="lightgreen", axis=0))  # Highlight best players

        else:
            st.subheader("No valid matches to display.")

    except Exception as e:
        st.error(f"Error displaying match type standings: {e}")
    finally:
        # Ensure resources are properly closed
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
def display_matchtype_standings_with_points_and_details(match_type_id):
    """
    Fetch and display standings with points for a specific match type.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # SQL Query to fetch player stats
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
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS PRWins,
                AVG(CASE 
                        WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
                        WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck
                        ELSE NULL 
                    END) AS AverageLuck,
                (SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1
                        ELSE 0 
                    END) * 2) +
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS Points
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
                Points DESC, Wins DESC;  -- ADDED WINS DESC FOR TIEBREAKERS
        """
        cursor.execute(query, (match_type_id,))
        player_stats = cursor.fetchall()

        if not player_stats:
            st.subheader("No matches found for this match type.")
            return

        # Prepare formatted stats for display
        formatted_stats = []
        for stat in player_stats:
            try:
                name_with_nickname = f"{stat[1]} ({stat[2]})"
                played = int(stat[3] or 0) + int(stat[4] or 0)  # Wins + Losses
                wins = int(stat[3] or 0)
                losses = int(stat[4] or 0)
                points = int(stat[9] or 0)
                points_percentage = f"{(points/(played * 3)) * 100:.2f}%" if played > 0 else "0.00%"
                # Adjusted for the Points column
                win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
                avg_pr = safe_float(stat[6])  # Uses safe_float function
                pr_wins = int(stat[7] or 0)
                avg_luck = safe_float(stat[8])  # Uses safe_float function
                
                formatted_stats.append([
                    name_with_nickname, played, points, points_percentage, wins, pr_wins, losses, win_percentage, avg_pr, avg_luck
                ])
            except IndexError as ie:
                st.warning(f"Skipping malformed row: {stat}. Error: {ie}")
            except Exception as e:
                st.error(f"Unexpected error while processing data: {e}")

        # Convert to DataFrame for display
        if formatted_stats:
            df = pd.DataFrame(
                formatted_stats,
                columns=["Name (Nickname)", "Played", "Points", "Points%", "Wins", "PR Wins", "Losses", "Win%", "Avg PR", "Avg Luck"]
            )
            
            # Customize Table Display
            print(df.dtypes)  # Check data types of all columns
            st.subheader("Standings with Points:")
            with st.spinner("Loading table..."):
                st.dataframe(df)
            
            #st.dataframe(df.style.format({
            #    "Win%": "{:.2f}%",
            #    "Avg PR": "{:.2f}",
            #    "Avg Luck": "{:.2f}"
            #}).highlight_max(["Points", "Wins"], color="lightgreen", axis=0))  # Highlight best players

        else:
            st.subheader("No valid matches to display.")

    except Exception as e:
        st.error(f"Error displaying match type standings: {e}")
    finally:
        # Ensure resources are properly closed
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def display_matchtype_standings_with_points_bold(match_type_id):
    """
    Fetch and display standings with points for a specific match type, highlighting the Points column and bolding the lower PR in each row.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # SQL Query to fetch player stats
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
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS PRWins,
                AVG(CASE 
                        WHEN mr.Player1ID = p.PlayerID THEN mr.Player1Luck
                        WHEN mr.Player2ID = p.PlayerID THEN mr.Player2Luck
                        ELSE NULL 
                    END) AS AverageLuck,
                (SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN 1
                        ELSE 0 
                    END) * 2) +
                SUM(CASE 
                        WHEN mr.Player1ID = p.PlayerID AND mr.Player1PR < mr.Player2PR THEN 1
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2PR < mr.Player1PR THEN 1
                        ELSE 0 
                    END) AS Points
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
                Points DESC;
        """
        cursor.execute(query, (match_type_id,))
        player_stats = cursor.fetchall()

        if not player_stats:
            st.subheader("No matches found for this match type.")
            return

        # Prepare formatted stats for display
        formatted_stats = []
        for stat in player_stats:
            try:
                name_with_nickname = f"{stat[1]} ({stat[2]})"
                played = int(stat[3] or 0) + int(stat[4] or 0)  # Wins + Losses
                wins = int(stat[3] or 0)
                losses = int(stat[4] or 0)
                points = int(stat[9] or 0)  # Adjusted for the Points column
                win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
                avg_pr = stat[6] if stat[6] is not None else float('inf')  # Averaged PR
                pr_wins = int(stat[7] or 0)
                avg_luck = f"{stat[8]:.2f}" if stat[8] is not None else "-"
                formatted_stats.append([
                    name_with_nickname, played, points, wins, losses, win_percentage, avg_pr, pr_wins, avg_luck
                ])
            except Exception as e:
                st.warning(f"Error processing row: {e}")

        # Convert to DataFrame for display
        if formatted_stats:
            df = pd.DataFrame(
                formatted_stats,
                columns=["Name (Nickname)", "Played", "Points", "Wins", "Losses", "Win%", "Averaged PR", "PR Wins", "Averaged Luck"]
            )

            # Apply custom styling
            def style_dataframe(row):
                styles = []
                for col in df.columns:
                    if col == "Points":
                        styles.append("font-weight: bold;")
                    elif col == "Averaged PR":
                        styles.append("font-weight: bold;" if row["Averaged PR"] == min(row["Averaged PR"]) else "")
                    else:
                        styles.append("")
                return styles

            st.dataframe(df.style.applymap(style_dataframe))
        else:
            st.subheader("No valid matches to display.")

    except Exception as e:
        st.error(f"Error displaying match type standings: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def display_series_with_points(series_id):
    # Connect to the database
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Query data for the series
        query = """
        SELECT 
            mr.Date,
            p1.Name AS Player1Name, 
            p2.Name AS Player2Name, 
            mr.Player1Points, 
            mr.Player2Points, 
            mr.Player1PR, 
            mr.Player2PR, 
            p1.PlayerID AS Player1ID,
            p2.PlayerID AS Player2ID
        FROM MatchResults mr
        JOIN Fixtures f ON mr.FixtureID = f.FixtureID
        JOIN MatchType mt ON f.MatchTypeID = mt.MatchTypeID
        JOIN SeriesMatchTypes smt ON mt.MatchTypeID = smt.MatchTypeID
        JOIN Players p1 ON mr.Player1ID = p1.PlayerID
        JOIN Players p2 ON mr.Player2ID = p2.PlayerID
        WHERE smt.SeriesID = %s
        ORDER BY mr.Date DESC;

        """
        cursor.execute(query, (series_id,))
        results = cursor.fetchall()

        if not results:
            st.warning("No matches found for this series.")
            return

        # Calculate points for each player
        player_points = {}
        data = []
        for row in results:
            match_date, player1_name, player2_name, p1_points, p2_points, p1_pr, p2_pr, p1_id, p2_id = row
            
            # Determine the winner
            if p1_points > p2_points:
                winner_id, loser_id = p1_id, p2_id
                winner_name, loser_name = player1_name, player2_name
                winner_pr, loser_pr = p1_pr, p2_pr
            else:
                winner_id, loser_id = p2_id, p1_id
                winner_name, loser_name = player2_name, player1_name
                winner_pr, loser_pr = p2_pr, p1_pr

            # Assign points
            player_points[winner_id] = player_points.get(winner_id, 0) + 2  # Winner gets 2 points
            if winner_pr < loser_pr:
                player_points[winner_id] += 1  # Bonus for lower PR
            if loser_pr < winner_pr:
                player_points[loser_id] = player_points.get(loser_id, 0) + 1  # Loser gets 1 point for lower PR

            # Add match details to data
            data.append([match_date, player1_name, player2_name, p1_points, p2_points, winner_name, loser_name])

        # Create DataFrame with points
        points_data = []
        for player_id, points in player_points.items():
            points_data.append([player_id, points])

        # Display results
        df = pd.DataFrame(data, columns=[
            "Date", "Player 1", "Player 2", "Player 1 Points", "Player 2 Points", "Winner", "Loser"
        ])
        points_df = pd.DataFrame(points_data, columns=["Player ID", "Points"])

        st.subheader("Match Details with Points")
        st.dataframe(df)
        st.subheader("Player Points")
        st.dataframe(points_df)
    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        conn.close()

def get_matchcount_by_date_and_matchtype(matchdate, match_type_id):
    """
    Returns the count of matches completed on a specific date for a given match type.
    
    Args:
        matchdate (str): The date to filter matches (in 'YYYY-MM-DD' format).
        match_type_id (int): The MatchTypeID to filter by.
    
    Returns:
        int: Number of matches completed on the specified date for the given match type.
    """
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # SQL query to count matches for the given date and match type
        query = """
        SELECT COUNT(*)
        FROM MatchResults
        JOIN Fixtures ON MatchResults.FixtureID = Fixtures.FixtureID
        WHERE MatchResults.Date = %s AND Fixtures.MatchTypeID = %s;
        """
        cursor.execute(query, (matchdate, match_type_id))
        result = cursor.fetchone()

        return result[0] if result else 0
    finally:
        cursor.close()
        conn.close()

def get_matchcount_by_date_and_series(matchdate, series_id):
    """
    Returns the count of matches completed on a specific date for a given series.
    
    Args:
        matchdate (str): The date to filter matches (in 'YYYY-MM-DD' format).
        series_id (int): The SeriesID to filter by.
    
    Returns:
        int: Number of matches completed on the specified date for the given series.
    """
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Fetch MatchTypeIDs linked to the given series
        query_match_types = """
        SELECT MatchTypeID
        FROM SeriesMatchTypes
        WHERE SeriesID = %s;
        """
        cursor.execute(query_match_types, (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            return 0  # No match types linked to this series

        # Step 2: Count matches for the given date and match types
        query_count_matches = f"""
        SELECT COUNT(*)
        FROM MatchResults
        JOIN Fixtures ON MatchResults.FixtureID = Fixtures.FixtureID
        WHERE MatchResults.Date = %s AND Fixtures.MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))});
        """
        cursor.execute(query_count_matches, (matchdate, *match_type_ids))
        result = cursor.fetchone()

        return result[0] if result else 0
    finally:
        cursor.close()
        conn.close()

def get_matchcount_by_date(matchdate):
    conn = create_connection()
    cursor = conn.cursor()

    try:
     # SQL query to count matches for the given date
        query = "SELECT COUNT(*) FROM MatchResults WHERE Date = %s;"
        cursor.execute(query, (matchdate,))
        result = cursor.fetchone()  # Fetch the single result (COUNT)

        return result[0] if result else 0

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return 0

    finally:
        cursor.close()
        conn.close()

def get_matchcount_by_matchtype(matchtype_id):
    """
    Returns the count of completed matches for a specific match type.
    
    Args:
        matchtype_id (int): The ID of the match type.
    
    Returns:
        int: Number of completed matches.
    """
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Query to count completed matches for the given MatchTypeID
        query = """
        SELECT COUNT(*)
        FROM Fixtures
        WHERE MatchTypeID = %s
          AND Completed = 1;
        """
        cursor.execute(query, (matchtype_id,))
        result = cursor.fetchone()

        return result[0] if result else 0
    finally:
        cursor.close()
        conn.close()

def get_matchcount_by_series(series_id):
    """
    Returns the count of completed matches for a specific series.
    
    Args:
        series_id (int): The ID of the series.
    
    Returns:
        int: Number of completed matches.
    """
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Fetch MatchTypeIDs associated with the series
        query_match_types = """
        SELECT MatchTypeID
        FROM SeriesMatchTypes
        WHERE SeriesID = %s;
        """
        cursor.execute(query_match_types, (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            return 0  # No match types linked to this series

        # Step 2: Count completed matches for those MatchTypeIDs
        query_count_matches = f"""
        SELECT COUNT(*)
        FROM Fixtures
        WHERE MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))})
          AND Completed = 1;
        """
        cursor.execute(query_count_matches, tuple(match_type_ids))
        result = cursor.fetchone()

        return result[0] if result else 0
    finally:
        cursor.close()
        conn.close()

def get_fixturescount_by_matchtype(matchtype_id):
    """
    Returns the count of matches for a specific match type.
    
    Args:
        matchtype_id (int): The ID of the match type.
    
    Returns:
        int: Number of matches.
    """
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Query to count fixtures for the given MatchTypeID
        query = """
        SELECT COUNT(*)
        FROM Fixtures
        WHERE MatchTypeID = %s;
        """
        cursor.execute(query, (matchtype_id,))
        result = cursor.fetchone()

        return result[0] if result else 0
    finally:
        cursor.close()
        conn.close()

def get_averagePR_by_matchtype(matchtype_id):
    """
    Retrieves the average PR (Performance Rating) for a given match type, rounded to 2 decimal places.
    """
    query = """
        SELECT AVG((Player1PR + Player2PR) / 2) 
        FROM MatchResults 
        WHERE MatchTypeID = %s;
    """
    try:
        conn = create_connection()  # Ensure you have a valid database connection
        with conn.cursor() as cursor:
            cursor.execute(query, (matchtype_id,))
            result = cursor.fetchone()
        conn.close()

        return round(result[0], 2) if result and result[0] is not None else 0.00  # Return 0.00 if no matches found

    except Exception as e:
        st.error(f"Error retrieving average PR: {e}")
        return None


    
def get_fixturescount_by_series(series_id): 
    """
    Returns the count of matches for a specific series.
    
    Args:
        series_id (int): The ID of the series.
    
    Returns:
        int: Number of matches.
    """
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Fetch MatchTypeIDs associated with the series
        query_match_types = """
        SELECT MatchTypeID
        FROM SeriesMatchTypes
        WHERE SeriesID = %s;
        """
        cursor.execute(query_match_types, (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            return 0  # No match types linked to this series

        # Step 2: Count matches for those MatchTypeIDs
        query_count_matches = f"""
        SELECT COUNT(*)
        FROM Fixtures
        WHERE MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))});
        """
        cursor.execute(query_count_matches, tuple(match_type_ids))
        result = cursor.fetchone()

        return result[0] if result else 0
    finally:
        cursor.close()
        conn.close()

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

def get_remaining_fixtures_by_series(series_id):
    """
    Retrieves remaining fixtures (Player1 vs Player2) for a specific series.

    Args:
        series_id (int): The ID of the series.

    Returns:
        list: A list of tuples with Player1 and Player2 names.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Step 1: Fetch MatchTypeIDs linked to the SeriesID
        query_match_types = """
        SELECT MatchTypeID
        FROM SeriesMatchTypes
        WHERE SeriesID = %s;
        """
        cursor.execute(query_match_types, (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            return []  # No match types linked to this series

        # Step 2: Query remaining fixtures for the MatchTypeIDs
        query_remaining_fixtures = f"""
        SELECT
            p1.Name AS Player1,
            p2.Name AS Player2
        FROM
            Fixtures f
        LEFT JOIN Players p1 ON f.Player1ID = p1.PlayerID
        LEFT JOIN Players p2 ON f.Player2ID = p2.PlayerID
        WHERE
            f.MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))}) AND f.Completed = 0
        """
        cursor.execute(query_remaining_fixtures, tuple(match_type_ids))
        remaining_fixtures = cursor.fetchall()
        
        return remaining_fixtures
    except Exception as e:
        st.error(f"Error retrieving remaining fixtures: {e}")
        return []
    finally:
        conn.close()

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
    #st.write(match_results)
    if match_results:
        # Create a list of unique player names
        player_names = set()
        for result in match_results:
            player_names.add(result[1])  # Player 1 Name
            player_names.add(result[3])  # Player 2 Name
            #st.write(f"Processing match 1 dmg: {player1_name} vs {player2_name}, {player1_points}-{player2_points}")

        # Sort player names for consistent order
        player_names = sorted(player_names)

        # Initialize an empty DataFrame with player names as both rows and columns
        score_df = pd.DataFrame(
            "–",  # Default value
            index=player_names,  # Scoring players
            columns=player_names  # Opponent players
        )

        # Populate the DataFrame with match results
        for result in match_results:
            player1_name = result[1]
            player2_name = result[3]
            player1_points = result[4]  # Points scored by Player 1
            player2_points = result[5]  # Points scored by Player 2

            # Set points in the DataFrame
            if player1_points is not None:
                score_df.loc[player2_name, player1_name] = str(player1_points)  # Player 1 scored against Player 2
            if player2_points is not None:
                score_df.loc[player1_name, player2_name] = str(player2_points)  # Player 2 scored against Player 1

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


def display_match_gridddd(match_type_id):
    # Fetch match results for the specified match type
    match_results = get_match_results_for_grid(match_type_id)
    if match_results:
        # Create a list of unique player names
        player_names = set()
        for result in match_results:
            player_names.add(result[1])  # Player 1 Name
            player_names.add(result[3])  # Player 2 Name

        # Sort player names for consistent order
        player_names = sorted(player_names)

        # Initialize an empty DataFrame with player names as both rows and columns
        score_df = pd.DataFrame(
            "–",  # Default value
            index=player_names,  # Scoring players
            columns=player_names  # Opponent players
        )

        # Populate the DataFrame with match results
        for result in match_results:
            player1_name = result[1]
            player2_name = result[3]
            player1_points = result[4]  # Points scored by Player 1
            player2_points = result[5]  # Points scored by Player 2

            if player1_points is not None:
                score_df.at[player2_name, player1_name] = str(player1_points)  # Points Player 1 scored against Player 2
            if player2_points is not None:
                score_df.at[player1_name, player2_name] = str(player2_points)  # Points Player 2 scored against Player 1

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

def display_match_gridd(match_type_id):
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

def list_remaining_fixtures_by_series(series_id):
    # Fetch remaining fixtures for the selected series
    remaining_fixtures = get_remaining_fixtures_by_series(series_id)
    if remaining_fixtures:
        st.subheader("Remaining Fixtures in Series:")
        for fixture in remaining_fixtures:
            player1, player2 = fixture
            st.write(f"- **{player1}** vs **{player2}**")
    else:
        st.write("No remaining fixtures in this series.")

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

def display_sorting_series_table(series_id):
    player_stats = get_player_stats_by_series(series_id)  
    if player_stats:
        formatted_stats = []
        for stat in player_stats:
            name_with_nickname = f"{stat[1]} ({stat[2]})"
            wins = int(stat[3] or 0)  # Ensure it's an integer
            losses = int(stat[4] or 0)  # Ensure it's an integer
            played = wins + losses
            win_percentage = f"{(wins / played) * 100:.2f}%" if played > 0 else "0.00%"
            avg_pr = f"{stat[6]:.2f}" if stat[6] is not None else "-"  
            avg_luck = f"{stat[7]:.2f}" if stat[7] is not None else "-"
            formatted_stats.append([name_with_nickname, avg_pr, played, wins, losses, win_percentage, avg_luck])  
        
        # Add the ranking column
        df = pd.DataFrame(
            formatted_stats, 
            columns=["Name (Nickname)", "Average PR", "Played", "Wins", "Losses", "Win%", "Average Luck"]
        )
        df.insert(0, "Ranking", range(1, len(df) + 1))  # Insert a ranking column at the start

        # Display the DataFrame as a table
        st.dataframe(df, hide_index=True)

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

def smccc(series_id):
    # Connect to the database
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Step 1: Fetch MatchTypeIDs linked to the Series_ID
        query_match_types = """
        SELECT MatchTypeID
        FROM SeriesMatchTypes
        WHERE SeriesID = %s;
        """
        cursor.execute(query_match_types, (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            st.warning("No match types found for the given series.")
            return

        # Step 2: Query completed matches for the MatchTypeIDs
        query_matches = f"""
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
            MatchResults.Player2Luck AS Player2Luck,
            MT.MatchTypeTitle AS MTTitle
        FROM MatchResults
        JOIN Fixtures ON MatchResults.FixtureID = Fixtures.FixtureID
        JOIN Players p1 ON MatchResults.Player1ID = p1.PlayerID
        JOIN Players p2 ON MatchResults.Player2ID = p2.PlayerID
        JOIN MatchType MT ON MT.MatchTypeID = Fixtures.MatchTypeID
        WHERE Fixtures.MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))})
          AND Fixtures.Completed = 1
        ORDER BY MatchResults.Date DESC, MatchResults.MatchResultID DESC;
        """
        cursor.execute(query_matches, tuple(match_type_ids))
        results = cursor.fetchall()

        if not results:
            st.warning("No completed matches found for this series.")
            return

        # Step 3: Prepare data for display
        data = []
        for row in results:
            match_date = row[0].strftime("%Y-%m-%d")
            player1_points, player2_points = row[5], row[6]
            player1_pr, player2_pr = row[7], row[9]
            player1_luck, player2_luck = row[8], row[10]
            match_type_title = row[11]

            # Determine winner and loser
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
                    match_type_title,
                    f"{winner_info} beat {loser_info}",
                    score,
                    f"{winner_pr:.2f}" if winner_pr is not None else "-",
                    f"{winner_luck:.2f}" if winner_luck is not None else "-",
                    f"{loser_pr:.2f}" if loser_pr is not None else "-",
                    f"{loser_luck:.2f}" if loser_luck is not None else "-",
                ]
            )

        # Step 4: Display results
        df = pd.DataFrame(data, columns=[
            "Date Completed", "Match Type", "Result", "Score", 
            "Winner PR", "Winner Luck", "Loser PR", "Loser Luck"
        ])

        if not df.empty:
            # Convert PR and Luck columns to float for proper sorting
            df[["Winner PR", "Winner Luck", "Loser PR", "Loser Luck"]] = df[["Winner PR", "Winner Luck", "Loser PR", "Loser Luck"]].astype(float)

            st.subheader("Completed Matches:")
            st.dataframe(df.set_index("Date Completed"))
        else:
            st.subheader("No completed matches found.")
    except Exception as e:
        st.error(f"Error fetching matches for series: {e}")
    finally:
        if conn:
            conn.close()

def get_series_completed_matches_detailed(series_id, player_id=None):
    """
    Loads and displays completed matches from CompletedMatchesCache for the series.
    If player_id is provided, adjusts columns to show that player's perspective.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                Date,
                MatchTypeTitle,
                Player1Name,
                Player2Name,
                Player1Points,
                Player2Points,
                Player1PR,
                Player1Luck,
                Player2PR,
                Player2Luck
            FROM CompletedMatchesCache
            WHERE SeriesID = %s
            ORDER BY Date DESC, TimeCompleted DESC
        """, (series_id,))
        results = cursor.fetchall()

        if not results:
            st.info("No completed matches recorded yet for this series.")
            return

        data = []
        for row in results:
            (
                match_date, match_type_title,
                p1_name, p2_name,
                p1_points, p2_points,
                p1_pr, p1_luck, p2_pr, p2_luck
            ) = row

            match_date = match_date.strftime("%Y-%m-%d") if match_date else "?"

            # Determine winner/loser and perspective if player_id provided
            if p1_points > p2_points:
                winner = p1_name
                loser = p2_name
                winner_pts = p1_points
                loser_pts = p2_points
                winner_pr = p1_pr
                winner_luck = p1_luck
                loser_pr = p2_pr
                loser_luck = p2_luck
            else:
                winner = p2_name
                loser = p1_name
                winner_pts = p2_points
                loser_pts = p1_points
                winner_pr = p2_pr
                winner_luck = p2_luck
                loser_pr = p1_pr
                loser_luck = p1_luck

            # If player perspective is needed
            if player_id:
                if winner == player_id:
                    result = "Won"
                    opponent = loser
                    player_pr_display = f"{winner_pr:.2f}" if winner_pr is not None else "-"
                    player_luck_display = f"{winner_luck:.2f}" if winner_luck is not None else "-"
                else:
                    result = "Lost"
                    opponent = winner
                    player_pr_display = f"{loser_pr:.2f}" if loser_pr is not None else "-"
                    player_luck_display = f"{loser_luck:.2f}" if loser_luck is not None else "-"
                score_display = f"11-{loser_pts}"
                data.append([
                    match_date, match_type_title, result, opponent,
                    score_display, player_pr_display, player_luck_display
                ])
            else:
                # General view
                result_line = f"{winner} beat {loser}"
                score_display = f"{winner_pts}-{loser_pts}"
                data.append([
                    match_date, match_type_title, result_line, score_display,
                    f"{winner_pr:.2f}" if winner_pr is not None else "-",
                    f"{winner_luck:.2f}" if winner_luck is not None else "-",
                    f"{loser_pr:.2f}" if loser_pr is not None else "-",
                    f"{loser_luck:.2f}" if loser_luck is not None else "-"
                ])

        if player_id:
            df = pd.DataFrame(data, columns=[
                "Date", "Match Type", "Result", "Opponent",
                "Score", "PR", "Luck"
            ])
        else:
            df = pd.DataFrame(data, columns=[
                "Date", "Match Type", "Result", "Score",
                "Winner PR", "Winner Luck", "Loser PR", "Loser Luck"
            ])

        st.subheader("✅ Completed Matches")
        st.dataframe(df, hide_index=True)

    except Exception as e:
        st.error(f"Error loading completed matches: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_series_completed_matches_detailed1(series_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                Date,
                MatchTypeTitle,
                Player1Name,
                Player2Name,
                Player1Points,
                Player2Points,
                Player1PR,
                Player1Luck,
                Player2PR,
                Player2Luck
            FROM CompletedMatchesCache
            WHERE SeriesID = %s
            ORDER BY Date DESC, TimeCompleted DESC
        """, (series_id,))
        results = cursor.fetchall()

        data = []
        for row in results:
            (
                match_date, match_type_title,
                p1_name, p2_name,
                p1_points, p2_points,
                p1_pr, p1_luck, p2_pr, p2_luck
            ) = row

            match_date = match_date.strftime("%Y-%m-%d") if match_date else "?"

            if p1_points > p2_points:
                winner_info = p1_name
                loser_info = p2_name
                score = f"{p1_points}-{p2_points}"
                winner_pr = f"{p1_pr:.2f}" if p1_pr is not None else "-"
                winner_luck = f"{p1_luck:.2f}" if p1_luck is not None else "-"
                loser_pr = f"{p2_pr:.2f}" if p2_pr is not None else "-"
                loser_luck = f"{p2_luck:.2f}" if p2_luck is not None else "-"
            else:
                winner_info = p2_name
                loser_info = p1_name
                score = f"{p2_points}-{p1_points}"
                winner_pr = f"{p2_pr:.2f}" if p2_pr is not None else "-"
                winner_luck = f"{p2_luck:.2f}" if p2_luck is not None else "-"
                loser_pr = f"{p1_pr:.2f}" if p1_pr is not None else "-"
                loser_luck = f"{p1_luck:.2f}" if p1_luck is not None else "-"

            result_line = f"{winner_info} beat {loser_info}"

            data.append([
                match_date,
                match_type_title,
                result_line,
                score,
                winner_pr,
                winner_luck,
                loser_pr,
                loser_luck
            ])

        return pd.DataFrame(data, columns=[
            "Date Completed", "Match Type", "Result", "Score",
            "Winner PR", "Winner Luck", "Loser PR", "Loser Luck"
        ])

    except Exception as e:
        st.error(f"Error loading completed matches from cache: {e}")
        return pd.DataFrame(columns=[
            "Date Completed", "Match Type", "Result", "Score",
            "Winner PR", "Winner Luck", "Loser PR", "Loser Luck"
        ])
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def show_matches_completed_by_series(series_id):
    # Connect to the database
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Fetch MatchTypeIDs linked to the Series_ID
        query_match_types = """
        SELECT MatchTypeID
        FROM SeriesMatchTypes
        WHERE SeriesID = %s;
        """
        cursor.execute(query_match_types, (series_id,))
        match_type_ids = [row[0] for row in cursor.fetchall()]

        if not match_type_ids:
            st.warning("No match types found for the given series.")
            return

        # Step 2: Query completed matches for the MatchTypeIDs
        query_matches = f"""
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
        WHERE Fixtures.MatchTypeID IN ({','.join(['%s'] * len(match_type_ids))})
          AND Fixtures.Completed = 1
        ORDER BY MatchResults.Date DESC;
        """
        cursor.execute(query_matches, tuple(match_type_ids))
        results = cursor.fetchall()

        if not results:
            st.warning("No completed matches found for this series.")
            return

        # Step 3: Prepare data for display
        data = []
        for row in results:
            match_date = row[0].strftime("%Y-%m-%d")
            player1_points, player2_points = row[5], row[6]
            player1_pr, player2_pr = row[7], row[9]
            player1_luck, player2_luck = row[8], row[10]

            # Determine winner and loser
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

        # Step 4: Display results
        st.subheader("Completed Matches:")
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

    except Exception as e:
        st.error(f"Error fetching matches for series: {e}")
    finally:
        conn.close()
        
def show_matches_completed_in_table(match_type_id):
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
        data.append([
            match_date,
            f"{winner_info} beat {loser_info}",
            score,
            round(winner_pr, 2) if winner_pr is not None else None,
            round(winner_luck, 2) if winner_luck is not None else None,
            round(loser_pr, 2) if loser_pr is not None else None,
            round(loser_luck, 2) if loser_luck is not None else None,
        ])

    # Display results
    st.subheader("Completed Matches:")
    
    # Create DataFrame
    df = pd.DataFrame(data, columns=[
        "Date Completed", "Result", "Score", 
        "Winner PR", "Winner Luck", "Loser PR", "Loser Luck"
    ])
    
    # Display DataFrame
    if not df.empty:
        st.dataframe(df.style.format({
            "Winner PR": "{:.2f}",
            "Winner Luck": "{:.2f}",
            "Loser PR": "{:.2f}",
            "Loser Luck": "{:.2f}"
        }), hide_index=True)

    else:
        st.subheader("No completed matches found.")

def get_match_results_for_grid(match_type_id):
    """
    Fetch match results for a given match type, using MatchResults.MatchTypeID
    as the source of truth. Includes player names for grid display.
    """
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                p1.PlayerID AS Player1ID,
                p1.Name AS Player1Name,
                p2.PlayerID AS Player2ID,
                p2.Name AS Player2Name,
                mr.Player1Points AS Player1Points,
                mr.Player2Points AS Player2Points
            FROM MatchResults mr
            JOIN Players p1 ON mr.Player1ID = p1.PlayerID
            JOIN Players p2 ON mr.Player2ID = p2.PlayerID
            WHERE mr.MatchTypeID = %s
            ORDER BY p1.Name ASC;
        """
        cursor.execute(query, (match_type_id,))
        results = cursor.fetchall()

        cursor.close()
        conn.close()
        return results

    except Exception as e:
        st.error(f"Error fetching match results: {e}")
        return []

def get_match_results_for_grid930(match_type_id):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = """
        SELECT 
        	p1.PlayerID AS Player1ID, 
            p1.Name AS Player1Name, 
            p2.PlayerID AS Player2ID, 
            p2.Name AS Player2Name, 
            MatchResults.Player1Points AS Player1Points, 
            MatchResults.Player2Points AS Player2Points 
        FROM MatchResults 
        JOIN Fixtures ON MatchResults.FixtureID = Fixtures.FixtureID 
        JOIN Players p1 ON MatchResults.Player1ID = p1.PlayerID 
        JOIN Players p2 ON MatchResults.Player2ID = p2.PlayerID 
        WHERE Fixtures.MatchTypeID = %s
        """  # No semicolon here

        # Execute the query without multi=True
        cursor.execute(query, (match_type_id,))

        # Fetch all rows
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
            ORDER by 
                mr.Date, mr.TimeCompleted;
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
    COUNT(DISTINCT CASE WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points > mr.Player2Points THEN mr.MatchResultID
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points > mr.Player1Points THEN mr.MatchResultID END) AS Wins,
    COUNT(DISTINCT CASE WHEN mr.Player1ID = p.PlayerID AND mr.Player1Points < mr.Player2Points THEN mr.MatchResultID
                        WHEN mr.Player2ID = p.PlayerID AND mr.Player2Points < mr.Player1Points THEN mr.MatchResultID END) AS Losses,
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
