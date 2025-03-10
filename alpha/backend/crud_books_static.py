import sqlite3

# Path to the static books database
DATABASE_STATIC_PATH = "database/books_static.db"

# Default URL patterns
DEFAULT_PICTURE_URL = (
    "https://bookslibraryfileserver-production.up.railway.app/db/pictures/books_id.png"
)
DEFAULT_DOWNLOAD_URL = (
    "https://bookslibraryfileserver-production.up.railway.app/db/downloads/books_id.pdf"
)


def add_book_static(books_id, picture_url=None, download_url=None):
    """
    Add static resources for a book by its ID.
    If URLs are not provided, use default URLs with the book ID.
    """
    conn = sqlite3.connect(DATABASE_STATIC_PATH)
    cursor = conn.cursor()
    try:
        # Set default URLs if none provided
        if picture_url is None:
            picture_url = DEFAULT_PICTURE_URL.replace(
                "books_id", str(books_id))
        if download_url is None:
            download_url = DEFAULT_DOWNLOAD_URL.replace(
                "books_id", str(books_id))

        cursor.execute(
            """
            INSERT INTO books_static (books_id, picture_url, download_url)
            VALUES (?, ?, ?)
        """,
            (books_id, picture_url, download_url),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print("Error: Static entry for this Book ID already exists.")
        return False
    finally:
        conn.close()


def get_book_static(books_id):
    """
    Retrieve static resources for a book by its ID.
    """
    conn = sqlite3.connect(DATABASE_STATIC_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM books_static WHERE books_id = ?", (books_id,))
    static_data = cursor.fetchone()
    conn.close()
    return static_data


def get_all_books_static():
    """
    Retrieve all static resources for books.
    """
    conn = sqlite3.connect(DATABASE_STATIC_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books_static")
    static_data = cursor.fetchall()
    conn.close()
    return static_data


def update_book_static(books_id, picture_url=None, download_url=None):
    """
    Update static resources for a book by its ID.
    """
    conn = sqlite3.connect(DATABASE_STATIC_PATH)
    cursor = conn.cursor()
    try:
        if picture_url is not None:
            cursor.execute(
                "UPDATE books_static SET picture_url = ? WHERE books_id = ?",
                (picture_url, books_id),
            )
        if download_url is not None:
            cursor.execute(
                "UPDATE books_static SET download_url = ? WHERE books_id = ?",
                (download_url, books_id),
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating static resources: {e}")
        return False
    finally:
        conn.close()


def delete_book_static(books_id):
    """
    Delete static resources for a book by its ID.
    """
    conn = sqlite3.connect(DATABASE_STATIC_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM books_static WHERE books_id = ?", (books_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting static resources: {e}")
        return False
    finally:
        conn.close()
