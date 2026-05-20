from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

PASSWORD_DATABASE = {
    "admin": "liam123",
    "parent": "parents2026",
    "student": "bibleheroes"
}

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

@app.route('/admin')
def admin():
    return render_template('admin.html', data=DAILY_CONTENT)

@app.route('/student')
def student():
    return render_template('student.html', data=DAILY_CONTENT)

@app.route('/parent')
def parent():
    return render_template('parent.html', data=DAILY_CONTENT)

if __name__ == '__main__':
    app.run(port=5000, debug=True)