import streamlit as st
import pandas as pd
import datetime
from st_aggrid import AgGrid, GridOptionsBuilder

from database import (
    add_fixture,
    add_player,
    add_match_type,
    add_match_result,
    create_connection,
    get_averagePR_by_matchtype,
    get_fixtures,
    get_fixturescount_by_matchtype,
    get_fixturescount_by_series,
    get_fixtures_with_names,
    get_players_simple,
    get_players_full,
    get_matchcount_by_matchtype,
    get_matchcount_by_series,
    get_match_types,
    get_match_results,
    get_match_results_nicely_formatted,
    get_nickname_to_full_name_map,
    get_email_checker_status,
    list_players_alphabetically,
    is_duplicate_player,
    set_email_checker_status,
    add_series,
    add_match_type_to_series,
    remove_match_type_from_series,
    get_series,
    get_series_match_types,
    update_match_type_status,
    update_series_title,
    update_match_type_in_series,
    update_fixture,
    update_player,
    refresh_series_stats,
    refresh_matchtype_stats,
    update_remaining_fixtures_by_series,
    generate_fixture_entries,
)

# Add a header image at the top of the page
st.image("https://www.sabga.co.za/wp-content/uploads/2020/06/cropped-coverphoto.jpg", use_container_width=True)

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

if 'form_updated' in st.session_state and st.session_state['form_updated']:
    del st.session_state['form_updated']
    st.rerun()
    
matches_played = get_matchcount_by_series(6)
total_fixtures = get_fixturescount_by_series(6)
percentage = (matches_played / total_fixtures) * 100
metric_value = f"{matches_played}/{total_fixtures} ({percentage:.1f}%)"

st.sidebar.header("Current series: RR S2 2025 (id=5)")
#st.sidebar.metric("Series data - players","54","3")
st.sidebar.metric("Series data - matches",metric_value, "4")
st.sidebar.subheader("Admin-Functions: Main")

st.sidebar.subheader("Update Series Stats")

# Fetch series from DB
try:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SeriesID, SeriesTitle FROM Series ORDER BY SeriesID DESC")
    series_rows = cursor.fetchall()
    cursor.close()
    conn.close()

    series_dict = {title: sid for sid, title in series_rows}
    selected_series_label = st.sidebar.selectbox("Select a series:", list(series_dict.keys()), key="series_select")
    selected_series_id = series_dict[selected_series_label]

    if st.sidebar.button("Refresh Series Stats"):
        refresh_series_stats(selected_series_id)
        st.sidebar.success(f"Refreshed: {selected_series_label}")
        
    if st.sidebar.button("Update Remaining Series Fixtures"):
        update_remaining_fixtures_by_series(selected_series_id)
        st.sidebar.success(f"Remaining fixtures updated for: {selected_series_label}")

except Exception as e:
    st.sidebar.error(f"Error loading series list: {e}")


# --------------------------
# Match Type Stats Controls
# --------------------------
st.sidebar.subheader("Update Match Type Stats")

# Dropdown to refresh individual match types
try:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MatchTypeID, MatchTypeTitle FROM MatchType ORDER BY MatchTypeTitle")
    matchtype_rows = cursor.fetchall()
    cursor.close()
    conn.close()

    matchtype_dict = {title: mtid for mtid, title in matchtype_rows}
    selected_label = st.sidebar.selectbox("Select a match type:", list(matchtype_dict.keys()), key="matchtype_select")
    selected_id = matchtype_dict[selected_label]

    if st.sidebar.button("Refresh Selected MatchType"):
        refresh_matchtype_stats(selected_id)
        st.sidebar.success(f"Refreshed: {selected_label}")

except Exception as e:
    st.sidebar.error(f"Error loading match types: {e}")


# Button to refresh ALL active match types
if st.sidebar.button("Refresh All Active MatchTypes"):
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MatchTypeID, MatchTypeTitle FROM MatchType WHERE Active = 1 ORDER BY MatchTypeTitle")
        active_matchtypes = cursor.fetchall()
        cursor.close()
        conn.close()

        for mt_id, mt_title in active_matchtypes:
            refresh_matchtype_stats(mt_id)
            st.sidebar.write(f"✓ {mt_title} refreshed")

        st.sidebar.success("All active match types refreshed.")

    except Exception as e:
        st.sidebar.error(f"Error refreshing all match types: {e}")
    
