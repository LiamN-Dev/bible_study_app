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
    
    # 4. Student Profiles Table
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
    
    # Seed initial data if empty
    cursor.execute("SELECT COUNT(*) FROM student_profiles")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO student_profiles (username, display_name, points, level, praise_count) VALUES ('jude', 'Jude', 0, 1, 0)")
        cursor.execute("INSERT INTO student_profiles (username, display_name, points, level, praise_count) VALUES ('beau', 'Beau', 0, 1, 0)")
        
        cursor.execute('''
            INSERT INTO study_days (day_number, title, verse, character_name, kids_mission, parent_takeaway, is_locked)
            VALUES (1, 'Day 1: The Sword Boot Camp', 'Genesis 1:1', 'The Bible / Navigation', 
                    'Draw your swords! Practice finding Genesis 1:1 three times at home today.', 
                    'We learned the 2-Minute Map Tour (Old vs New Testament) and how chapters/verses work like a GPS address. Help them practice!', 0)
        ''')
        d1_id = cursor.lastrowid
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d1_id, "The Bible is a library of 66 separate books bound together."))
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d1_id, "The Old Testament is the front 3/4; the New Testament is the back 1/4."))
        cursor.execute("INSERT INTO character_facts (day_id, fact_text) VALUES (?, ?)", (d1_id, "The Big Number is the Chapter; the Tiny Number is the Verse."))
        
        cursor.execute("INSERT INTO app_state (id, current_active_day_id) VALUES (1, ?)", (d1_id,))
    
    conn.commit()
    conn.close()

init_db()

PASSWORD_DATABASE = {"admin": "liam123", "parent": "parents2026", "student": "bibleheroes"}

SHOP_CATALOG = {
    # --- BADGES ---
    "aura": {"type": "badge", "name": "Neon Star Aura", "emoji": "✨", "cost": 200, "desc": "Surround your avatar cards with cosmic stardust energy!"},
    "shield": {"type": "badge", "name": "Archangel Aegis Shield", "emoji": "🛡️", "cost": 300, "desc": "Deflect custom server penalties with holy protection."},
    "blade": {"type": "badge", "name": "Legendary Paladin Blade", "emoji": "⚔️", "cost": 400, "desc": "A gleaming celestial sword for master drillers."},
    "crown": {"type": "badge", "name": "Crown of Wisdom", "emoji": "👑", "cost": 500, "desc": "A glowing majestic crown for scripture memory leaders."},
    "dragon": {"type": "badge", "name": "Mythic Dragon Familiar", "emoji": "🐉", "cost": 600, "desc": "Unlock a rare legendary dragon companion pet!"},
    "chariot": {"type": "badge", "name": "Chariot of Fire Rider", "emoji": "🏎️", "cost": 750, "desc": "The highest tier badge for speed drill champs."},
    "lootbox": {"type": "lootbox", "cost": 350, "name": "Mystery Loot Box", "emoji": "🎁", "desc": "Roll for a surprise rare laser dino or diamond item!"},
    
    # --- NAME COLORS ---
    "color_fire": {"type": "color", "value": "#ff4500", "style": "glow", "cost": 300, "name": "🔥 Lava Flame Text", "desc": "Turn your display text into burning volcanic orange!"},
    "color_neon_green": {"type": "color", "value": "#39ff14", "style": "glow", "cost": 400, "name": "🟢 Cyber Neon Green", "desc": "Light up the profile board with intense green matrix code!"},
    "color_laser_blue": {"type": "color", "value": "#00d2ff", "style": "glow", "cost": 500, "name": "⚡ Laser Blue Glow", "desc": "Makes your rank card overflow with crackling electricity!"},
    "color_glitch_pink": {"type": "color", "value": "#ff007f", "style": "glow", "cost": 600, "name": "💖 Glitch Pink Glow", "desc": "Ultra-rare glowing arcade pink cosmetics."},
    
    # --- COOL RANK PREFIX TAGS ---
    "title_space_cadet": {"type": "title", "value": "🚀[SPACE RANGER] ", "cost": 350, "name": "[SPACE RANGER] Tag", "desc": "Puts an astronaut badge right before your name."},
    "title_superhero": {"type": "title", "value": "⚡[SUPER HERO] ", "cost": 450, "name": "[SUPER HERO] Tag", "desc": "Unlock elite superhero styling on the roster dashboard."},
    "title_ninja": {"type": "title", "value": "🥷[NINJA] Rank Tag", "cost": 550, "name": "[NINJA] Rank Tag", "desc": "Add a stealth ninja title prefix to your user card."},
    "title_megaboss": {"type": "title", "value": "👑[MEGA BOSS] ", "cost": 700, "name": "[MEGA BOSS] Tag", "desc": "The ultimate title tag for high-score legendary leaders."}
}

LOOTBOX_POOL = [
    {"name": "Laser Dino", "emoji": "🦖"},
    {"name": "Golden Crown", "emoji": "👑"},
    {"name": "Lightning Falcon", "emoji": "🦅"},
    {"name": "Ninja Star", "emoji": "⭐"},
    {"name": "Diamond Shield", "emoji": "💎"}
]

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    role = request.form.get('role')
    password = request.form.get('password')
    if password == PASSWORD_DATABASE.get(role):
        return jsonify({"success": True, "redirect_url": url_for(role)})
    return jsonify({"success": False, "message": "Incorrect security key. Try again!"})

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
    return render_template('student.html', day=day_data, facts=facts, profiles=profiles, shopper=shopper_data, catalog=SHOP_CATALOG)

