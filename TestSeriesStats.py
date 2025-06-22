import streamlit as st
import pandas as pd
import plotly.express as px
from database import create_connection

# Function to load pre-aggregated stats
def get_series_stats(series_id):
    conn = create_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            p.Name,
            sps.GamesPlayed,
            sps.Wins,
            sps.Losses,
            sps.WinPercentage,
            sps.Points,
            sps.AveragePR,
            sps.PRWins,
            sps.AverageLuck,
            sps.LastUpdated
        FROM SeriesPlayerStats sps
        JOIN Players p ON sps.PlayerID = p.PlayerID
        WHERE sps.SeriesID = %s
        ORDER BY sps.Points DESC, sps.AveragePR ASC
    """
    cursor.execute(query, (series_id,))
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(results, columns=columns)
    cursor.close()
    conn.close()
    return df

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("📊 Series Stats Explorer (Test Page)")

series_options = {
    "2025 - Series 2": 6,
    "2025 - Series 1": 5,
    "2024 - Sorting League": 4
}

selected_series = st.selectbox("Select a series:", list(series_options.keys()))
series_id = series_options[selected_series]

df = get_series_stats(series_id)

if df.empty:
    st.warning("No stats found for this series. Did you refresh it yet?")
    st.stop()

# Filter
min_games = st.slider("Minimum games played to include player", 0, int(df["GamesPlayed"].max()), 3)
filtered_df = df[df["GamesPlayed"] >= min_games]

st.subheader("📋 Raw Stats Table")
st.dataframe(filtered_df.style.format({
    "WinPercentage": "{:.1f}%",
    "AveragePR": "{:.2f}",
    "AverageLuck": "{:.2f}"
}), use_container_width=True)

# --- Charts ---
st.markdown("### 🏆 Points Leaderboard")
fig1 = px.bar(filtered_df, x="Name", y="Points", color="Points", text="Points",
              labels={"Points": "Total Points", "Name": "Player"}, height=400)
fig1.update_traces(textposition="outside")
st.plotly_chart(fig1, use_container_width=True)

st.markdown("### 📉 Average PR per Player")
fig2 = px.line(filtered_df.sort_values("AveragePR"), x="Name", y="AveragePR", markers=True,
               labels={"AveragePR": "Avg PR", "Name": "Player"}, height=400)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("### 🎯 PR vs. Luck (Scatter Plot)")
fig3 = px.scatter(filtered_df, x="AveragePR", y="AverageLuck", size="GamesPlayed", color="Name",
                  hover_name="Name", labels={"AveragePR": "Avg PR", "AverageLuck": "Avg Luck"},
                  title="Skill vs. Luck", height=450)
st.plotly_chart(fig3, use_container_width=True)

st.markdown("### 📊 PR Distribution")
fig4 = px.histogram(filtered_df, x="AveragePR", nbins=20, title="Distribution of Average PRs")
st.plotly_chart(fig4, use_container_width=True)

st.markdown("### ⚔️ Win Percentage")
fig5 = px.bar(filtered_df.sort_values("WinPercentage", ascending=False),
              x="Name", y="WinPercentage", color="WinPercentage",
              labels={"WinPercentage": "Win %"}, height=400)
fig5.update_traces(texttemplate="%{y:.1f}%", textposition="outside")
st.plotly_chart(fig5, use_container_width=True)

st.caption(f"Data last updated: {df['LastUpdated'].max()}")
