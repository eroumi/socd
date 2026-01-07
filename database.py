import sqlite3
import os
import time
import logging

DATABASE_FILE = os.getenv("DATABASE_FILE", "sentinel.db")
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS bans (id INTEGER PRIMARY KEY, user_id INTEGER, moderator_id INTEGER, reason TEXT, timestamp INTEGER, active BOOLEAN DEFAULT 1)")
    cursor.execute("CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY, user_id INTEGER, moderator_id INTEGER, reason TEXT, timestamp INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS timeouts (id INTEGER PRIMARY KEY, user_id INTEGER, moderator_id INTEGER, reason TEXT, timestamp INTEGER, expires_at INTEGER, active BOOLEAN DEFAULT 1)")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        channel_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'open'
    );
    """)
    conn.commit()
    conn.close()
    logger.info("Veritabanı başlatıldı ve tablolar kontrol edildi.")

def add_record(table: str, data: dict):
    try:
        conn = get_db_connection()
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(data.values()))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Kayıt eklenirken hata: {e}")

def get_warnings_for_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM warnings WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    records = cursor.fetchall()
    conn.close()
    return records

def get_active_records(table: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    if table == "timeouts":
        cursor.execute("UPDATE timeouts SET active = 0 WHERE expires_at < ? AND active = 1", (int(time.time()),))
        conn.commit()
    cursor.execute(f"SELECT * FROM {table} WHERE active = 1 ORDER BY timestamp DESC")
    records = cursor.fetchall()
    conn.close()
    return records

def deactivate_record(table: str, user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE {table} SET active = 0 WHERE user_id = ? AND active = 1", (user_id,))
    conn.commit()
    conn.close()

def get_warning_by_id(warning_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM warnings WHERE id = ?", (warning_id,))
    record = cursor.fetchone()
    conn.close()
    return record

def delete_warning(warning_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM warnings WHERE id = ?", (warning_id,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def create_ticket_record(user_id: int, channel_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tickets (user_id, channel_id, status) VALUES (?, ?, 'open') ON CONFLICT(user_id) DO UPDATE SET channel_id=excluded.channel_id, status='open'", (user_id, channel_id))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Bilet kaydı oluşturulurken hata: {e}")

def get_open_ticket_by_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE user_id = ? AND status = 'open'", (user_id,))
    record = cursor.fetchone()
    conn.close()
    return record

def get_open_ticket_by_channel(channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE channel_id = ? AND status = 'open'", (channel_id,))
    record = cursor.fetchone()
    conn.close()
    return record

def close_ticket_record(channel_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Bilet kapatılırken hata: {e}")
