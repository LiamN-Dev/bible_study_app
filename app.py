import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB_FILE = "bible_study.db"

# ========================================================
# 1. YOUR EXACT PASSWORD DATABASE (UNTOUCHED)
# ========================================================
PASSWORD_DATABASE = {
    "admin": "liam123",
    "parent": "parents2026",
    "student": "bibleheroes"
}

# ========================================================
# 2. YOUR EXACT DAILY CONTENT & PROFILES (UNTOUCHED)
# ========================================================
DAILY_CONTENT = {
    "verse": "Joshua 1:9 - \"Be strong and courageous. Do not be afraid; do not be discouraged, for the Lord your God will be with you wherever you go.\"",
    "character_name": "Joshua",
    "character_facts": [
        "He was Moses' trusted assistant before becoming the leader.",
        "He lead the Israelites across the Jordan River into the Promised Land.",
        "He is famous for the battle of Jericho."
    ],
    "kids_mission": "Encourage someone today when they are working hard or playing a game!",
    
    # INDIVIDUAL PROFILES FOR YOUR BROTHERS
    "profiles": {
        "jude": {
            "name": "Jude",
            "age": 9,
            "level": 4,
            "points": 450,
            "badges": [
                {"icon": "🧠", "title": "Memory Champion", "desc": "Recited a full verse perfectly"},
                {"icon": "🛡️", "title": "Courage Badge", "desc": "Completed the Joshua Lesson"},
                {"icon": "🔥", "title": "3-Day Streak", "desc": "Perfect focus 3 days in a row"}
            ]
        },
        "beau": {
            "name": "Beau",
            "age": 7,
            "level": 2,
            "points": 250,
            "badges": [
                {"icon": "🛡️", "title": "Courage Badge", "desc": "Completed the Joshua Lesson"},
                {"icon": "🙏", "title": "Prayer Warrior", "desc": "Led the family closing prayer"}
            ]
        }
    },
    
    "liam_notes": [
        "Read Joshua Chapter 1 out loud with the boys.",
        "Explain what a 'successor' is.",
        "Ask: What is something scary you had to do where you needed courage?",
        "Remind them that being brave means trusting God anyway."
    ],
    
    "parent_summary": "Today we kicked off our study on Joshua. We focused on courage and trusting God's promises.",
    "parent_dinner_question": "Ask the boys what area of their lives they feel like they need the most courage in right now."
}

# ========================================================
# 3. NEW DATABASE LAYER FOR THE RELEASE PIPELINE
# ========================================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Sets up the multi-day schedule tracking table without altering dicts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_number INTEGER UNIQUE,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_locked BOOLEAN DEFAULT 1,
            request_pending BOOLEAN DEFAULT 0
        )
    ''')
    
    # Pre-populate 3 days if the database is brand new
    cursor.execute("SELECT COUNT(*) FROM study_days")
    if cursor.fetchone()[0] == 0:
        sample_days = [
            (1, "Day 1: Introduction to Joshua", "Read Joshua 1:1-9 together. Focus on courage.", 0, 0),
            (2, "Day 2: Spies in Jericho", "Read Joshua 2. Rahab hides the two Israelite spies.", 1, 0),
            (3, "Day 3: Crossing the Jordan", "Read Joshua 3. The water stops when the priests step in.", 1, 0)
        ]
        cursor.executemany('''
            INSERT INTO study_days (day_number, title, content, is_locked, request_pending)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_days)
        conn.commit()
    conn.close()

init_db()

# ========================================================
# 4. YOUR ORIGINAL LOGIN ROUTES (UNTOUCHED)
# ========================================================
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    role = request.form.get('role')
    password = request.form.get('password')
    if password == PASSWORD_DATABASE.get(role):
        return redirect(url_for(role))
    else:
        return "<h1>Incorrect Password!</h1><p><a href='/'>Go back and try again.</a></p>"

@app.route('/student')
def student():
    return render_template('student.html', data=DAILY_CONTENT)

# ========================================================
# 5. UPDATED ACCESSIBLE VIEWS (PASSING BOTH DICT & DATABASE)
# ========================================================
@app.route('/admin')
def admin():
    conn = get_db_connection()
    days = conn.execute('SELECT * FROM study_days ORDER BY day_number ASC').fetchall()
    conn.close()
    # Passes your original daily content dictionary AS WELL AS the database days!
    return render_template('admin.html', data=DAILY_CONTENT, days=days)

@app.route('/parent')
def parent():
    conn = get_db_connection()
    days = conn.execute('SELECT * FROM study_days ORDER BY day_number ASC').fetchall()
    conn.close()
    # Passes your original daily content dictionary AS WELL AS the database days!
    return render_template('parent.html', data=DAILY_CONTENT, days=days)

# ========================================================
# 6. NEW INTERACTION ROUTE HANDLERS
# ========================================================
@app.route('/request_access/<int:day_id>', methods=['POST'])
def request_access(day_id):
    conn = get_db_connection()
    conn.execute('UPDATE study_days SET request_pending = 1 WHERE id = ?', (day_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('parent'))

@app.route('/unlock_day/<int:day_id>', methods=['POST'])
def unlock_day(day_id):
    conn = get_db_connection()
    conn.execute('UPDATE study_days SET is_locked = 0, request_pending = 0 WHERE id = ?', (day_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/lock_day/<int:day_id>', methods=['POST'])
def lock_day(day_id):
    conn = get_db_connection()
    conn.execute('UPDATE study_days SET is_locked = 1 WHERE id = ?', (day_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(port=5000, debug=True)
