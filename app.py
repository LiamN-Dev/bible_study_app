import sqlite3
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response

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
    
    # 4. Student Profiles Table (Upgraded dynamically with Cosmetic properties)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_profiles (
            username TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            praise_count INTEGER DEFAULT 0
        )
    ''')

    # DYNAMIC COLUMNS UPGRADE SAFE ENGINE
    # This automatically updates your existing live database columns safely without wiping data!
    cursor.execute("PRAGMA table_info(student_profiles)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'name_color' not in columns:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN name_color TEXT DEFAULT '#ffffff'")
    if 'name_style' not in columns:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN name_style TEXT DEFAULT 'normal'")
    if 'player_title' not in columns:
        cursor.execute("ALTER TABLE student_profiles ADD COLUMN player_title TEXT DEFAULT ''")
    
    # 5. Badges Table
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
        cursor.execute("INSERT INTO student_profiles (username, display_name, points, level, praise_count) VALUES ('jude', 'Jude', 0, 1, 0)")
        cursor.execute("INSERT INTO student_profiles (username, display_name, points, level, praise_count) VALUES ('beau', 'Beau', 0, 1, 0)")
        
        # --- AUTOMATED CURRICULUM DATA ---
        cursor.execute('''
            INSERT INTO study_days (day_number, title, verse, character_name, kids_mission, parent_takeaway, is_locked)
            VALUES (1, 'Day 1: The Sword Boot Camp', 'Genesis 1:1', 'The Bible / Navigation', 
                    'Draw your swords! Practice finding Genesis 1:1 three times at home today.', 
                    'We learned the 2-Minute Map Tour (Old vs New Testament) and how chapters/verses work like a GPS address (Book -> Chapter -> Verse). Help them practice flipping to the Table of Contents if they get stuck!', 0)
        ''')
        d1_id = cursor.lastrowid
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d1_id, "The Bible is a library of 66 separate books bound together."))
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d1_id, "The Old Testament is the front 3/4; the New Testament is the back 1/4."))
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d1_id, "The Big Number is the Chapter; the Tiny Number is the Verse."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (d1_id, "Map Tour: Front 3/4 is Old Testament, back 1/4 is New Testament. Use Table of Contents as a cheat sheet."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (d1_id, "GPS Code explanation: Genesis 1:1 is Book -> Chapter (Big) -> Verse (Tiny). Like City -> Street -> House."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (d1_id, "Game Rules: Hold Bibles flat on palms above heads. Shout 'Draw your swords! Find Genesis 1:1... CHARGE!' Run 3 practice rounds."))

        # Day 2 Setup
        cursor.execute('''
            INSERT INTO study_days (day_number, title, verse, character_name, kids_mission, parent_takeaway, is_locked)
            VALUES (2, 'Day 2: Creation & The Sneaky Snake', 'Genesis 1:1 & Genesis 3:1', 'Adam, Eve & The Snake', 
                    'If you could ask God to create one brand new animal right now, what would it look like?', 
                    'We covered Genesis 1 and 3 today—how God made a perfect world, how sin entered through a trick, and God''s immediate promise that a Savior would come defeat the snake.', 1)
        ''')
        d2_id = cursor.lastrowid
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d2_id, "God speaks and creates everything out of absolutely nothing."))
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d2_id, "God looks at everything He made and says, 'It is very good!'"))
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d2_id, "A sneaky snake (Satan) tricks Adam and Eve into breaking God's one rule, bringing sin into the world."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (d2_id, "Bible Search target: Genesis Chapters 1 & 3."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (d2_id, "Sword Drill Challenge: Race to find Genesis 1:1 and Genesis 3:1."))
        cursor.execute("INSERT INTO liam_notes (day_id, note_text) VALUES (?, ?)", (d2_id, "Emphasize: Even right when things got broken, God promised a Savior would come to defeat the snake one day."))

        cursor.execute("INSERT INTO app_state (id, current_active_day_id) VALUES (1, ?)", (d1_id,))
    
    cursor.execute("SELECT COUNT(*) FROM app_state WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM study_days ORDER BY day_number ASC LIMIT 1")
        first_day = cursor.fetchone()
        first_day_id = first_day['id'] if first_day else None
        cursor.execute("INSERT INTO app_state (id, current_active_day_id) VALUES (1, ?)", (first_day_id,))

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
        return jsonify({"success": True, "redirect_url": url_for(role)})
    else:
        return jsonify({"success": False, "message": f"Incorrect security key for {role.upper()} portal. Please try again!"})

# ========================================================
# PORTALS & ROUTING MODULES
# ========================================================
@app.route('/student')
def student():
    conn = get_db_connection()
    active_day_row = conn.execute('SELECT current_active_day_id FROM app_state WHERE id = 1').fetchone()
    day_id = active_day_row['current_active_day_id'] if active_day_row else None
    
    day_data = None
    facts = []
    if day_id:
        day_data = conn.execute('SELECT * FROM study_days WHERE id = ?', (day_id,)).fetchone()
        facts = conn.execute('SELECT * FROM character_facts WHERE day_id = ?', (day_id,)).fetchall()
        
    profiles_raw = conn.execute('SELECT * FROM student_profiles').fetchall()
    profiles = []
    for p in profiles_raw:
        p_dict = dict(p)
        p_dict['badges'] = conn.execute('SELECT * FROM badges WHERE username = ?', (p['username'],)).fetchall()
        profiles.append(p_dict)
        
    # Get who is currently shopping from cookies, default to the first user found if not set
    active_shopper_username = request.cookies.get('active_shopper')
    if not active_shopper_username and profiles:
        active_shopper_username = profiles[0]['username']
        
    shopper_data = None
    for p in profiles:
        if p['username'] == active_shopper_username:
            shopper_data = p
            break
    if not shopper_data and profiles:
        shopper_data = profiles[0]

    conn.close()
    return render_template('student.html', day=day_data, facts=facts, profiles=profiles, shopper=shopper_data)

# Route to change which kid is looking at the store page
@app.route('/student/change_shopper', methods=['POST'])
def change_shopper():
    selected_kid = request.form.get('shopper_username')
    response = make_response(redirect(url_for('student')))
    if selected_kid:
        response.set_cookie('active_shopper', selected_kid, max_age=60*60*24*7) # Save choice for a week
    return response

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
    
    all_notes_raw = conn.execute('''
        SELECT liam_notes.*, study_days.day_number, study_days.title 
        FROM liam_notes 
        JOIN study_days ON liam_notes.day_id = study_days.id
        ORDER BY study_days.day_number ASC
    ''').fetchall()
    
    notes_by_day = {}
    for note in all_notes_raw:
        d_id = note['day_id']
        if d_id not in notes_by_day:
            notes_by_day[d_id] = {
                'title': f"Day {note['day_number']}: {note['title']}",
                'items': []
            }
        notes_by_day[d_id]['items'].append(note['note_text'])
        
    conn.close()
    return render_template('admin.html', days=days, profiles=profiles, 
                           current_day_id=current_day_id, notes_by_day=notes_by_day)

# ========================================================
# ADVANCED MECHANICS ENGINE (REWORKED PRAISE & ULTRA SHOP)
# ========================================================

@app.route('/parent/praise/<username>', methods=['POST'])
def parent_praise(username):
    conn = get_db_connection()
    conn.execute('UPDATE student_profiles SET praise_count = praise_count + 1 WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    return redirect(url_for('parent'))

@app.route('/admin/adjust_praise/<username>/<action>', methods=['POST'])
def admin_adjust_praise(username, action):
    conn = get_db_connection()
    if action == 'add':
        conn.execute('UPDATE student_profiles SET praise_count = praise_count + 1 WHERE username = ?', (username,))
    elif action == 'remove':
        conn.execute('UPDATE student_profiles SET praise_count = MAX(0, praise_count - 1) WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# REWORKED: Total Kid-Friendly Shop Matrix Engine 
@app.route('/student/purchase_item/<username>', methods=['POST'])
def student_purchase_item(username):
    # Expanded kid-friendly store database matrix (Tags, colors, items!)
    SHOP_CATALOG = {
        # --- BADGES ---
        "dragon": {"type": "badge", "name": "Mythic Dragon Familiar", "emoji": "🐉", "cost": 600},
        "blade": {"type": "badge", "name": "Legendary Paladin Blade", "emoji": "⚔️", "cost": 400},
        "shield": {"type": "badge", "name": "Archangel Aegis Shield", "emoji": "🛡️", "cost": 300},
        "crown": {"type": "badge", "name": "Crown of Wisdom", "emoji": "👑", "cost": 500},
        "chariot": {"type": "badge", "name": "Chariot of Fire Rider", "emoji": "🏎️", "cost": 750},
        "aura": {"type": "badge", "name": "Neon Star Aura", "emoji": "✨", "cost": 200},
        "lootbox": {"type": "lootbox", "cost": 350},
        
        # --- NAME COLORS ---
        "color_fire": {"type": "color", "value": "#ff4500", "style": "glow", "cost": 300},
        "color_neon_green": {"type": "color", "value": "#39ff14", "style": "glow", "cost": 400},
        "color_laser_blue": {"type": "color", "value": "#00d2ff", "style": "glow", "cost": 500},
        "color_glitch_pink": {"type": "color", "value": "#ff007f", "style": "glow", "cost": 600},
        
        # --- COOL RANK PREFIX TAGS ---
        "title_superhero": {"type": "title", "value": "⚡[SUPER HERO] ", "cost": 450},
        "title_ninja": {"type": "title", "value": "🥷[NINJA] ", "cost": 550},
        "title_megaboss": {"type": "title", "value": "👑[MEGA BOSS] ", "cost": 700},
        "title_space_cadet": {"type": "title", "value": "🚀[SPACE RANGER] ", "cost": 350}
    }
    
    LOOTBOX_POOL = [
        {"name": "Laser Dino", "emoji": "🦖"},
        {"name": "Golden Crown", "emoji": "👑"},
        {"name": "Lightning Falcon", "emoji": "🦅"},
        {"name": "Ninja Star", "emoji": "⭐"},
        {"name": "Diamond Shield", "emoji": "💎"}
    ]
    
    item_key = request.form.get('item_key')
    if item_key not in SHOP_CATALOG:
        return redirect(url_for('student'))
        
    selected_item = SHOP_CATALOG[item_key]
    cost = selected_item['cost']
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM student_profiles WHERE username = ?', (username,)).fetchone()
    
    if user and user['points'] >= cost:
        new_points = user['points'] - cost
        
        # 1. Update Core Points Wallet Balance
        conn.execute('UPDATE student_profiles SET points = ? WHERE username = ?', (new_points, username))
        
        # 2. Process specific style unlock actions
        if selected_item['type'] == 'badge':
            conn.execute('INSERT INTO badges (username, badge_name, emoji) VALUES (?, ?, ?)', 
                         (username, selected_item['name'], selected_item['emoji']))
                         
        elif selected_item['type'] == 'lootbox':
            rolled_reward = random.choice(LOOTBOX_POOL)
            conn.execute('INSERT INTO badges (username, badge_name, emoji) VALUES (?, ?, ?)', 
                         (username, f"Lootbox: {rolled_reward['name']}", rolled_reward['emoji']))
                         
        elif selected_item['type'] == 'color':
            conn.execute('UPDATE student_profiles SET name_color = ?, name_style = ? WHERE username = ?',
                         (selected_item['value'], selected_item['style'], username))
                         
        elif selected_item['type'] == 'title':
            conn.execute('UPDATE student_profiles SET player_title = ? WHERE username = ?',
                         (selected_item['value'], username))
                         
        conn.commit()
        
    conn.close()
    return redirect(url_for('student'))

@app.route('/admin/reward/<username>', methods=['POST'])
def award_xp(username):
    xp_amount = int(request.form.get('xp', 50))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM student_profiles WHERE username = ?', (username,)).fetchone()
    if user:
        new_xp = user['points'] + xp_amount
        if new_xp < 0: 
            new_xp = 0 
            
        new_level = user['level']
        if xp_amount > 0 and new_xp >= (new_level * 150):
            new_level += 1
        elif xp_amount < 0 and new_xp < ((new_level - 1) * 150) and new_level > 1:
            new_level -= 1
            
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
        
        cursor.execute("SELECT current_active_day_id FROM app_state WHERE id = 1")
        current_active = cursor.fetchone()
        if current_active and current_active['current_active_day_id'] is None:
            cursor.execute("UPDATE app_state SET current_active_day_id = ? WHERE id = 1", (day_id,))
        
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
    
    active_day_row = conn.execute('SELECT current_active_day_id FROM app_state WHERE id = 1').fetchone()
    if active_day_row and active_day_row['current_active_day_id'] == day_id:
        next_day = conn.execute('SELECT id FROM study_days ORDER BY day_number ASC LIMIT 1').fetchone()
        next_id = next_day['id'] if next_day else None
        conn.execute('UPDATE app_state SET current_active_day_id = ? WHERE id = 1', (next_id,))
        
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