# Checkbox to access "Generate Fixtures" functionality
generate_fixtures = st.sidebar.checkbox("Generate Fixtures")
# Checkbox to toggle email checker on/off
email_checker_checkbox = st.sidebar.checkbox("Enable Email Checker", value=email_checker_status)
see_series_details = st.sidebar.checkbox("Series details")

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
show_AZ_list = st.sidebar.checkbox("List Players A-Z")
show_AZ_list_and_nicknames = st.sidebar.checkbox("List Players and Nicknames A-Z")
show_match_types = st.sidebar.checkbox("Show all Match Types")
show_match_results = st.sidebar.checkbox("Show all Match Results")
show_match_results_nicely_formatted = st.sidebar.checkbox("Show Match Results Nicely Formatted")
show_fixtures = st.sidebar.checkbox("Show all Fixtures")
show_fixtures_with_names = st.sidebar.checkbox("Show all Fixtures with names")
show_series = st.sidebar.checkbox("Show all Series")

# New checkboxes to updating a row
st.sidebar.subheader("Update Table Content")

edit_players = st.sidebar.checkbox("Edit Players")
edit_match_types = st.sidebar.checkbox("Edit Match Types")
edit_match_results = st.sidebar.checkbox("Edit Match Results")
edit_fixtures = st.sidebar.checkbox("Edit Fixtures")
edit_series = st.sidebar.checkbox("Edit Series")

if email_checker_checkbox != email_checker_status:
    set_email_checker_status(email_checker_checkbox)
    st.success(f"Email Checker {'enabled' if email_checker_checkbox else 'disabled'}")

if see_series_details:
    st.subheader("Series Details")
    # Step 1: Fetch Series List
    series_list = get_series()  # Fetch Series from database
    
    if series_list:
        series_options = {series[0]: series[1] for series in series_list}  # {id: name}
        selected_series_id = st.selectbox("Select a Series", options=series_options.keys(), format_func=lambda x: series_options[x])
    
        if selected_series_id:
            # Step 2: Fetch Series-wide match stats
            total_matches_played = get_matchcount_by_series(selected_series_id)
            total_fixtures = get_fixturescount_by_series(selected_series_id)
            matches_left = total_fixtures - total_matches_played
    
            # Display overall progress
            col1, col2 = st.columns(2)
            percentage = (total_matches_played / total_fixtures) * 100
            metric_value = f"{total_matches_played}/{total_fixtures} ({percentage:.1f}%)"
            col1.metric("Total Matches Played:", metric_value)
            col2.metric("Matches Left:", matches_left)
    
            # Step 3: Show match progress per Match Type
            st.subheader("Match Type Breakdown")
            match_types = get_series_match_types(selected_series_id)
    
            if match_types:
                for match_type_id, match_type_title in match_types:
                    played = get_matchcount_by_matchtype(match_type_id)
                    total = get_fixturescount_by_matchtype(match_type_id)
                    remaining = total - played
                    if played != 0:
                        percentage = (played/total) * 100
                    else : 
                        percentage = 0
                    metval = f"{played}/{total} ({percentage:.1f}%)"
                    st.metric(match_type_title, metval, f"{remaining} left")

            #show Ave PRs
            st.title("League averages:")
            match_types = get_series_match_types(selected_series_id)
            if match_types:
                for match_type_id, match_type_title in match_types:
                    matchtypePR = get_averagePR_by_matchtype(match_type_id)


            # Step 1: Get Match Types for the Selected Series
            match_types = get_series_match_types(selected_series_id)
            
            # Step 2: Fetch PR values for each match type in the series
            league_names = []  # Store league names dynamically
            average_prs = []   # Store corresponding PR values
            
            if match_types:
                for match_type_id, match_type_title in match_types:
                    league_names.append(match_type_title)  # Use match_type_title as league name
                    average_prs.append(get_averagePR_by_matchtype(match_type_id))
            
            # Step 3: Create DataFrame
            df = pd.DataFrame({"League": league_names, "Average PR": average_prs})
            
            # Step 4: Display DataFrame and Chart
            st.dataframe(df)
        
            # Streamlit bar chart
            st.subheader("📊 Average PR per League")
            #st.line_chart(df.set_index("League"))
            st.bar_chart(df.set_index("League"))
        
            # Set up the figure and axis
            fig, ax = plt.subplots(figsize=(8, 5))
            sns.barplot(x="League", y="Average PR", data=df, ax=ax, palette="coolwarm")
            
            # Add value labels on top of the bars
            for i, v in enumerate(average_prs):
                ax.text(i, v + 0.5, f"{v:.2f}", ha='center', fontsize=12, fontweight='bold')
            
            # Set labels and title
            ax.set_ylabel("Average PR")
            ax.set_xlabel("League")
            ax.set_title("Average PR per League")
            
            # Display the chart in Streamlit
            st.pyplot(fig)

