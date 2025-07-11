# init_user_db.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "user_data.db")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Users table
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT,
    year_group TEXT,
    subjects TEXT,
    last_active TIMESTAMP
)
""")

# Interactions table
c.execute("""
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    role TEXT,
    message TEXT,
    topic TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Scores table
c.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    topic TEXT,
    score INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()
print("Database initialized.")
