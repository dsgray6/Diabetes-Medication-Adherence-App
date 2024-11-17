import streamlit as st
import datetime
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import calendar

def create_database_connection():
    """Create and return a database connection"""
    try:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / "diabetes_app.db"
        conn = sqlite3.connect(str(db_path))
        
        # Create tables when connecting
        create_tables(conn)
        
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None
# Database Setup
def create_tables(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS medications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  med_name TEXT,
                  dosage REAL,
                  time_taken TIMESTAMP,
                  scheduled_time TIME,
                  date DATE)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS glucose_readings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  glucose_level REAL,
                  reading_time TIMESTAMP)''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS medication_schedule
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  med_name TEXT,
                  scheduled_time TIME,
                  dosage REAL)''')

def calculate_streak(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date FROM medications 
        WHERE user_id = ? 
        ORDER BY date DESC
    """, (user_id,))
    dates = [row[0] for row in cursor.fetchall()]
    
    if not dates:
        return 0
        
    streak = 1
    current_date = datetime.strptime(dates[0], '%Y-%m-%d')
    
    for date_str in dates[1:]:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        if (current_date - date).days == 1:
            streak += 1
            current_date = date
        else:
            break
    
    return streak

def medication_tracker():
    st.header("Medication Tracker")
    
    # Current time display
    current_time = datetime.now().strftime("%H:%M")
    st.subheader(f"Current Time: {current_time}")
    
    # Calendar view
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_date = st.date_input("Select Date", datetime.now())
        
    # Medication Schedule
    st.subheader("Medication Schedule")
    conn = create_database_connection()
    
    if conn is not None:
        # Display scheduled medications
        cursor = conn.cursor()
        cursor.execute("""
            SELECT med_name, scheduled_time, dosage 
            FROM medication_schedule 
            WHERE user_id = ?
        """, (st.session_state.get('user_id', 'default_user'),))
        
        scheduled_meds = cursor.fetchall()
        
        for med in scheduled_meds:
            med_name, scheduled_time, dosage = med
            st.write(f"{med_name} - {scheduled_time} - {dosage} units")
    
    # Add new medication
    with st.expander("Log New Medication"):
        med_name = st.text_input("Medication Name")
        dosage = st.number_input("Dosage", min_value=0.0)
        time_taken = st.time_input("Time Taken")
        
        if st.button("Log Medication"):
            if conn is not None:
                try:
                    with conn:
                        conn.execute("""
                            INSERT INTO medications 
                            (user_id, med_name, dosage, time_taken, date)
                            VALUES (?, ?, ?, ?, ?)
                        """, (st.session_state.get('user_id', 'default_user'),
                              med_name, dosage, time_taken,
                              selected_date))
                    st.success("Medication logged successfully!")
                except Exception as e:
                    st.error(f"Error logging medication: {e}")
                finally:
                    conn.close()
    if st.button("Log Medication"):
        if conn is not None:
            try:
                with conn:
                    # Convert time_taken to string format
                    time_taken_str = time_taken.strftime('%H:%M:%S')
                    conn.execute("""
                        INSERT INTO medications 
                        (user_id, med_name, dosage, time_taken, date)
                        VALUES (?, ?, ?, ?, ?)
                    """, (st.session_state.get('user_id', 'default_user'),
                          med_name, dosage, time_taken_str,
                          selected_date))
                st.success("Medication logged successfully!")
            except Exception as e:
                st.error(f"Error logging medication: {e}")
            finally:
                conn.close()

def glucose_tracker():
    st.subheader("Glucose Tracker")
    
    # Glucose input
    glucose_level = st.number_input("Glucose Level", min_value=0)
    if st.button("Log Glucose"):
        conn = create_database_connection()
        if conn is not None:
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO glucose_readings 
                        (user_id, glucose_level, reading_time)
                        VALUES (?, ?, ?)
                    """, (st.session_state.get('user_id', 'default_user'),
                          glucose_level, datetime.now()))
                st.success("Glucose level logged successfully!")
            except Exception as e:
                st.error(f"Error logging glucose level: {e}")
            finally:
                conn.close()

def display_glucose_chart():
    conn = create_database_connection()
    if conn is not None:
        df = pd.read_sql_query("""
            SELECT glucose_level, reading_time 
            FROM glucose_readings 
            WHERE user_id = ? 
            ORDER BY reading_time
        """, conn, params=(st.session_state.get('user_id', 'default_user'),))
        
        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['reading_time'], 
                                   y=df['glucose_level'],
                                   mode='lines+markers'))
            fig.update_layout(title='Glucose Levels Over Time',
                            xaxis_title='Time',
                            yaxis_title='Glucose Level')
            st.plotly_chart(fig)
        conn.close()

def main():
    st.set_page_config(page_title="Diabetes Support App", layout="wide")
    
    # Initialize session state
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = 'default_user'
    
    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Home", "Medication Tracker", "Glucose Tracker", 
         "Community", "Resources", "Settings"]
    )
    
    if page == "Home":
        st.title("Diabetes Support App")
        st.write("Welcome to your diabetes management assistant!")
        
        # Display streak
        conn = create_database_connection()
        if conn is not None:
            streak = calculate_streak(conn, st.session_state['user_id'])
            st.metric("Current Streak", f"{streak} days")
            conn.close()
        
        # Display today's schedule
        st.subheader("Today's Schedule")
        display_glucose_chart()
        
    elif page == "Medication Tracker":
        medication_tracker()
        
    elif page == "Glucose Tracker":
        glucose_tracker()
        
    elif page == "Community":
        st.title("Community Support")
        st.write("Connect with others in the diabetes community")
        
        # Add community features here
        
    elif page == "Resources":
        st.title("Resources")
        st.write("Educational materials and helpful information")
        
        # Add educational resources here
        
    elif page == "Settings":
        st.title("Settings")
        # Add settings options here
        notification_time = st.time_input("Set Default Reminder Time")
        if st.button("Save Settings"):
            st.success("Settings saved successfully!")
def get_medication_options():
    return ["Insulin", "Metformin", "Glipizide", "Januvia", "Other"]

def medication_tracker():
    # ... existing code ...
    with st.expander("Log New Medication"):
        med_name = st.selectbox("Medication Name", get_medication_options())
        if med_name == "Other":
            med_name = st.text_input("Enter medication name")
def display_medication_calendar(conn, user_id):
    st.subheader("Medication Calendar")
    
    # Get current month's dates
    now = datetime.now()
    cal = calendar.monthcalendar(now.year, now.month)
    
    # Get medication data for the month
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, med_name, dosage, time_taken 
        FROM medications 
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, now.strftime('%Y-%m')))
    med_data = cursor.fetchall()
    
    # Create calendar view
    cols = st.columns(7)
    for idx, day_name in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']):
        cols[idx].write(day_name)
    
    for week in cal:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day != 0:
                # Check if medication was taken on this day
                date_str = f"{now.year}-{now.month:02d}-{day:02d}"
                day_meds = [m for m in med_data if m[0] == date_str]
                
                if day_meds:
                    cols[idx].markdown(f"**{day}** ✅")
                    if cols[idx].button(f"Details {day}", key=f"btn_{date_str}"):
                        st.write(f"Medications taken on {date_str}:")
                        for med in day_meds:
                            st.write(f"- {med[1]}: {med[2]} units at {med[3]}")
                else:
                    cols[idx].write(day)
def update_streak(conn, user_id):
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date FROM medications 
        WHERE user_id = ? AND date = ?
    """, (user_id, yesterday))
    
    if cursor.fetchone():
        # Update streak
        cursor.execute("""
            UPDATE users 
            SET streak = streak + 1 
            WHERE user_id = ?
        """, (user_id,))
    else:
        # Reset streak
        cursor.execute("""
            UPDATE users 
            SET streak = 0 
            WHERE user_id = ?
        """, (user_id,))
    
    conn.commit()
def main():
    st.set_page_config(page_title="Diabetes Support App", layout="wide")
    
    # Add custom CSS
    st.markdown("""
        <style>
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 24px;
            border-radius: 5px;
        }
        .success-message {
            padding: 10px;
            border-radius: 5px;
            background-color: #dff0d8;
            border: 1px solid #d6e9c6;
            color: #3c763d;
        }
        </style>
    """, unsafe_allow_html=True)
if __name__ == "__main__":
    main()