#-------------------------------------------------------------------------------------------------------
# Generate Fixtures UI
if generate_fixtures:
    st.subheader("Generate Fixtures")

    # Session state to manage form reset
    if "reset_flag" not in st.session_state:
        st.session_state.reset_flag = False

    # Fetch available match types and players for dropdowns
    match_types = get_match_types()  # Assuming get_match_types() returns a list of tuples (MatchTypeID, MatchTypeTitle, ...)
    players = get_players_simple()  # Assuming get_players_simple() returns a list of tuples (PlayerID, Name, Nickname)

    # Debugging output
    print("Match Types:", match_types)
    print("Players:", players)

    # Convert match_types into a dictionary for easier lookup
    match_type_dict = {mt[0]: mt[1] for mt in match_types}  # Assuming MatchTypeID is mt[0] and Title is mt[1]

    # Dropdown for Match Type selection
    match_type_id = st.selectbox(
        "Select Match Type",
        options=list(match_type_dict.keys()),
        format_func=lambda x: match_type_dict[x],
        key="match_type" if not st.session_state.reset_flag else None
    )

    # Multi-select dropdowns for selecting up to 10 players
    selected_players = []
    for i in range(1, 13):
        player = st.selectbox(
            f"Select Player {i}",
            options=[None] + players,
            format_func=lambda x: x[1] if x else "None",
            key=f"player_select_{i}" if not st.session_state.reset_flag else None
        )
        if player:
            selected_players.append(player[0])  # Append PlayerID

    # Ensure at least 3 players are selected
    if len(selected_players) < 3:
        st.warning("Please select at least 3 players to generate fixtures.")
    else:
        # Button to generate fixtures
        if st.button("Generate Fixtures"):
            generate_fixture_entries(match_type_id, selected_players)
            st.success("Fixtures generated successfully!")

            # Reset session state flags to clear the form
            for key in st.session_state.keys():
                if key.startswith("match_type") or key.startswith("player_select_"):
                    st.session_state[key] = None
            st.session_state.reset_flag = True  # Trigger reset on the next render
            
# Function to generate fixture entries in the database
def generate_fixture_entries(match_type_id, player_ids):
    conn = create_connection()
    cursor = conn.cursor()

    # Generate unique matchups between players
    for i in range(len(player_ids)):
        for j in range(i + 1, len(player_ids)):
            player1_id, player2_id = player_ids[i], player_ids[j]
            cursor.execute(
                '''
                INSERT INTO Fixtures (MatchTypeID, Player1ID, Player2ID, Completed)
                VALUES (%s, %s, %s, %s)
                ''',
                (match_type_id, player1_id, player2_id, 0)  # Ensure 'Completed' defaults to 0
            )
    conn.commit()
    conn.close()    
# *****************************************************ADDING FORMS********************************************
# Add Player Form
if show_add_player_form:
    st.subheader("Add a New Player")

    player_form_placeholder = st.empty()
    with player_form_placeholder.form(key="add_player_form"):
        player_name = st.text_input("Player Name")
        heroes_nickname = st.text_input("Heroes Nickname")
        email = st.text_input("Email")

        # Submit to add the Player to the database
        submitted = st.form_submit_button("Add Player")

        if submitted:
            if not player_name or not heroes_nickname or not email:
                st.warning("All fields are required!")
            elif is_duplicate_player(player_name, heroes_nickname, email):
                st.error("Duplicate entry found! Please use unique values.")
            else:
                add_player(player_name, heroes_nickname, email)
                st.success(f"Player '{player_name}' added successfully!")
                st.rerun()  # Clear form and refresh

