import imaplib
import email
import re
import random
import streamlit as st
import pandas as pd

from database import (
    get_remaining_fixtures_for_admin,
    insert_match_result_admin,
    get_matchcount_by_date_and_matchtype,
    display_matchtype_standings_with_points,
    get_matchcount_by_matchtype,
    get_fixturescount_by_matchtype,
    display_match_gridd,
    smccc,
    get_matchcount_by_date,
    get_matchcount_by_series,
    get_fixturescount_by_series,
    show_matches_completed_by_series,
    show_matches_completed,
    display_sorting_series_table,
    display_series_table,
    display_series_table_completedonly,
    display_match_grid,
    list_remaining_fixtures,
    display_group_table,
    get_remaining_fixtures,
    get_match_results_for_grid,
    get_player_stats_with_fixtures,
    get_player_stats_by_matchtype,
    get_sorting_standings,
    get_fixtures_with_names_by_match_type,
    get_match_results_nicely_formatted,
    print_table_structure,
    get_player_id_by_nickname,
    get_match_type_id_by_identifier,
    check_result_exists,
    insert_match_result,
    get_fixture,
    get_standings,
    get_match_results,
    check_tables,
    create_connection,
    insert_match_result,
    check_result_exists,
    get_email_checker_status
)

from datetime import datetime, timedelta, timezone, date


# =========================================================
# ADMIN LOGIN CONFIG
# =========================================================

ADMIN_PASSWORD = st.secrets["admin"]["password"]

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False


def admin_login():
    st.sidebar.subheader("Admin Login")

    password = st.sidebar.text_input(
        "Enter admin password",
        type="password"
    )

    if st.sidebar.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.sidebar.success("Logged in successfully")
        else:
            st.sidebar.error("Incorrect password")


def admin_logout():
    if st.sidebar.button("Logout"):
        st.session_state.admin_logged_in = False
        st.rerun()


# =========================================================
# PUBLIC PAGE
# =========================================================

# Add a header image at the top of the page
st.image(
    "https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg",
    use_container_width=True
)

# InitiationVariables
match_type_id = 77

matches_played = get_matchcount_by_matchtype(match_type_id)
total_fixtures = get_fixturescount_by_matchtype(match_type_id)

percentage = (matches_played / total_fixtures) * 100
metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"

# Get today and yesterday's date
today = date.today()
yesterday = today - timedelta(days=1)

# Fetch match count for yesterday
match_count_yesterday = get_matchcount_by_date_and_matchtype(
    yesterday.strftime("%Y-%m-%d"),
    5
)

# Public-facing app for all users
st.title("SABGA Backgammon presents...")

col1, col2 = st.columns(2)

col1.title("DC's 'BMAB Test' Live League 2026: S1!")
col2.metric("Progress...", metric_value, match_count_yesterday)

# =========================================================
# SIDEBAR ADMIN AREA
# =========================================================

st.sidebar.title("Administration")

if st.session_state.admin_logged_in:
    st.sidebar.success("Admin Mode Active")
    admin_logout()
else:
    admin_login()

# =========================================================
# MAIN TABS
# =========================================================

tab1, tab2 = st.tabs(["Player Standings", "Further Details"])

with tab1:
    st.header("Player Standings - ordered by Points")
    st.write("R500 entry, eventual prize: Africa Open entry!")

    display_matchtype_standings_with_points(match_type_id)

with tab2:
    display_match_grid(match_type_id)
    list_remaining_fixtures(match_type_id)
    show_matches_completed(match_type_id)

# =========================================================
# ADMIN SECTION
# =========================================================

if st.session_state.admin_logged_in:

    st.divider()

    st.header("Admin Panel")

    st.success("You are logged in as administrator.")

    st.subheader("Enter Match Result")

    remaining_fixtures = get_remaining_fixtures_for_admin(match_type_id)

    if not remaining_fixtures:

        st.success("All fixtures completed.")

    else:

        fixture_options = {}

        for fixture in remaining_fixtures:

            label = (
                f"{fixture['Player1Name']} "
                f"vs "
                f"{fixture['Player2Name']}"
            )

            fixture_options[label] = fixture

        selected_label = st.selectbox(
            "Select Fixture",
            list(fixture_options.keys())
        )

        selected_fixture = fixture_options[selected_label]

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:

            player1_points = st.number_input(
                f"{selected_fixture['Player1Name']} Points",
                min_value=0,
                max_value=25,
                value=0
            )

            player1_pr = st.number_input(
                f"{selected_fixture['Player1Name']} PR",
                min_value=0.0,
                max_value=50.0,
                value=0.0,
                step=0.1
            )

        with col2:

            player2_points = st.number_input(
                f"{selected_fixture['Player2Name']} Points",
                min_value=0,
                max_value=25,
                value=0
            )

            player2_pr = st.number_input(
                f"{selected_fixture['Player2Name']} PR",
                min_value=0.0,
                max_value=50.0,
                value=0.0,
                step=0.1
            )

        if st.button("Submit Result"):

            if player1_points == player2_points:

                st.error("Scores cannot be equal.")

            else:

                success, message = insert_match_result_admin(
                    fixture_id=selected_fixture["FixtureID"],
                    match_type_id=match_type_id,
                    player1_id=selected_fixture["Player1ID"],
                    player2_id=selected_fixture["Player2ID"],
                    player1_points=player1_points,
                    player2_points=player2_points,
                    player1_pr=player1_pr,
                    player2_pr=player2_pr
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)