@app.route('/student/change_shopper', methods=['POST'])
def change_shopper():
    selected_kid = request.form.get('shopper_username')
    response = make_response(redirect(url_for('student')))
    if selected_kid:
        response.set_cookie('active_shopper', selected_kid, max_age=60*60*24*7)
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

@app.route('/parent/day/<day_id>')
def parent_day_view(day_id):
    conn = get_db_connection()
    day = conn.execute('SELECT * FROM study_days WHERE id = ? or day_number = ?', (day_id, day_id)).fetchone()
    if not day:
        conn.close()
        return "<h1>⚠️ Lesson Module Not Found</h1>", 404
    if day['is_locked']:
        conn.close()
        return "<h1>🔒 Lesson Module Locked!</h1><p><a href='/parent'>Return to Dashboard</a></p>"
        
    facts = conn.execute('SELECT * FROM character_facts WHERE day_id = ?', (day['id'],)).fetchall()
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
    requests = conn.execute('SELECT * FROM study_days WHERE request_pending = 1').fetchall()
    conn.close()
    return render_template('admin.html', days=days, profiles=profiles, current_day_id=current_day_id, requests=requests)

@app.route('/parent/praise/<username>', methods=['POST'])
def parent_praise(username):
    conn = get_db_connection()
    conn.execute('UPDATE student_profiles SET praise_count = praise_count + 1 WHERE username = ?', (username,))
    conn.commit()
    updated = conn.execute('SELECT praise_count FROM student_profiles WHERE username = ?', (username,)).fetchone()
    conn.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "praise_count": updated['praise_count']})
    return redirect(url_for('parent'))

@app.route('/admin/adjust_stars/<username>/<action>', methods=['POST'])
def admin_adjust_praise(username, action):
    conn = get_db_connection()
    if action == 'add':
        conn.execute('UPDATE student_profiles SET praise_count = praise_count + 1 WHERE username = ?', (username,))
    elif action == 'remove':
        conn.execute('UPDATE student_profiles SET praise_count = MAX(0, praise_count - 1) WHERE username = ?', (username,))
    conn.commit()
    updated = conn.execute('SELECT praise_count FROM student_profiles WHERE username = ?', (username,)).fetchone()
    conn.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "praise_count": updated['praise_count']})
    return redirect(url_for('admin'))

@app.route('/admin/adjust_xp/<username>', methods=['POST'])
def admin_adjust_xp(username):
    xp_amount = int(request.form.get('xp_amount', 0))
    action = request.form.get('action', 'add')
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM student_profiles WHERE username = ?', (username,)).fetchone()
    if user:
        new_xp = user['points'] + xp_amount if action == 'add' else max(0, user['points'] - xp_amount)
        new_level = user['level']
        if action == 'add' and xp_amount > 0 and new_xp >= (new_level * 150):
            new_level = (new_xp // 150) + 1
        elif action == 'deduct' and new_xp < ((new_level - 1) * 150) and new_level > 1:
            new_level = max(1, (new_xp // 150) + 1)
        conn.execute('UPDATE student_profiles SET points = ?, level = ? WHERE username = ?', (new_xp, new_level, username))
        conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/student/purchase_item/<username>', methods=['POST'])
def student_purchase_item(username):
    item_key = request.form.get('item_key')
    if item_key not in SHOP_CATALOG:
        return redirect(url_for('student'))
        
    selected_item = SHOP_CATALOG[item_key]
    cost = selected_item['cost']
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM student_profiles WHERE username = ?', (username,)).fetchone()
    
    success = False
    msg = "Insufficient balance!"
    
    if user and user['points'] >= cost:
        success = True
        new_points = user['points'] - cost
        conn.execute('UPDATE student_profiles SET points = ? WHERE username = ?', (new_points, username))
        
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
        msg = f"Successfully unlocked {selected_item.get('name', 'item')}!"
        
    conn.close()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": success, "message": msg})
    return redirect(url_for('student'))

@app.route('/admin/process_purchase', methods=['POST'])
def admin_process_purchase():
    username = request.form.get('username')
    reward_item = request.form.get('reward_item')
    if not username or not reward_item:
        return redirect(url_for('admin'))
        
    item_key, cost_str = reward_item.split('|')
    cost = int(cost_str)
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM student_profiles WHERE username = ?', (username,)).fetchone()
    if user and user['points'] >= cost:
        new_points = user['points'] - cost
        conn.execute('UPDATE student_profiles SET points = ? WHERE username = ?', (new_points, username))
        if item_key == 'lootbox':
            rolled = random.choice(LOOTBOX_POOL)
            conn.execute('INSERT INTO badges (username, badge_name, emoji) VALUES (?, ?, ?)', (username, f"Lootbox: {rolled['name']}", rolled['emoji']))
        elif item_key == 'title':
            conn.execute('UPDATE student_profiles SET player_title = ? WHERE username = ?', ("👑[MEGA BOSS] ", username))
        elif item_key == 'theme':
            conn.execute('UPDATE student_profiles SET name_color = ?, name_style = ? WHERE username = ?', ("#ff007f", "glow", username))
        elif item_key == 'emoji':
            conn.execute('INSERT INTO badges (username, badge_name, emoji) VALUES (?, ?, ?)', (username, "Emoji Pack", "💬"))
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

if __name__ == '__main__':
    app.run(port=5000, debug=True)
