import sqlite3
import os

DB_WITH_LOCATION = "file_record_db/records.db"

def get_db_connection():
    conn = sqlite3.connect(DB_WITH_LOCATION)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 code TEXT NOT NULL UNIQUE,
                 filename TEXT NOT NULL,
                 filepath TEXT NOT NULL
                 )
""")
    conn.commit()
    return conn

def create_records_db(file_information):
    code, file_name, file_path = file_information
    conn = sqlite3.connect(DB_WITH_LOCATION)
    cursor=conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL
                    )
                """)
    cursor.execute("INSERT INTO files (code, file_name, file_path) VALUES (?, ?, ?)",
                   (str(code), file_name, file_path))
    conn.commit()
    conn.close()


def get_file_info_by_code(uuid_code):
    conn = get_db_connection()
    cursor= conn.cursor()
    query = "SELECT * FROM files WHERE code = ?"
    try:
        cursor.execute(query, (str(uuid_code),))
        result = cursor.fetchone()
        if result is None:
            return False, None
        return True, result
    except sqlite3.Error as e:
        return False, None
    finally:
        conn.close()