# Add Match Result
if show_add_match_result_form:
    st.subheader("Add a New Match Result")

    match_result_form_placeholder = st.empty()
    with match_result_form_placeholder.form(key="add_match_result_form"):
        date = st.date_input("Date")
        time_completed = st.time_input("Time Completed")
        match_type_id = st.selectbox("Match Type", [mt[0] for mt in get_match_types()])
        player1_id = st.selectbox("Player 1", [p[0] for p in get_players_simple()])
        player2_id = st.selectbox("Player 2", [p[0] for p in get_players_simple()])
        player1_points = st.number_input("Player 1 Points", min_value=0)
        player2_points = st.number_input("Player 2 Points", min_value=0)
        player1_pr = st.number_input("Player 1 PR", format="%.2f")
        player2_pr = st.number_input("Player 2 PR", format="%.2f")
        player1_luck = st.number_input("Player 1 Luck", format="%.2f")
        player2_luck = st.number_input("Player 2 Luck", format="%.2f")

        # Submit to add the Match Result to the database
        submitted = st.form_submit_button("Add Match Result")
        if submitted:
            add_match_result(date, time_completed, match_type_id, player1_id, player2_id, 
                             player1_points, player2_points, player1_pr, player2_pr, 
                             player1_luck, player2_luck)
            st.success("Match Result added successfully!")
            match_result_form_placeholder.empty()  # Clear form by emptying the placeholder
            st.rerun()

# Add Match Type# Add Match Type
if show_add_match_type_form:
    st.subheader("Add a New Match Type")

    match_type_form_placeholder = st.empty()
    with match_type_form_placeholder.form(key="add_match_type_form"):
        match_type_title = st.text_input("Match Type Title", help="Enter a descriptive title for the match type.")
        match_type_identifier = st.text_input(
            "Match Type Identifier",
            help="Enter a unique identifier for the match type. Example: 'league', 'friendly'."
        )
        active = st.checkbox("Active", value=True)

        # Validation and submission
        submitted = st.form_submit_button("Add Match Type")
        if submitted:
            if not match_type_title:
                st.error("Match Type Title is required.")
            elif not match_type_identifier:
                st.error("Match Type Identifier is required.")
            elif " " in match_type_identifier:
                st.error("Match Type Identifier should not contain spaces.")
            else:
                # Add to database
                add_match_type(match_type_title, match_type_identifier, active)
                st.success(f"Match Type '{match_type_title}' with identifier '{match_type_identifier}' added successfully!")
                match_type_form_placeholder.empty()  # Clear form
                st.session_state["key"] = None
                #st.rerun()


# Add Fixture
if show_add_fixture_form:
    st.subheader("Add a New Fixture")

    fixture_form_placeholder = st.empty()
    with fixture_form_placeholder.form(key="add_fixture_form"):
        # Get match types and players as lists of tuples (ID, Name)
        match_types = get_match_types()
        players = get_players_simple()

        # Show match type titles and retrieve the selected ID
        selected_match_type_title = st.selectbox("Match Type", [mt[1] for mt in match_types])
        match_type_id = next(mt[0] for mt in match_types if mt[1] == selected_match_type_title)

        # Show player names and retrieve the selected IDs
        selected_player1_name = st.selectbox("Player 1", [p[1] for p in players])
        player1_id = next(p[0] for p in players if p[1] == selected_player1_name)

        selected_player2_name = st.selectbox("Player 2", [p[1] for p in players])
        player2_id = next(p[0] for p in players if p[1] == selected_player2_name)

        # Submit to add the Fixture to the database
        submitted = st.form_submit_button("Add Fixture")
        if submitted and player1_id != player2_id:  # Ensure players are not the same
            add_fixture(match_type_id, player1_id, player2_id)
            st.success("Fixture added successfully!")
            fixture_form_placeholder.empty()  # Clear form by emptying the placeholder
            st.session_state['form_updated'] = True
        elif submitted and player1_id == player2_id:
            st.error("Player 1 and Player 2 cannot be the same.")

# Add Series
if show_add_series_form:
    st.subheader("Add a New Series")

    series_form_placeholder = st.empty()
    with series_form_placeholder.form(key="add_series_form"):
        series_title = st.text_input("Series Title")

        # Submit to add the Series to the database
        submitted = st.form_submit_button("Add Series")
        if submitted and series_title:
            add_series(series_title)
            st.success(f"Series '{series_title}' added successfully!")
            series_form_placeholder.empty()  # Clear form by emptying the placeholder
            st.rerun()

