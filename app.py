import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB_FILE = "bible_study.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Base study days table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_number INTEGER UNIQUE,
            title TEXT NOT NULL,
            verse TEXT NOT NULL,
            character_name TEXT NOT NULL,
            kids_mission TEXT NOT NULL,
            is_locked BOOLEAN DEFAULT 1,
            request_pending BOOLEAN DEFAULT 0
        )
    ''')
    
    # 2. Dynamic multi-line tables linked to days
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS character_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id INTEGER,
            fact_text TEXT NOT NULL,
            FOREIGN KEY(day_id) REFERENCES study_days(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS liam_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id INTEGER,
            note_text TEXT NOT NULL,
            FOREIGN KEY(day_id) REFERENCES study_days(id) ON DELETE CASCADE
        )
    ''')
    
    # 3. Dynamic Student Profiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_profiles (
            username TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )
    ''')
    
    # 4. Global App Configuration Settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_state (
            id INTEGER PRIMARY KEY,
            current_active_day_id INTEGER
        )
    ''')
    
    # Seed data if tables are freshly created
    cursor.execute("SELECT COUNT(*) FROM student_profiles")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO student_profiles VALUES ('jude', 'Jude', 450, 4)")
        cursor.execute("INSERT INTO student_profiles VALUES ('beau', 'Beau', 250, 2)")
        
        # Base Seed Day
        cursor.execute('''
            INSERT INTO study_days (day_number, title, verse, character_name, kids_mission, is_locked)
            VALUES (1, 'Day 1: Joshua & Courage', 'Joshua 1:9 - "Be strong and courageous..."', 'Joshua', 'Encourage someone today when they are working hard!', 0)
        ''')
        day_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (day_id, "He was Moses' trusted assistant."))
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (day_id, "He led the Israelites across Jordan."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (day_id, "Read Joshua Chapter 1 out loud."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (day_id, "Explain what a successor is."))
        
        cursor.execute("INSERT INTO app_state (id, current_active_day_id) VALUES (1, ?)", (day_id,))
        conn.commit()
        
    conn.close()

init_db()

PASSWORD_DATABASE = {"admin": "liam123", "parent": "parents2026", "student": "bibleheroes"}

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    role = request.form.get('role')
    password = request.form.get('password')
    if password == PASSWORD_DATABASE.get(role):
        return redirect(url_for(role))
    return "<h1>Incorrect Password!</h1><p><a href='/'>Go back and try again.</a></p>"

# ========================================================
# VIEWS & ACCESS RULES
# ========================================================
@app.route('/student')
def student():
    conn = get_db_connection()
    active_day_row = conn.execute('SELECT current_active_day_id FROM app_state WHERE id = 1').fetchone()
    day_id = active_day_row['current_active_day_id']
    
    day_data = conn.execute('SELECT * FROM study_days WHERE id = ?', (day_id,)).fetchone()
    facts = conn.execute('SELECT * FROM character_facts WHERE day_id = ?', (day_id,)).fetchall()
    profiles = conn.execute('SELECT * FROM student_profiles').fetchall()
    conn.close()
    
    return render_template('student.html', day=day_data, facts=facts, profiles=profiles)

@app.route('/parent')
def parent():
    conn = get_db_connection()
    days = conn.execute('SELECT * FROM study_days ORDER BY day_number ASC').fetchall()
    profiles = conn.execute('SELECT * FROM student_profiles').fetchall()
    conn.close()
    return render_template('parent.html', days=days, profiles=profiles)

@app.route('/admin')
def admin():
    conn = get_db_connection()
    days = conn.execute('SELECT * FROM study_days ORDER BY day_number ASC').fetchall()
    profiles = conn.execute('SELECT * FROM student_profiles').fetchall()
    active_day_row = conn.execute('SELECT current_active_day_id FROM app_state WHERE id = 1').fetchone()
    current_day_id = active_day_row['current_active_day_id'] if active_day_row else None
    
    # Get text notes for whichever day is current
    notes = conn.execute('SELECT * FROM liam_notes WHERE day_id = ?', (current_day_id,)).fetchall()
    conn.close()
    return render_template('admin.html', days=days, profiles=profiles, current_day_id=current_day_id, notes=notes)

# ========================================================
# DATA MODIFICATION HANDLERS (REWARDS & LESSONS)
# ========================================================
@app.route('/admin/reward/<username>', methods=['POST'])
def award_xp(username):
    xp_amount = int(request.form.get('xp', 50))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM student_profiles WHERE username = ?', (username,)).fetchone()
    if user:
        new_xp = user['points'] + xp_amount
        new_level = user['level']
        # Calculate level up threshold milestones
        if new_xp >= (new_level * 150):
            new_level += 1
        conn.execute('UPDATE student_profiles SET points = ?, level = ? WHERE username = ?', (new_xp, new_level, username))
        conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/set_active_day', methods=['POST'])
def set_active_day():
    day_id = request.form.get('day_id')
    conn = get_db_connection()
    conn.execute('UPDATE app_state SET current_active_day_id = ? WHERE id = 1', (day_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/add_day', methods=['POST'])
def add_day():
    day_num = request.form.get('day_number')
    title = request.form.get('title')
    verse = request.form.get('verse')
    char_name = request.form.get('character_name')
    mission = request.form.get('kids_mission')
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO study_days (day_number, title, verse, character_name, kids_mission, is_locked)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (day_num, title, verse, char_name, mission))
        day_id = cursor.lastrowid
        
        # Handle dynamic entry arrays split by lines
        for fact in request.form.get('facts', '').split('\n'):
            if fact.strip():
                cursor.execute('INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)', (day_id, fact.strip()))
        for note in request.form.get('notes', '').split('\n'):
            if note.strip():
                cursor.execute('INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)', (day_id, note.strip()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Prevents duplicate day numbers from crashing database initialization pipelines
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/delete_day/<int:day_id>', methods=['POST'])
def delete_day(day_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM study_days WHERE id = ?', (day_id,))
    conn.execute('DELETE FROM character_facts WHERE day_id = ?', (day_id,))
    conn.execute('DELETE FROM liam_notes WHERE day_id = ?', (day_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

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
