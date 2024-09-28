import mysql.connector
import streamlit as st

def create_connection():
    try:
        conn = mysql.connector.connect(
            host="sql58.jnb2.host-h.net",
            user="sabga_admin",
            password="6f5f73102v7Y1A",
            database="sabga_test"
        )
        if conn.is_connected():
            st.success("Connected to the database!")
        return conn
    except mysql.connector.Error as e:
        st.error(f"Error connecting to the database: {e}")
        return None

def test_database_connection():
    conn = create_connection()
    if conn:
        cursor = conn.cursor()

        # Query to show all tables
        try:
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            st.write("Tables in the database:", tables)

            # Run a simple query to test fetching data (assuming Players table exists)
            cursor.execute("SELECT * FROM Players LIMIT 5;")
            rows = cursor.fetchall()
            if rows:
                st.write("Sample data from Players table:")
                st.write(rows)
            else:
                st.write("Players table is empty or doesn't exist.")
        except Exception as e:
            st.error(f"Error querying the database: {e}")
        finally:
            conn.close()

# Run the test
st.title("Test MySQL Database Connection")
test_database_connection()