# 2. ******************************************* SHOW TABLE CONTENTS ******************************************************
if show_series:
    st.subheader("Series in Database")
    series = get_series()

    if series:
        # Prepare data for displaying Series along with their Match Types
        series_data = []
        
        for s in series:
            series_id = s[0]
            series_title = s[1]
            
            # Fetch match types for the current series
            match_types = get_series_match_types(series_id)
            
            # Create a comma-separated string of match type titles
            match_type_titles = ", ".join([match[1] for match in match_types]) if match_types else "No Match Types"
            
            # Append series information along with its match types to the list
            series_data.append({"Series ID": series_id, "Series Title": series_title, "Match Types": match_type_titles})
        
        # Convert the list of dictionaries into a DataFrame
        series_df = pd.DataFrame(series_data)
        
        # Display the DataFrame as a table
        st.table(series_df)
    else:
        st.write("No Series found in the database.")

if show_AZ_list:
    players = list_players_alphabetically()
    st.write("Players A-Z:")
    st.write(players)

if show_AZ_list_and_nicknames:
    #players = list_players_and_nicknames()
    players = get_players_simple()
    num_players = len(players)
    st.write(f"Players and Nicknames A-Z ({num_players}):")  
    
    if players:  # Check if there are players in the list
        st.write(f"### Players List({num_players}):")
        for _, name, nickname in players:
            st.write(f"{name} - {nickname}")
    else:
        st.error("No players available to display.")

if show_fixtures:
    st.subheader("Fixtures in Database:")
    fixtures = get_fixtures()

    if fixtures:
    
        # Convert list of tuples to a DataFrame
        fixture_data = pd.DataFrame(fixtures, columns=["Fixture ID", "Match Type ID", "Player 1 ID", "Player 2 ID", "Completed"])
        
        #st.table(fixture_data)
        
        # Apply basic styling
        styled_fixture_data = fixture_data.style.applymap(
        lambda val: "background-color: lightgreen" if val == "Completed" else "background-color: lightcoral", 
        subset=["Completed"]
    ).set_table_styles([
        {"selector": "thead th", "props": [("background-color", "lightblue"), ("font-weight", "bold")]},
        {"selector": "tbody td", "props": [("border", "1px solid black"), ("text-align", "center")]},
        {"selector": "tr:hover", "props": [("background-color", "lightyellow")]}
    ])
        
        # Render styled DataFrame
        with st.container():
            st.write(styled_fixture_data)
    else:
        st.write("No fixtures found in the database.")
        
if show_fixtures_with_names:
    st.subheader("Fixtures with Names in Database:")
    fixtures = get_fixtures_with_names()

    if fixtures:
        # Convert list of tuples to a DataFrame for table display
        fixture_data = pd.DataFrame(fixtures, columns=["Fixture ID", "Match Type ID", "Player 1", "Player 2", "Completed"])
        st.table(fixture_data)
    else:
        st.write("No fixtures found in the database.")

if show_players:
    st.subheader("Players in Database:")
    players = get_players_full()

    if players:
        # Convert list of tuples to a DataFrame for table display
        players_data = pd.DataFrame(players, columns=["Player ID", "Player Name", "Player NickName", "Email", "Games Played", "AveragePR","CurrentLeague","DaysIdle"])
        st.table(players_data)
    else:
        st.write("No players found in the database.")

if show_match_results:
    st.subheader("Match Results in Database:")
    matchresults = get_match_results()

    if matchresults:
        # Convert list of tuples to a DataFrame for table display
        matchresults_data = pd.DataFrame(matchresults, columns=[
            "MatchResult ID", "Date", "Time Completed", "MatchTypeID",
            "Player1ID", "Player2ID", "Player 1 pts", "Player 2 pts",
            "Player 1 PR", "Player 2 PR", "Player 1 Luck", "Player 2 Luck"
        ])

        # Format date and time columns, if needed
        matchresults_data["Date"] = pd.to_datetime(matchresults_data["Date"]).dt.date
        matchresults_data["Time Completed"] = matchresults_data["Time Completed"].astype(str)

        st.table(matchresults_data)
    else:
        st.write("No match results found in the database.")

