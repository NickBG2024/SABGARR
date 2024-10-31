import streamlit as st
from database import (
    add_player,
    add_match_type,
    add_match_result,
    get_fixtures,
    get_players,
    get_match_types,
    get_match_results,
    get_email_checker_status,
    set_email_checker_status,
    add_series,
    add_match_type_to_series,
    get_series,
    get_series_match_types,
    update_series_title,
    update_match_type_in_series
)

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)

# Public-facing app for all users
st.title("SABGA Backgammon: Admin page")
st.write("Welcome to the admin page of South African Backgammon Round Robin! This page is for admins to manage the SABGA National Round Robin.")

# Add an icon image to sidebar
st.sidebar.markdown(
    """
    <div style='text-align: center; margin: 20px 5px 20px 5px;'>
        <img src='https://www.sabga.co.za/wp-content/uploads/2020/06/SABGA_logo_tight.jpg' width='250'/>
    </div>
    """, unsafe_allow_html=True
)

# Retrieve the current status of the email checker
email_checker_status = get_email_checker_status()

# Checkbox to toggle email checker on/off
email_checker_checkbox = st.sidebar.checkbox("Enable Email Checker", value=email_checker_status)

if email_checker_checkbox != email_checker_status:
    set_email_checker_status(email_checker_checkbox)
    st.success(f"Email Checker {'enabled' if email_checker_checkbox else 'disabled'}")

st.sidebar.subheader("ADMIN-FUNCTIONS")
# Checkbox to access "Generate Fixtures" functionality
generate_fixtures = st.sidebar.checkbox("Generate Fixtures")

# Sidebar checkboxes for adding to databases
st.sidebar.subheader("Add to Databases")
show_add_player_form = st.sidebar.checkbox("Add Player")
show_add_match_type_form = st.sidebar.checkbox("Add Match Type")
show_add_match_result_form = st.sidebar.checkbox("Add Match Result")
show_add_fixture_form = st.sidebar.checkbox("Add Fixture")
show_add_series_form = st.sidebar.checkbox("Add Series")

# New checkboxes for showing tables
st.sidebar.subheader("Show Databases")
show_players = st.sidebar.checkbox("Show all Players")
show_match_types = st.sidebar.checkbox("Show all Match Types")
show_match_results = st.sidebar.checkbox("Show all Match Results")
show_fixtures = st.sidebar.checkbox("Show all Fixtures")
show_series = st.sidebar.checkbox("Show all Series")

# New checkboxes to updating a row
st.sidebar.subheader("Update Table Content")

edit_players = st.sidebar.checkbox("Edit Players")
edit_match_types = st.sidebar.checkbox("Edit Match Types")
edit_match_results = st.sidebar.checkbox("Edit Match Results")
edit_fixtures = st.sidebar.checkbox("Edit Fixtures")
edit_series = st.sidebar.checkbox("Edit Series")

# Generating Fixtures UI
if generate_fixtures:
    st.subheader("Generate Fixtures")

    # Fetch available match types and players for dropdowns
    match_types = get_match_types()  # Assuming get_match_types() returns a list of tuples (MatchTypeID, MatchTypeTitle)
    players = get_players()  # Assuming get_players() returns a list of tuples (PlayerID, Name)

    # Dropdown for Match Type selection
    match_type_id = st.selectbox("Select Match Type", [mt[0] for mt in match_types], format_func=lambda x: dict(match_types)[x])

    # Multi-select dropdowns for selecting up to 10 players
    selected_players = []
    for i in range(1, 11):
        player = st.selectbox(f"Select Player {i}", options=[None] + players, format_func=lambda x: x[1] if x else "None")
        if player:
            selected_players.append(player[0])

    # Ensure at least 3 players are selected
    if len(selected_players) < 3:
        st.warning("Please select at least 3 players to generate fixtures.")
    else:
        # Button to generate fixtures
        if st.button("Generate Fixtures"):
            generate_fixture_entries(match_type_id, selected_players)
            st.success("Fixtures generated successfully!")

