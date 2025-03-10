import sqlite3
from crud_books_data import DATABASE_BOOKS_PATH
from crud_books_static import DATABASE_STATIC_PATH


def initialize_databases():
    """
    Initialize both books and books_static databases with their tables
    """
    # Initialize books database
    conn = sqlite3.connect(DATABASE_BOOKS_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            books_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            author_name TEXT NOT NULL,
            category TEXT,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()

    # Initialize books_static database
    conn = sqlite3.connect(DATABASE_STATIC_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books_static (
            books_id INTEGER PRIMARY KEY,
            picture_url TEXT,
            download_url TEXT,
            FOREIGN KEY (books_id) REFERENCES books (books_id)
            ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()
