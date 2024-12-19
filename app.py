from inspect import getmembers
from flask import Flask, flash, render_template, request, redirect, url_for, session, g
from database import init_db, get_db
from functools import wraps
import sqlite3
import math
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "supersecretkey"  
app.permanent_session_lifetime = timedelta(minutes=30)  
init_db()

def hash_password(password):
    return generate_password_hash(password)

def check_user_password(stored_hash, password):
    return check_password_hash(stored_hash, password)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('role') != role:
                return "Access Denied", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        userid = request.form['userid']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        db = get_db()

        user_check = db.execute("SELECT * FROM users WHERE username = ?", (userid,)).fetchone()
        if user_check:
            return "User ID already exists"

        try:
            db.execute("INSERT INTO users (username, password_hash, role, name, email) VALUES (?, ?, ?, ?, ?)",
                       (userid, hash_password(password), role, name, email))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.Error as e:
            return f"An error occurred: {e}"

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['username']  
        password = request.form['password'] 
        db = get_db()


        user = db.execute("SELECT * FROM users WHERE username = ?", (userid,)).fetchone()


        if user and check_password_hash(user['password_hash'], password):  
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('index')) 

        return "Invalid credentials", 401 

    return render_template('login.html')  

@app.route('/members')
@login_required
@role_required('Librarian')
def members():
    db = get_db()

    members_data = db.execute("""
        SELECT u.id, u.name, u.email, b.title, b.author, bo.borrow_date, bo.return_date
        FROM users u
        LEFT JOIN borrowings bo ON u.id = bo.user_id
        LEFT JOIN books b ON bo.book_id = b.id
        WHERE u.role = 'Member'
    """).fetchall()

    members_dict = {}
    for row in members_data:
        member_id = row['id']
        if member_id not in members_dict:
            members_dict[member_id] = {
                'id': member_id,
                'name': row['name'],
                'email': row['email'],
                'borrowed_books': [],
                'returned_books': []
            }
        
        book = {
            'title': row['title'],
            'author': row['author'],
            'borrow_date': row['borrow_date'],
        }

        if row['return_date']:
            book['return_date'] = row['return_date']
            members_dict[member_id]['returned_books'].append(book)  
        else:
            members_dict[member_id]['borrowed_books'].append(book) 

    members_list = list(members_dict.values())

    return render_template('members.html', members=members_list)

@app.route('/delete_member/<int:member_id>', methods=['POST'])
@login_required
@role_required('Librarian')
def delete_member(member_id):
    db = get_db()

    member_borrowings = db.execute("""
        SELECT COUNT(*) AS count FROM borrowings
        WHERE user_id = ? AND return_date IS NULL
    """, (member_id,)).fetchone()

    if member_borrowings['count'] > 0:
        flash('Member cannot be deleted because they have active borrowings.', 'error')
        return redirect(url_for('members'))

    db.execute("DELETE FROM users WHERE id = ?", (member_id,))
    db.commit()
    flash('Member successfully deleted.', 'success')
    return redirect(url_for('members'))

@app.route('/logout')
def logout():
    session.clear()  
    return redirect(url_for('login'))  


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db = get_db()
    user_id = session['user_id']
    
    borrowed_books = db.execute("""
        SELECT b.title, b.author, bo.borrow_date FROM borrowings bo
        JOIN books b ON bo.book_id = b.id
        WHERE bo.user_id = ? AND bo.return_date IS NULL
    """, (user_id,)).fetchall()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        db.execute("UPDATE users SET name = ?, email = ? WHERE id = ?", (name, email, user_id))
        db.commit()
    
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return render_template('profile.html', user=user, borrowed_books=borrowed_books)

@app.route('/')
@login_required
def index():
    return render_template('home.html')

@app.route('/books', methods=['GET', 'POST'])
@login_required
def books():
    db = get_db()

    page = request.args.get('page', 1, type=int)
    per_page = 5
    search = request.form.get('search', '')  
    
    query = """
        SELECT b.*, 
               (SELECT COUNT(*) FROM borrowings WHERE book_id = b.id AND return_date IS NULL) AS is_borrowed,
               (SELECT user_id FROM borrowings WHERE book_id = b.id AND return_date IS NULL LIMIT 1) AS borrowed_by_user_id
        FROM books b
        WHERE b.title LIKE ? OR b.author LIKE ? OR b.genre LIKE ?
        LIMIT ? OFFSET ?
    """
    
    search_pattern = f"%{search}%"  
    books = db.execute(query, (search_pattern, search_pattern, search_pattern, per_page, (page - 1) * per_page)).fetchall()

    total_books = db.execute("""
        SELECT COUNT(*) 
        FROM books b
        WHERE b.title LIKE ? OR b.author LIKE ? OR b.genre LIKE ?
    """, (search_pattern, search_pattern, search_pattern)).fetchone()[0]
    
    total_pages = (total_books + per_page - 1) // per_page

    books_data = []
    for book in books:
        book_dict = dict(book) 
        if book_dict['is_borrowed'] > 0:
            book_dict['status'] = 'Borrowed'
        else:
            book_dict['status'] = 'Available'

        book_dict['borrowed_by_user_id'] = book_dict['borrowed_by_user_id']
        books_data.append(book_dict)

    return render_template('books.html', books=books_data, page=page, total_pages=total_pages, search=search)


