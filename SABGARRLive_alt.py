import streamlit as st
import shutil
import os
from datetime import date, timedelta

from database import (
    query_count,
    show_player_summary_tab,
    show_player_of_the_year,
    fetch_cached_series_standings,
    show_cached_remaining_fixtures_by_series,
    display_cached_matchtype_standings,
    display_match_grid,
    list_cached_remaining_fixtures,
    show_cached_matches_completed,
    get_averagePR_by_matchtype,
    get_fixturescount_by_matchtype,
    get_matchcount_by_matchtype,
    get_matchcount_by_date_and_series,
    get_matchcount_by_series,
    get_fixturescount_by_series,
    smccc,
    display_sorting_series_table,
    get_sorting_standings
)

# ==============================
# CONFIGURATION (KEY DESIGN)
# ==============================

SERIES_CONFIG = {
    "2026 - Series 2": {
        "series_id": 11,
        "end_date": date(2026, 6, 23),
        "leagues": {
            "A-League": 66,
            "B-League": 67,
            "C-League": 68,
            "D-League": 69,
            "E-League": 70,
            "F-League": 71,
            "Guppy Yellow": 72,
            "Guppy Blue": 73,
            "Guppy Red": 74,
            "Guppy Green": 75,  # NEW
        }
    },

    "2026 - Series 1": {
        "series_id": 10,
        "end_date": date(2026, 4, 2),
        "leagues": {
            "A-League": 56,
            "B-League": 57,
            "C-League": 58,
            "D-League": 59,
            "E-League": 60,
            "F-League": 61,
            "Guppy Yellow": 62,
            "Guppy Blue": 63,
            "Guppy Red": 64,
        }
    },

    "2025 - Series 4": {
        "series_id": 8,
        "end_date": date(2025, 12, 31),
        "leagues": {
            "A-League": 48,
            "B-League": 49,
            "C-League": 50,
            "D-League": 51,
            "E-League": 52,
            "F-League": 53,
            "Guppy 1": 54,
            "Guppy 2": 55,
        }
    },

    "2024 - Sorting League": {
        "series_id": 4,
        "sorting": True
    }
}


# ==============================
# SETUP
# ==============================

if os.path.exists("secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    shutil.copy("secrets.toml", ".streamlit/secrets.toml")

st.image(
    "https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg",
    use_column_width=True
)

st.sidebar.markdown(
    """
    <div style='text-align: center; margin: 10px;'>
        <img src='https://www.sabga.co.za/wp-content/uploads/2020/06/SABGA_logo_tight.jpg' width='200'/>
    </div>
    """,
    unsafe_allow_html=True
)


# ==============================
# COMPONENTS
# ==============================

def render_series_header(series_name, config):
    series_id = config["series_id"]

    matches_played = get_matchcount_by_series(series_id)
    total_fixtures = get_fixturescount_by_series(series_id)

    today = date.today()
    yesterday = today - timedelta(days=1)

    try:
        match_count_yesterday = get_matchcount_by_date_and_series(
            yesterday.strftime("%Y-%m-%d"), series_id
        )
    except:
        match_count_yesterday = 0

    if total_fixtures:
        percentage = (matches_played / total_fixtures) * 100
        metric_value = f"{matches_played}/{total_fixtures}"
    else:
        percentage = 0
        metric_value = "0/0"

    days_left = (config["end_date"] - today).days if "end_date" in config else 0

    st.title("SABGA Backgammon presents...")
    col1, col2 = st.columns(2)

    col1.title("Round Robin Leagues!")
    col2.metric("Progress", metric_value, f"{percentage:.1f}%")
    col2.write(f"Days remaining: {days_left}")

    return days_left


def render_overview(series_id):
    st.header("Overview")

    with st.expander("📊 Series Overview", expanded=True):
        fetch_cached_series_standings(series_id)

        if st.checkbox("Recent Results", key=f"results_{series_id}"):
            smccc(series_id)

        if st.checkbox("Remaining Fixtures", key=f"fixtures_{series_id}"):
            show_cached_remaining_fixtures_by_series(series_id)


def render_league(matchtype_id, league_name, days_left):
    with st.expander(f"🏆 {league_name}", expanded=False):

        if not st.checkbox(f"Load {league_name}", key=f"load_{matchtype_id}"):
            st.info("Click to load league data")
            return

        with st.spinner("Loading..."):
            played = get_matchcount_by_matchtype(matchtype_id)
            total = get_fixturescount_by_matchtype(matchtype_id)
            ave_pr = get_averagePR_by_matchtype(matchtype_id)

            games_left = max(total - played, 0)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Played", f"{played}/{total}")
            col2.metric("Remaining", games_left)
            col3.metric("Days left", days_left)
            col4.metric("Avg PR", ave_pr)

        if st.checkbox("Standings", key=f"s_{matchtype_id}"):
            display_cached_matchtype_standings(matchtype_id)

        if st.checkbox("Match Grid", key=f"g_{matchtype_id}"):
            display_match_grid(matchtype_id)

        if st.checkbox("Remaining Fixtures", key=f"f_{matchtype_id}"):
            list_cached_remaining_fixtures(matchtype_id)

        if st.checkbox("Completed Matches", key=f"c_{matchtype_id}"):
            show_cached_matches_completed(matchtype_id)


def render_series(series_name):
    config = SERIES_CONFIG[series_name]

    # Sorting League special case
    if config.get("sorting"):
        st.title("Sorting League")
        display_sorting_series_table(config["series_id"])
        smccc(config["series_id"])
        return

    days_left = render_series_header(series_name, config)

    render_overview(config["series_id"])

    st.header("Leagues")

    for league_name, matchtype_id in config["leagues"].items():
        render_league(matchtype_id, league_name, days_left)


# ==============================
# SIDEBAR NAV
# ==============================

st.sidebar.title("ROUND ROBIN DATA")
st.sidebar.write(f"Queries this run: {query_count}")

view_option = st.sidebar.radio(
    "Select view:",
    ["League Standings 📊", "Player Stats 👤", "Season Stats 📅"]
)

if view_option == "League Standings 📊":
    series_choice = st.sidebar.radio(
        "Select Series:",
        list(SERIES_CONFIG.keys()),
        index=0
    )

    render_series(series_choice)

elif view_option == "Player Stats 👤":
    show_player_summary_tab()
    st.stop()

elif view_option == "Season Stats 📅":
    season_choice = st.sidebar.radio("Season:", ["2026", "2025"])

    season_map = {"2026": 2, "2025": 1}
    show_player_of_the_year(season_map[season_choice])
    st.stop()