if show_match_results_nicely_formatted:
    st.subheader("Match Results Nicely Formatted:")
    matchresults = get_match_results_nicely_formatted()
    if matchresults:
            # Convert list of tuples to a DataFrame for table display
            matchresults_data = pd.DataFrame(matchresults, columns=[
                "MatchResult ID", "Date", "Time Completed", "MatchTypeID",
                "Player1ID", "Player2ID", "Player 1 pts", "Player 2 pts",
                "Player 1 PR", "Player 2 PR", "Player 1 Luck", "Player 2 Luck"
            ])
    
            # Format date and time columns, if needed
            matchresults_data["Date"] = pd.to_datetime(matchresults_data["Date"]).dt.date
            matchresults_data["Time Completed"] = matchresults_data["Time Completed"].astype(str)
    
            st.table(matchresults_data)
    else:
            st.write("No match results found in the database.")

# Update match type view to include 'Active' column
if show_match_types:
    st.subheader("Match Types in Database:")
    matchtypes = get_match_types()
    print("Fetched match types:", matchtypes)
    
    if matchtypes:
        # Convert list of tuples to a DataFrame for table display, including 'Active' column
        matchtypes_data = pd.DataFrame(matchtypes, columns=["MatchType ID", "Match Type Name", "Identifier", "Active"])
        st.table(matchtypes_data)
    else:
        st.write("No match types found in the database.")
    
# 3. *****************************EDITING FORMS************************************************
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
                    st.rerun()

            # Show match types with checkboxes
            st.write("Match Types in this Series:")
            match_types_in_series = [match[0] for match in get_series_match_types(series_id)]
            all_match_types = get_match_types()

            # Display each match type with a checkbox
            updated_match_types = []
            for match_type in all_match_types:
                match_type_id, match_type_title, identifier, active = match_type
                is_checked = st.checkbox(
                    f"{match_type_title} (ID: {match_type_id})",
                    value=(match_type_id in match_types_in_series)
                )
                if is_checked:
                    updated_match_types.append(match_type_id)

            # Submit changes to match types in the series
            if st.button("Update Match Types in Series"):
                # Add new match types and remove unchecked ones
                for match_type_id in updated_match_types:
                    if match_type_id not in match_types_in_series:
                        add_match_type_to_series(series_id, match_type_id)

                for match_type_id in match_types_in_series:
                    if match_type_id not in updated_match_types:
                        remove_match_type_from_series(series_id, match_type_id)

                st.success("Match Types updated in series!")
                st.rerun()
                    
# Editing Players
if edit_players:
    st.subheader("Edit Player")

    # Fetch all players to populate the selectbox
    players = get_players_full()

    if players:
        # Create a dictionary to map player names to their IDs for selection
        try:
            player_dict = {f"{player[1]} (ID: {player[0]})": player for player in players}
            selected_player = st.selectbox("Select Player to Edit", list(player_dict.keys()))
        except Exception as e:
            st.error(f"Error mapping players: {e}")

        if selected_player:
            player_data = player_dict[selected_player]
            player_id = player_data[0]  # Extract the PlayerID

            # Prepopulate form with the selected player's data
            with st.form(key='edit_player_form'):
                name = st.text_input("Name", value=player_data[1] or "")
                nickname = st.text_input("Nickname", value=player_data[2] or "")
                email = st.text_input("Email", value=player_data[3] or "")

                # Form submission
                submitted = st.form_submit_button("Update Player")
                if submitted:
                    # Call update function to update the player in the database
                    update_player(player_id, name, nickname, email)
                    st.success("Player updated successfully!")
                    st.rerun()
                    
