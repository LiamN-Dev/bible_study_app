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
    
    # 1. Main Study Days Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_number INTEGER UNIQUE,
            title TEXT NOT NULL,
            verse TEXT NOT NULL,
            character_name TEXT NOT NULL,
            kids_mission TEXT NOT NULL,
            parent_takeaway TEXT DEFAULT 'No special parent takeaways added yet.',
            is_locked BOOLEAN DEFAULT 1,
            request_pending BOOLEAN DEFAULT 0
        )
    ''')
    
    # 2. Character Facts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS character_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id INTEGER,
            fact_text TEXT NOT NULL,
            FOREIGN KEY(day_id) REFERENCES study_days(id) ON DELETE CASCADE
        )
    ''')
    
    # 3. Teaching Notes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS liam_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id INTEGER,
            note_text TEXT NOT NULL,
            FOREIGN KEY(day_id) REFERENCES study_days(id) ON DELETE CASCADE
        )
    ''')
    
    # 4. Student Profiles Table (Fresh Seed Data!)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_profiles (
            username TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )
    ''')
    
    # 5. NEW: Badges Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            badge_name TEXT NOT NULL,
            emoji TEXT DEFAULT '🏆',
            FOREIGN KEY(username) REFERENCES student_profiles(username) ON DELETE CASCADE
        )
    ''')
    
    # 6. Global Active State Tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_state (
            id INTEGER PRIMARY KEY,
            current_active_day_id INTEGER
        )
    ''')
    
    # Seed profiles and initial configurations if completely empty
    cursor.execute("SELECT COUNT(*) FROM student_profiles")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO student_profiles VALUES ('jude', 'Jude', 0, 1)")
        cursor.execute("INSERT INTO student_profiles VALUES ('beau', 'Beau', 0, 1)")
        
        # Initial Seed Day 1 Setup
        cursor.execute('''
            INSERT INTO study_days (day_number, title, verse, character_name, kids_mission, parent_takeaway, is_locked)
            VALUES (1, 'Day 1: Joshua & Courage', 'Joshua 1:9 - "Be strong and courageous..."', 'Joshua', 'Encourage someone today when they are working hard!', 'Help your kids spot moments where they can choose courage over fear today.', 0)
        ''')
        day_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (day_id, "He was Moses' trusted assistant."))
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (day_id, "He successfully led Israel into the Promised Land."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (day_id, "Read Joshua Chapter 1 together."))
        
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
# PORTALS & ROUTING MODULES
# ========================================================
@app.route('/student')
def student():
    conn = get_db_connection()
    active_day_row = conn.execute('SELECT current_active_day_id FROM app_state WHERE id = 1').fetchone()
    day_id = active_day_row['current_active_day_id']
    
    day_data = conn.execute('SELECT * FROM study_days WHERE id = ?', (day_id,)).fetchone()
    facts = conn.execute('SELECT * FROM character_facts WHERE day_id = ?', (day_id,)).fetchall()
    
    # Fetch student listings alongside earned achievements
    profiles_raw = conn.execute('SELECT * FROM student_profiles').fetchall()
    profiles = []
    for p in profiles_raw:
        p_dict = dict(p)
        p_dict['badges'] = conn.execute('SELECT * FROM badges WHERE username = ?', (p['username'],)).fetchall()
        profiles.append(p_dict)
        
    conn.close()
    return render_template('student.html', day=day_data, facts=facts, profiles=profiles)

@app.route('/parent')
def parent():
    conn = get_db_connection()
    days = conn.execute('SELECT * FROM study_days ORDER BY day_number ASC').fetchall()
    
    profiles_raw = conn.execute('SELECT * FROM student_profiles').fetchall()
    profiles = []
    for p in profiles_raw:
        p_dict = dict(p)
        p_dict['badges'] = conn.execute('SELECT * FROM badges WHERE username = ?', (p['username'],)).fetchall()
        profiles.append(p_dict)
        
    conn.close()
    return render_template('parent.html', days=days, profiles=profiles)

@app.route('/parent/day/<int:day_id>')
def parent_day_view(day_id):
    conn = get_db_connection()
    day = conn.execute('SELECT * FROM study_days WHERE id = ?', (day_id,)).fetchone()
    
    # Security Rule: If a lesson is locked, parents cannot view this detail page directly
    if day and day['is_locked']:
        conn.close()
        return "<h1>🔒 Lesson Module Locked!</h1><p>You must wait for admin clearance to view these materials.</p><p><a href='/parent'>Return to Dashboard</a></p>"
        
    facts = conn.execute('SELECT * FROM character_facts WHERE day_id = ?', (day_id,)).fetchall()
    conn.close()
    return render_template('parent_day.html', day=day, facts=facts)

@app.route('/admin')
def admin():
    conn = get_db_connection()
    days = conn.execute('SELECT * FROM study_days ORDER BY day_number ASC').fetchall()
    
    profiles_raw = conn.execute('SELECT * FROM student_profiles').fetchall()
    profiles = []
    for p in profiles_raw:
        p_dict = dict(p)
        p_dict['badges'] = conn.execute('SELECT * FROM badges WHERE username = ?', (p['username'],)).fetchall()
        profiles.append(p_dict)
        
    active_day_row = conn.execute('SELECT current_active_day_id FROM app_state WHERE id = 1').fetchone()
    current_day_id = active_day_row['current_active_day_id'] if active_day_row else None
    
    notes = conn.execute('SELECT * FROM liam_notes WHERE day_id = ?', (current_day_id,)).fetchall()
    conn.close()
    return render_template('admin.html', days=days, profiles=profiles, current_day_id=current_day_id, notes=notes)

# ========================================================
# ENGINE MANAGEMENT PORTS (REWARDS, BADGES, & ACTIONS)
# ========================================================
@app.route('/admin/reward/<username>', methods=['POST'])
def award_xp(username):
    xp_amount = int(request.form.get('xp', 50))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM student_profiles WHERE username = ?', (username,)).fetchone()
    if user:
        new_xp = user['points'] + xp_amount
        new_level = user['level']
        # Level up threshold benchmark
        if new_xp >= (new_level * 150):
            new_level += 1
        conn.execute('UPDATE student_profiles SET points = ?, level = ? WHERE username = ?', (new_xp, new_level, username))
        conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/admin/award_badge/<username>', methods=['POST'])
def award_badge(username):
    badge_name = request.form.get('badge_name')
    emoji = request.form.get('emoji', '🏆')
    if badge_name:
        conn = get_db_connection()
        conn.execute('INSERT INTO badges (username, badge_name, emoji) VALUES (?, ?, ?)', (username, badge_name.strip(), emoji))
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
    parent_takeaway = request.form.get('parent_takeaway', 'No special parent takeaways added yet.')
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO study_days (day_number, title, verse, character_name, kids_mission, parent_takeaway, is_locked)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (day_num, title, verse, char_name, mission, parent_takeaway))
        day_id = cursor.lastrowid
        
        for fact in request.form.get('facts', '').split('\n'):
            if fact.strip():
                cursor.execute('INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)', (day_id, fact.strip()))
        for note in request.form.get('notes', '').split('\n'):
            if note.strip():
                cursor.execute('INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)', (day_id, note.strip()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
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
