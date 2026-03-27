from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import uuid

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#databaseee
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        date TEXT,
        description TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        filename TEXT
    )
    """)

    # admin loginn
    c.execute("INSERT OR IGNORE INTO users (username,password,role) VALUES (?,?,?)",
              ("admin", "admin123", "admin"))

    conn.commit()
    conn.close()

init_db()

 # home page 
@app.route("/")
def home():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM events ORDER BY id DESC LIMIT 3")
    events = c.fetchall()

    event_data = []

    for event in events:
        c.execute("SELECT filename FROM images WHERE event_id=? LIMIT 4", (event[0],))
        images = c.fetchall()
        event_data.append({"event": event, "images": images})

    conn.close()

    return render_template("home.html", event_data=event_data)


#loginn
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[3]

            if user[3] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("home"))

        return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


#admin page
@app.route("/admin")
def admin_dashboard():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    return render_template("admin.html")


#add event
@app.route("/add_event", methods=["GET", "POST"])
def add_event():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        date = request.form["date"]
        description = request.form["description"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO events (title,category,date,description) VALUES (?,?,?,?)",
                  (title, category, date, description))
        event_id = c.lastrowid

        images = request.files.getlist("images")
        for image in images:
            if image.filename:
                unique_name = str(uuid.uuid4()) + "_" + image.filename
                image.save(os.path.join(UPLOAD_FOLDER, unique_name))
                c.execute("INSERT INTO images (event_id,filename) VALUES (?,?)",
                          (event_id, unique_name))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_dashboard"))

    return render_template("add_event.html")


#event page
@app.route("/events")
def events_page():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM events ORDER BY id DESC")
    events = c.fetchall()
    conn.close()
    return render_template("events.html", events=events)


#full gallery
@app.route("/event/<int:event_id>")
def event_gallery(event_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM events WHERE id=?", (event_id,))
    event = c.fetchone()

    c.execute("SELECT filename FROM images WHERE event_id=?", (event_id,))
    images = c.fetchall()

    conn.close()

    return render_template("event_gallery.html", event=event, images=images)


#event delete
@app.route("/delete_event/<int:event_id>")
def delete_event(event_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("DELETE FROM images WHERE event_id=?", (event_id,))
    c.execute("DELETE FROM events WHERE id=?", (event_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                      (username, password, "user"))
            conn.commit()
        except:
            return "Username already exists"

        conn.close()
        return redirect(url_for("login"))

    return render_template("signup.html")

if __name__ == "__main__":
    app.run(debug=True)