# Editing Match Types
if edit_match_types:
    st.subheader("Edit Match Types")

    # Fetch all match types
    matchtypes = get_match_types()
    if matchtypes:
        # Map match type titles to their IDs for selection
        matchtype_dict = {f"{mt[1]} (ID: {mt[0]})": mt for mt in matchtypes}
        selected_matchtype = st.selectbox("Select Match Type to Edit", list(matchtype_dict.keys()))

        if selected_matchtype:
            matchtype_data = matchtype_dict[selected_matchtype]
            matchtype_id = matchtype_data[0]
            matchtype_identifier = matchtype_data[2]  # Get the current identifier

            # Prepopulate the form with selected match type data
            with st.form(key='edit_matchtype_form'):
                active = st.checkbox("Active", value=matchtype_data[3])
                identifier = st.text_input("Match Type Identifier", value=matchtype_identifier)  # Editable identifier

                # Form submission
                submitted = st.form_submit_button("Update Match Type")
                if submitted:
                    update_match_type_status(matchtype_id, active, identifier)  # Pass identifier
                    st.success("Match Type updated successfully!")
                    st.rerun()

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
    st.subheader("Edit Fixtures")

    # Fetch all fixtures
    fixtures = get_fixtures()
    match_types = get_match_types()  # Fetch all match types to display in dropdown
    players = get_players_simple()  # Fetch all players to display in dropdown

    if fixtures:
        # Map fixtures to their IDs for selection
        fixture_dict = {f"Fixture ID {f[0]} (Match Type ID: {f[1]})": f for f in fixtures}
        selected_fixture = st.selectbox("Select Fixture to Edit", list(fixture_dict.keys()))

        if selected_fixture:
            fixture_data = fixture_dict[selected_fixture]
            fixture_id = fixture_data[0]

            # Prepopulate the form with selected fixture data
            with st.form(key='edit_fixture_form'):
                # Dropdown for Match Type
                match_type_id = st.selectbox(
                    "Match Type",
                    options=[(mt[0], mt[1]) for mt in match_types],
                    format_func=lambda x: x[1],
                    index=[mt[0] for mt in match_types].index(fixture_data[1])
                )

                # Dropdowns for Player 1 and Player 2
                player1_id = st.selectbox(
                    "Player 1",
                    options=[(p[0], p[1]) for p in players],
                    format_func=lambda x: x[1],
                    index=[p[0] for p in players].index(fixture_data[2])
                )
                player2_id = st.selectbox(
                    "Player 2",
                    options=[(p[0], p[1]) for p in players],
                    format_func=lambda x: x[1],
                    index=[p[0] for p in players].index(fixture_data[3])
                )

                # Checkbox for completion status
                completed = st.checkbox("Completed", value=fixture_data[4])

                # Form submission
                submitted = st.form_submit_button("Update Fixture")
                if submitted:
                    # Update the fixture with new details
                    update_fixture(
                        fixture_id=fixture_id,
                        match_type_id=match_type_id[0],
                        player1_id=player1_id[0],
                        player2_id=player2_id[0],
                        completed=completed
                    )
                    st.success("Fixture updated successfully!")
                    st.rerun()
    

# Editing Match Results
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

                # Process time_completed directly from the database
                try:
                    if isinstance(match_result_data[2], str):
                        # Parse the string to a datetime.time object
                        time_completed_value = datetime.datetime.strptime(match_result_data[2], '%H:%M:%S').time()
                    elif isinstance(match_result_data[2], datetime.time):
                        # Use the value directly if it's already a time object
                        time_completed_value = match_result_data[2]
                    else:
                        # Default to 00:00 if the value is invalid or None
                        time_completed_value = datetime.time(0, 0)
                except Exception as e:
                    st.error(f"Error processing time_completed: {e}")
                    time_completed_value = datetime.time(0, 0)
                
                # Pass the validated value to the time_input widget
                time_completed = st.time_input("Time Completed", value=time_completed_value)

                match_type_id = st.number_input("Match Type ID", min_value=1, value=match_result_data[3])
                player1_id = st.number_input("Player 1 ID", min_value=1, value=match_result_data[4])
                player2_id = st.number_input("Player 2 ID", min_value=1, value=match_result_data[5])
                player1_points = st.number_input("Player 1 Points", min_value=0, value=match_result_data[6])
                player2_points = st.number_input("Player 2 Points", min_value=0, value=match_result_data[7])
                player1_pr = st.number_input("Player 1 PR", min_value=0.0, value=match_result_data[8])
                player2_pr = st.number_input("Player 2 PR", min_value=0.0, value=match_result_data[9])
                
                # Allow negative values for luck scores
                player1_luck = st.number_input("Player 1 Luck", value=match_result_data[10], step=0.01, format="%.2f")
                player2_luck = st.number_input("Player 2 Luck", value=match_result_data[11], step=0.01, format="%.2f")

                # Submit button
                submitted = st.form_submit_button("Update Match Result")

                if submitted:
                    # Call update function to update the match result in the database
                    update_match_result(
                        match_result_id, date, time_completed, match_type_id, player1_id, player2_id,
                        player1_points, player2_points, player1_pr, player2_pr, player1_luck, player2_luck
                    )
                    st.success("Match result updated successfully!")
                    st.rerun()
    else:
        st.warning("No match results available to edit.")
        
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
