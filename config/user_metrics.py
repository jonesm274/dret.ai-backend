# user_metrics.py
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "user_data.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

# --- User Management ---
def create_or_update_user(user_id, name=None, year_group=None, subjects=None):
    conn = get_connection()
    c = conn.cursor()
    subjects_str = ",".join(subjects) if subjects else None
    
    # Try to insert, or update if exists
    c.execute('''
        INSERT INTO users (id, name, year_group, subjects, last_active)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            year_group=excluded.year_group,
            subjects=excluded.subjects,
            last_active=excluded.last_active
    ''', (user_id, name, year_group, subjects_str, datetime.utcnow()))

    conn.commit()
    conn.close()

# --- Interactions ---
def log_interaction(user_id, role, message, topic=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO interactions (user_id, role, message, topic)
        VALUES (?, ?, ?, ?)
    ''', (user_id, role, message, topic))

    # Update last active
    c.execute('''
        UPDATE users SET last_active = ? WHERE id = ?
    ''', (datetime.utcnow(), user_id))

    conn.commit()
    conn.close()

# --- Scores ---
def log_score(user_id, topic, score):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO scores (user_id, topic, score)
        VALUES (?, ?, ?)
    ''', (user_id, topic, score))

    conn.commit()
    conn.close()

# --- Queries ---
def get_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_interactions(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM interactions WHERE user_id = ? ORDER BY timestamp ASC', (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def get_user_scores(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM scores WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
    scores = c.fetchall()
    conn.close()
    return scores