@app.route('/my_books')
@login_required
@role_required('Member')
def my_books():
    db = get_db()

    borrowed_books = db.execute("""
        SELECT b.title, b.author, bo.borrow_date, bo.return_date
        FROM borrowings bo
        JOIN books b ON bo.book_id = b.id
        WHERE bo.user_id = ? AND bo.return_date IS NULL
    """, (session['user_id'],)).fetchall()

    return render_template('my_books.html', borrowed_books=borrowed_books)

@app.route('/add_book', methods=['GET', 'POST'])
@login_required
@role_required('Librarian')
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']

        db = get_db()
        db.execute("""
            INSERT INTO books (title, author, genre)
            VALUES (?, ?, ?)
        """, (title, author, genre))
        db.commit()
        flash("New book added.", 'success')
        return redirect(url_for('books'))

    return render_template('edit_book.html', book=None)

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
@role_required('Librarian')
def edit_book(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']

        db.execute("""
            UPDATE books
            SET title = ?, author = ?, genre = ?
            WHERE id = ?
        """, (title, author, genre, book_id))

        db.commit()
        flash("Book has been updated.", 'success')
        return redirect(url_for('books'))

    return render_template('edit_book.html', book=book)

@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
@role_required('Librarian')
def delete_book(book_id):
    db = get_db()
    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    flash("Book has been deleted.", 'success')
    return redirect(url_for('books'))

@app.route('/borrow_book/<int:book_id>', methods=['POST'])
@login_required
@role_required('Member')
def borrow_book(book_id):
    db = get_db()

    book = db.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()

    if book is None:
        flash("The requested book does not exist.", 'danger')
        return redirect(url_for('books'))

    if book['status'] == 'Available':
        try:

            db.execute("""
                INSERT INTO borrowings (book_id, user_id, borrow_date)
                VALUES (?, ?, ?)
            """, (book_id, session['user_id'], datetime.now()))

            db.execute("""
                UPDATE books
                SET status = 'Borrowed'
                WHERE id = ?
            """, (book_id,))
            
            db.commit()

            flash("You have successfully borrowed the book.", 'success')
        except Exception as e:
            db.rollback()
            flash(f"An error occurred while borrowing the book: {str(e)}", 'danger')
    else:
        flash("This book is currently not available.", 'danger')

    return redirect(url_for('books'))

@app.route('/return_book/<int:borrowing_id>', methods=['POST'])
@login_required
@role_required('Librarian')
def return_book(borrowing_id):
    db = get_db()

    borrowing = db.execute("SELECT * FROM borrowings WHERE id = ?", (borrowing_id,)).fetchone()
    if not borrowing:
        flash("Borrowing record not found.", "danger")
        return redirect(url_for('books'))

    try:

        db.execute("UPDATE borrowings SET return_date = ? WHERE id = ?", (datetime.now(), borrowing_id))

        next_reservation = db.execute("""
            SELECT * FROM reservations 
            WHERE book_id = ? 
            ORDER BY queue_position LIMIT 1
        """, (borrowing['book_id'],)).fetchone()

        if next_reservation:

            flash(f"Book is now available for {next_reservation['user_id']}.", "info")

        db.commit()
        flash("Book returned successfully.", "success")
    except Exception as e:
        db.rollback()
        flash(f"An error occurred: {str(e)}", "danger")

    return redirect(url_for('books'))


@app.route('/my_borrowed_books')
@login_required
@role_required('Member')
def my_borrowed_books():
    db = get_db()
    borrowed_books = db.execute("""
        SELECT bo.id AS borrowing_id, b.title, b.author, bo.borrow_date, bo.return_date
        FROM borrowings bo
        JOIN books b ON bo.book_id = b.id
        WHERE bo.user_id = ? 
        ORDER BY bo.borrow_date DESC
    """, (session['user_id'],)).fetchall()
    return render_template('my_borrowed_books.html', borrowed_books=borrowed_books)

@app.route('/reserve_book/<int:book_id>', methods=['POST'])
@login_required
@role_required('Member')
def reserve_book(book_id):
    db = get_db()
    user_id = session['user_id']

    borrowed = db.execute("""
        SELECT * FROM borrowings WHERE book_id = ? AND return_date IS NULL
    """, (book_id,)).fetchone()

    if not borrowed:
        flash("The book is available! You can borrow it directly.", "info")
        return redirect(url_for('books'))

    existing_reservation = db.execute("""
        SELECT * FROM reservations WHERE book_id = ? AND user_id = ?
    """, (book_id, user_id)).fetchone()

    if existing_reservation:
        flash("You have already reserved this book.", "warning")
        return redirect(url_for('books'))

    last_position = db.execute("""
        SELECT MAX(queue_position) FROM reservations WHERE book_id = ?
    """, (book_id,)).fetchone()[0]

    queue_position = (last_position or 0) + 1

    try:

        db.execute("""
            INSERT INTO reservations (book_id, user_id, reservation_date, queue_position)
            VALUES (?, ?, ?, ?)
        """, (book_id, user_id, datetime.now(), queue_position))
        db.commit()
        flash(f"You have reserved the book. Your queue position is {queue_position}.", "success")
    except Exception as e:
        db.rollback()
        flash(f"An error occurred: {str(e)}", "danger")

    return redirect(url_for('books'))


@app.route('/book_reservations/<int:book_id>')
@login_required
@role_required('Librarian')
def book_reservations(book_id):
    db = get_db()

    reservations = db.execute("""
        SELECT r.queue_position, u.name, u.email, r.reservation_date
        FROM reservations r
        JOIN users u ON r.user_id = u.id
        WHERE r.book_id = ?
        ORDER BY r.queue_position
    """, (book_id,)).fetchall()

    parsed_reservations = []
    for reservation in reservations:
        reservation_date = reservation['reservation_date']
        try:

            parsed_date = datetime.strptime(reservation_date, '%Y-%m-%d %H:%M:%S')
        except ValueError:

            parsed_date = datetime.strptime(reservation_date, '%Y-%m-%d')

        parsed_reservations.append({
            'queue_position': reservation['queue_position'],
            'name': reservation['name'],
            'email': reservation['email'],
            'reservation_date': parsed_date  # Pass as datetime
        })

    book = db.execute("SELECT title FROM books WHERE id = ?", (book_id,)).fetchone()

    return render_template('book_reservations.html', reservations=parsed_reservations, book_title=book['title'])

@app.route('/my_reservations')
@login_required
@role_required('Member')
def my_reservations():
    db = get_db()
    user_id = session['user_id']

    reservations = db.execute("""
        SELECT r.queue_position, b.title, b.author, r.reservation_date
        FROM reservations r
        JOIN books b ON r.book_id = b.id
        WHERE r.user_id = ?
        ORDER BY r.queue_position
    """, (user_id,)).fetchall()

    parsed_reservations = []
    for reservation in reservations:
        reservation_date = reservation['reservation_date']
        try:

            parsed_date = datetime.strptime(reservation_date, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:

                parsed_date = datetime.strptime(reservation_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:

                parsed_date = datetime.strptime(reservation_date, '%Y-%m-%d')

        parsed_reservations.append({
            'queue_position': reservation['queue_position'],
            'title': reservation['title'],
            'author': reservation['author'],
            'reservation_date': parsed_date  
        })

    return render_template('my_reservations.html', reservations=parsed_reservations)


@app.route('/edit_member/<int:member_id>', methods=['GET', 'POST'])
@login_required
@role_required('Librarian')
def edit_member(member_id):
    db = get_db()

    member = db.execute("SELECT * FROM users WHERE id = ?", (member_id,)).fetchone()

    if not member:
        flash("Member not found.", "error")
        return redirect(url_for('members'))

    borrowed_books = db.execute("""
        SELECT bo.id AS borrowing_id, b.id AS book_id, b.title, b.author, bo.borrow_date, bo.return_date
        FROM borrowings bo
        JOIN books b ON bo.book_id = b.id
        WHERE bo.user_id = ? AND bo.return_date IS NULL
    """, (member_id,)).fetchall()

    member_data = dict(member)  

    member_data['borrowed_books'] = [dict(book) for book in borrowed_books]

    return render_template('edit_member.html', member=member_data)

@app.route('/return_book/<int:book_id>/<int:member_id>', methods=['POST'])
@login_required
@role_required('Librarian')
def return_book_action(book_id, member_id):
    return_book(book_id, member_id)
    flash("Book marked as returned.")
    return redirect(url_for('edit_member', member_id=member_id))


if __name__ == '__main__':
    app.run(debug=True)
