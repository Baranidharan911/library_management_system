import sqlite3
from flask import flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'library.db'

def get_db():
    """Get a database connection with row_factory as sqlite3.Row."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    conn.execute("PRAGMA foreign_keys = ON") 
    return conn

def init_db():
    """Initialize the database with tables for books, members, users, borrowings, and reservations."""
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row 

            conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                name TEXT,
                email TEXT
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT,
                status TEXT DEFAULT 'Available'
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS borrowings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                user_id INTEGER,
                borrow_date TEXT,
                return_date TEXT,
                FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                user_id INTEGER,
                reservation_date TEXT,
                queue_position INTEGER,
                status TEXT DEFAULT 'Pending',  -- Can be 'Pending' or 'Fulfilled'
                FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            conn.commit()
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")

def add_queue_position_column():
    """Add the queue_position column to the reservations table if it doesn't exist."""
    db = get_db()
    try:
        db.execute("ALTER TABLE reservations ADD COLUMN queue_position INTEGER;")
        db.commit()
    except sqlite3.Error as e:
        print(f"Error adding column: {e}")

def create_user(userid, password, role, name=None, email=None):
    """Create a new user with a hashed password."""
    db = get_db()
    password_hash = generate_password_hash(password)  # Hash the password
    try:
        db.execute("INSERT INTO users (username, password_hash, role, name, email) VALUES (?, ?, ?, ?, ?)",
                   (userid, password_hash, role, name, email))
        db.commit()
    except sqlite3.IntegrityError as e:

        return f"Error: User ID '{userid}' already exists. Please choose a different User ID."
    return db.lastrowid

def check_user_credentials(userid, password):
    """Check if the user's credentials are correct."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (userid,)).fetchone()

    if user and check_password_hash(user['password_hash'], password): 
        return user
    return None

def get_user_by_id(user_id):
    """Fetch user details by user_id."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return user

def get_members():
    """Fetch all members from the database (users with 'Member' role)."""
    db = get_db()
    members = db.execute("SELECT * FROM users WHERE role = 'Member'").fetchall()
    return members

def update_user(user_id, name=None, email=None):
    """Update user's profile information."""
    db = get_db()
    if name:
        db.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    if email:
        db.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
    db.commit()

def get_books():
    """Fetch all books from the database."""
    db = get_db()
    books = db.execute("SELECT * FROM books").fetchall()
    return books

def add_book(title, author, genre):
    """Add a new book to the catalog."""
    db = get_db()
    db.execute("INSERT INTO books (title, author, genre) VALUES (?, ?, ?)", (title, author, genre))
    db.commit()

def update_book(book_id, title, author, genre):
    """Update book details."""
    db = get_db()
    db.execute("UPDATE books SET title = ?, author = ?, genre = ? WHERE id = ?", (title, author, genre, book_id))
    db.commit()

def borrow_book(book_id, user_id):
    """Record a book borrowing action."""
    db = get_db()

    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user['role'] != 'Member':
        return "Only members can borrow books."

    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book['status'] == 'Borrowed':
        return "This book is already borrowed by someone else."

    db.execute("INSERT INTO borrowings (book_id, user_id, borrow_date) VALUES (?, ?, date('now'))",
               (book_id, user_id))
    db.execute("UPDATE books SET status = 'Borrowed' WHERE id = ?", (book_id,))
    db.commit()

    flash("Book borrowed successfully!", 'success')
    return redirect(url_for('user_profile', user_id=user_id)) 

def return_book(book_id, user_id):
    """Record a book return action."""
    db = get_db()
    
    # Check if the book is borrowed
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book or book['status'] != 'Borrowed':
        return "This book is not currently borrowed."
    
    db.execute("UPDATE books SET status = 'Available' WHERE id = ?", (book_id,))
    db.execute("""
        UPDATE borrowings 
        SET return_date = date('now') 
        WHERE book_id = ? AND user_id = ? AND return_date IS NULL
    """, (book_id, user_id))
    db.commit()

def reserve_book(book_id, user_id):
    """Reserve a book."""
    db = get_db()

    existing_reservation = db.execute("""
        SELECT * FROM reservations
        WHERE book_id = ? AND user_id = ?
    """, (book_id, user_id)).fetchone()

    if existing_reservation:
        return "You have already reserved this book."

    if db.execute("SELECT status FROM books WHERE id = ?", (book_id,)).fetchone()['status'] == 'Available':
        return "This book is currently available. You can borrow it directly."

    last_position = db.execute("""
        SELECT MAX(queue_position)
        FROM reservations
        WHERE book_id = ?
    """, (book_id,)).fetchone()[0]

    queue_position = (last_position or 0) + 1

    db.execute("""
        INSERT INTO reservations (book_id, user_id, reservation_date, queue_position)
        VALUES (?, ?, date('now'), ?)
    """, (book_id, user_id, queue_position))
    db.commit()

def get_reservations_by_user(user_id):
    """Fetch all reservations for a specific user."""
    db = get_db()
    return db.execute("""
        SELECT r.*, b.title, b.author
        FROM reservations r
        JOIN books b ON r.book_id = b.id
        WHERE r.user_id = ?
    """, (user_id,)).fetchall()

def get_reservations_by_book(book_id):
    """Fetch reservations for a specific book."""
    db = get_db()
    return db.execute("""
        SELECT r.*, u.name, u.email
        FROM reservations r
        JOIN users u ON r.user_id = u.id
        WHERE r.book_id = ?
        ORDER BY r.queue_position ASC
    """, (book_id,)).fetchall()

def get_borrowed_books(user_id):
    """Fetch all borrowed books for a user."""
    db = get_db()
    borrowed_books = db.execute("""
        SELECT b.id, b.title, b.author, bo.borrow_date, bo.return_date
        FROM borrowings bo
        JOIN books b ON bo.book_id = b.id
        WHERE bo.user_id = ? AND bo.return_date IS NULL
    """, (user_id,)).fetchall()
    return [dict(book) for book in borrowed_books]