# Define function to generate fixtures based on selected match type and players
def generate_fixture_entries(match_type_id, player_ids):
    conn = create_connection()
    cursor = conn.cursor()
    # Generate unique matchups between players
    for i in range(len(player_ids)):
        for j in range(i + 1, len(player_ids)):
            player1_id, player2_id = player_ids[i], player_ids[j]
            cursor.execute(
                '''
                INSERT INTO Fixtures (MatchTypeID, Player1ID, Player2ID)
                VALUES (%s, %s, %s)
                ''',
                (match_type_id, player1_id, player2_id)
            )
    conn.commit()
    conn.close()
    
# 1. **Add Series Form**
if show_add_series_form:
    st.subheader("Add a New Series")

    with st.form(key="add_series_form"):
        series_title = st.text_input("Series Title")

        # Submit to add the Series to the database
        submitted = st.form_submit_button("Add Series")
        if submitted and series_title:
            add_series(series_title)
            st.success(f"Series '{series_title}' added successfully!")
            st.experimental_rerun()

# 2. **Show Series Table Content**
if show_series:
    st.subheader("Series in Database")
    series = get_series()
    for s in series:
        st.write(f"ID: {s[0]}, Title: {s[1]}")

# 3. **Edit Series**
if edit_series:
    st.subheader("Edit Series")

    # Fetch all series
    series = get_series()
    if series:
        # Map series titles to their IDs for selection
        series_dict = {f"{s[1]} (ID: {s[0]})": s for s in series}
        selected_series = st.selectbox("Select Series to Edit", list(series_dict.keys()))

        if selected_series:
            series_data = series_dict[selected_series]
            series_id = series_data[0]

            # Prepopulate the form with selected series data
            with st.form(key='edit_series_form'):
                series_title = st.text_input("Series Title", value=series_data[1])

                # Form submission
                submitted = st.form_submit_button("Update Series")
                if submitted:
                    update_series_title(series_id, series_title)
                    st.success("Series updated successfully!")
                    st.experimental_rerun()
                    
            # Show match types in the selected series
            st.write("Match Types in this Series:")
            match_types = get_series_match_types(series_id)
            for match in match_types:
                st.write(f"MatchType ID: {match[0]}, Title: {match[1]}")

            # Option to add new match type to the series
            with st.form(key="add_match_type_to_series_form"):
                match_type_id = st.number_input("MatchType ID to Add", min_value=1)
                submitted_add = st.form_submit_button("Add Match Type to Series")
                if submitted_add:
                    add_match_type_to_series(series_id, match_type_id)
                    st.success("Match Type added to series!")
                    st.experimental_rerun()
                    
# Editing Players
if edit_players:
    st.subheader("Edit Player")

    # Fetch all players to populate the selectbox
    players = get_players()

    if players:
        # Create a dictionary to map player names to their IDs for selection
        player_dict = {f"{player[1]} (ID: {player[0]})": player for player in players}
        selected_player = st.selectbox("Select Player to Edit", list(player_dict.keys()))

        if selected_player:
            player_data = player_dict[selected_player]
            player_id = player_data[0]  # Extract the PlayerID

            # Prepopulate form with the selected player's data
            with st.form(key='edit_player_form'):
                name = st.text_input("Name", value=player_data[1])
                nickname = st.text_input("Nickname", value=player_data[2])
                email = st.text_input("Email", value=player_data[3])

                # Form submission
                submitted = st.form_submit_button("Update Player")
                if submitted:
                    # Call update function to update the player in the database
                    update_player(player_id, name, nickname, email)
                    st.success("Player updated successfully!")
                    st.experimental_rerun()
                    
