import sqlite3

# Path to the books database
DATABASE_BOOKS_PATH = "database/books_data.db"


def add_book(name, author_name, books_id, category, description):
    """
    Add a new book to the 'books' table.
    """
    conn = sqlite3.connect(DATABASE_BOOKS_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO books (books_id, name, author_name, category, description)
            VALUES (?, ?, ?, ?, ?)
        """,
            (books_id, name, author_name, category, description),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print("Error: Book ID already exists.")
        return False
    finally:
        conn.close()


def get_all_books():
    """
    Retrieve all books from the 'books' table.
    """
    conn = sqlite3.connect(DATABASE_BOOKS_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    conn.close()
    return books


def get_book_by_id(books_id):
    """
    Retrieve a book by its ID.
    """
    conn = sqlite3.connect(DATABASE_BOOKS_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE books_id = ?", (books_id,))
    book = cursor.fetchone()
    conn.close()
    return book


def update_book(books_id, name=None, author_name=None, category=None, description=None):
    """
    Update a book's details by its ID.
    """
    conn = sqlite3.connect(DATABASE_BOOKS_PATH)
    cursor = conn.cursor()
    try:
        if name:
            cursor.execute(
                "UPDATE books SET name = ? WHERE books_id = ?", (name, books_id)
            )
        if author_name:
            cursor.execute(
                "UPDATE books SET author_name = ? WHERE books_id = ?",
                (author_name, books_id),
            )
        if category:
            cursor.execute(
                "UPDATE books SET category = ? WHERE books_id = ?", (category, books_id)
            )
        if description:
            cursor.execute(
                "UPDATE books SET description = ? WHERE books_id = ?",
                (description, books_id),
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating book: {e}")
        return False
    finally:
        conn.close()


def delete_book(books_id):
    """
    Delete a book by its ID.
    """
    conn = sqlite3.connect(DATABASE_BOOKS_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM books WHERE books_id = ?", (books_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting book: {e}")
        return False
    finally:
        conn.close()
