import streamlit as st
from database import add_player, add_match_type, add_match_result, get_players, get_match_types, get_match_results, get_email_checker_status, set_email_checker_status

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_column_width=True)  # The image will resize to the width of the page

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
    
# Sidebar checkboxes for adding to databases
st.sidebar.subheader("Add to Databases")
show_add_player_form = st.sidebar.checkbox("Add Player")
show_add_match_type_form = st.sidebar.checkbox("Add Match Type")
show_add_match_result_form = st.sidebar.checkbox("Add Match Result")
show_add_fixture_form = st.sidebar.checkbox("Add Fixture")

# New checkboxes for showing tables
st.sidebar.subheader("Show Databases")
show_players = st.sidebar.checkbox("Show all Players")
show_match_types = st.sidebar.checkbox("Show all Match Types")
show_match_results = st.sidebar.checkbox("Show all Match Results")
show_fixtures = st.sidebar.checkbox("Show all Fixtures")

# New checkboxes to updating a row
st.sidebar.subheader("Update Table Content")
page = st.sidebar.selectbox("",["Players","Match Types","Match Results","Fixtures"])
st.sidebar.write("Editing fields will open in main section -->")

# Editing Players
if page == "Players":
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
if page == "Match Types":
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

                # Form submission
                submitted = st.form_submit_button("Update Match Type")
                if submitted:
                    # Call update function to update the match type in the database
                    update_match_type(match_type_id, match_type_title)
                    st.success("Match type updated successfully!")
                    st.experimental_rerun()

# Add this function to update match type in database
def update_match_type(match_type_id, match_type_title):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE MatchTypes
        SET MatchTypeTitle = %s
        WHERE MatchTypeID = %s
    ''', (match_type_title, match_type_id))
    conn.commit()
    conn.close()

# Editing Fixtures
if page = "Fixtures":
    st.subheader("Edit Fixture")
    
# Editing Match Results
if page == "Match Results":
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

# Headings and forms for adding data
if show_add_player_form:
    st.subheader("Add Player")
    with st.form(key='add_player_form'):
        name = st.text_input("Name")
        nickname = st.text_input("Heroes Nickname")
        email = st.text_input("Email Address")
        submitted = st.form_submit_button("Add Player")
        if submitted:
            add_player(name, nickname, email)
            st.success("Player added successfully!")
            st.experimental_rerun()

if show_add_match_type_form:
    st.subheader("Add Match Type")
    with st.form(key='add_match_type_form'):
        match_type_title = st.text_input("Match Type Title")
        submitted = st.form_submit_button("Add Match Type")
        if submitted:
            add_match_type(match_type_title)
            st.success("Match type added successfully!")
            st.experimental_rerun()

if show_add_fixture_form:
    st.subheader("Add Fixture")
    
if show_add_match_result_form:
    st.subheader("Add Match Result")
    with st.form(key='add_match_result_form'):
        date = st.date_input("Date")
        time_completed = st.time_input("Time Completed")
        player1_id = st.number_input("Player 1 ID", min_value=1)
        player2_id = st.number_input("Player 2 ID", min_value=1)
        match_type_id = st.number_input("Match Type ID", min_value=1)
        player1_points = st.number_input("Player 1 Points", min_value=0)
        player2_points = st.number_input("Player 2 Points", min_value=0)
        player1_pr = st.number_input("Player 1 PR", min_value=0.0)
        player2_pr = st.number_input("Player 2 PR", min_value=0.0)
        player1_luck = st.number_input("Player 1 Luck", min_value=0.0)
        player2_luck = st.number_input("Player 2 Luck", min_value=0.0)
        submitted = st.form_submit_button("Add Match Result")
        if submitted:
            add_match_result(date, time_completed, player1_id, player2_id, match_type_id, player1_points, player2_points, player1_pr, player2_pr, player1_luck, player2_luck)
            st.success("Match result added successfully!")
            st.experimental_rerun()

# Display tables based on checkboxes
if show_players:
    st.subheader("All Players")
    players = get_players()
    if players:
        st.write("PlayerID | Name | Nickname | Email | Games Played | Total Wins | Total Losses | Win Percentage | Average PR")
        st.table(players)
    else:
        st.error("No players found.")

if show_match_types:
    st.subheader("All Match Types")
    match_types = get_match_types()
    if match_types:
        st.write("MatchTypeID | MatchTypeTitle")
        st.table(match_types)
    else:
        st.error("No match types found.")

if show_match_results:
    st.subheader("All Match Results")
    match_results = get_match_results()
    if match_results:
        st.write("MatchResultID | Date | Time Completed | Match Type ID | Player 1 ID | Player 2 ID | Player 1 Points | Player 2 Points | Player 1 PR | Player 2 PR | Player 1 Luck | Player 2 Luck")
        st.table(match_results)
    else:
        st.error("No match results found.")

if show_fixures:
    st.subheader("All fixtures")
    