# Editing Match Types
if edit_match_types:
    st.subheader("Edit Match Type")

    # Fetch all match types
    match_types = get_match_types()

    if match_types:
        # Create a dictionary to map match type titles to their IDs for selection
        match_type_dict = {f"{match_type[1]} (ID: {match_type[0]})": match_type for match_type in match_types}
        selected_match_type = st.selectbox("Select Match Type to Edit", list(match_type_dict.keys()))

        if selected_match_type:
            match_type_data = match_type_dict[selected_match_type]
            match_type_id = match_type_data[0]  # Extract the MatchTypeID

            # Prepopulate form with the selected match type's data
            with st.form(key='edit_match_type_form'):
                match_type_title = st.text_input("Match Type Title", value=match_type_data[1])
                active_status = st.checkbox("Active", value=match_type_data[2])

                # Form submission
                submitted = st.form_submit_button("Update Match Type")
                if submitted:
                    # Call update function to update the match type in the database
                    update_match_type(match_type_id, match_type_title, active_status)
                    st.success("Match type updated successfully!")
                    st.experimental_rerun()

# Add this function to update match type in database
def update_match_type(match_type_id, match_type_title, active_status):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE MatchType
        SET MatchTypeTitle = %s, Active = %s
        WHERE MatchTypeID = %s
    ''', (match_type_title, active_status, match_type_id))
    conn.commit()
    conn.close()

# Editing Fixtures
if edit_fixtures:
    st.subheader("Edit Fixture")
    
# Editing Match Results
if edit_match_results:
    st.subheader("Edit Match Result")

    # Fetch all match results
    match_results = get_match_results()

    if match_results:
        # Create a dictionary to map match result IDs to their data for selection
        match_result_dict = {f"Match ID {match_result[0]} (Date: {match_result[1]})": match_result for match_result in match_results}
        selected_match_result = st.selectbox("Select Match Result to Edit", list(match_result_dict.keys()))

        if selected_match_result:
            match_result_data = match_result_dict[selected_match_result]
            match_result_id = match_result_data[0]  # Extract the MatchResultID

            # Prepopulate form with the selected match result's data
            with st.form(key='edit_match_result_form'):
                date = st.date_input("Date", value=match_result_data[1])
                time_completed = st.time_input("Time Completed", value=match_result_data[2])
                match_type_id = st.number_input("Match Type ID", min_value=1, value=match_result_data[3])
                player1_id = st.number_input("Player 1 ID", min_value=1, value=match_result_data[4])
                player2_id = st.number_input("Player 2 ID", min_value=1, value=match_result_data[5])
                player1_points = st.number_input("Player 1 Points", min_value=0, value=match_result_data[6])
                player2_points = st.number_input("Player 2 Points", min_value=0, value=match_result_data[7])
                player1_pr = st.number_input("Player 1 PR", min_value=0.0, value=match_result_data[8])
                player2_pr = st.number_input("Player 2 PR", min_value=0.0, value=match_result_data[9])
                player1_luck = st.number_input("Player 1 Luck", min_value=0.0, value=match_result_data[10])
                player2_luck = st.number_input("Player 2 Luck", min_value=0.0, value=match_result_data[11])

                # Form submission
                submitted = st.form_submit_button("Update Match Result")
                if submitted:
                    # Call update function to update the match result in the database
                    update_match_result(match_result_id, date, time_completed, match_type_id, player1_id, player2_id,
                                        player1_points, player2_points, player1_pr, player2_pr, player1_luck, player2_luck)
                    st.success("Match result updated successfully!")
                    st.experimental_rerun()

# Add this function to update match result in database
def update_match_result(match_result_id, date, time_completed, match_type_id, player1_id, player2_id,
                        player1_points, player2_points, player1_pr, player2_pr, player1_luck, player2_luck):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE MatchResults
        SET Date = %s, TimeCompleted = %s, MatchTypeID = %s, Player1ID = %s, Player2ID = %s,
            Player1Points = %s, Player2Points = %s, Player1PR = %s, Player2PR = %s, Player1Luck = %s, Player2Luck = %s
        WHERE MatchResultID = %s
    ''', (date, time_completed, match_type_id, player1_id, player2_id, player1_points, player2_points,
          player1_pr, player2_pr, player1_luck, player2_luck, match_result_id))
    conn.commit()
    conn.close()

# Add this function to update player in database
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
