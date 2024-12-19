# Library Management System

This project is a simple Library Management System built using Python, Flask, and SQLite. The system allows users to register, log in, browse books, borrow books, and manage their reservations. Administrators can manage books, members, and reservations.

---

## (a) How to Run the Project

Ensure you have the following installed on your system:

- Python 3.7 or above
- pip (Python package manager)

### Steps to Run

1. **Clone the Repository**:
   Clone this repository to your local machine using:

   ```bash
   git clone <repository_url>
   cd LIBRARY_MANAGEMENT
   ```

2. **Install Dependencies**:
   Install the required Python packages using:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up the Database**:
   The SQLite database `library.db` is already included. If you need to reset the database, delete the `library.db` file and run:

   ```bash
   python database.py
   ```

   This script initializes the database with the required tables.

4. **Run the Application**:
   Start the Flask application by executing:

   ```bash
   python app.py
   ```

   The application will be accessible at `http://127.0.0.1:5000/`.

5. **Access the System**:

   - **For Members**: Register a new account or log in using your credentials.
   - **For Admins**: Use a pre-existing admin account (if defined) or modify the `database.py` script to add one.

---

## (b) Design Choices Made

### 1. **Separation of Concerns**:

- The project follows the MVC (Model-View-Controller) architecture:
  - **Model**: `database.py` handles database initialization and management.
  - **View**: HTML templates located in the `templates` folder, styled with CSS from the `static` folder.
  - **Controller**: Routes and logic defined in `app.py`.

### 2. **HTML Templates**:

- A `base.html` file is used as the parent template for all pages, ensuring consistent layout and structure.
- Templates such as `books.html`, `borrow_book.html`, and `profile.html` handle specific functionalities.

### 3. **Database**:

- SQLite was chosen for its simplicity and ease of setup.
- The database schema includes tables for books, members, reservations, and borrow records.

### 4. **CSS Styling**:

- The `styles.css` file provides a minimalist and responsive design to ensure the application is user-friendly on both desktop and mobile devices.

### 5. **User Authentication**:

- A simple session-based authentication mechanism is implemented using Flask’s session feature.
- Passwords are stored securely using hashing.

### 6. **Modularity**:

- Features like book management, member management, and reservations are modularized for easy future expansion.

---

## (c) Assumptions and Limitations

### Assumptions

1. **Admin Account**:

   - The system assumes an admin account exists or can be manually added via `database.py` or SQL scripts.

2. **Book Availability**:

   - The system tracks the availability of books based on borrow and reservation records.

3. **Borrow Limit**:

   - Users can borrow as many books as they want, and the system manages all borrowing records accordingly.

### Limitations

1. **Scalability**:

   - SQLite is suitable for small-scale applications but may not perform well under heavy load.

2. **Authentication**:

   - The current implementation lacks advanced security features like multi-factor authentication or CAPTCHA.

3. **Concurrency**:

   - Simultaneous updates to the database (e.g., multiple users borrowing the same book) may lead to conflicts.

4. **Admin Features**:

   - Features such as detailed analytics or reporting for admins are not implemented.

5. **Responsive Design**:

   - While the CSS ensures basic responsiveness, it may require additional testing and adjustments for full compatibility with all devices.

---

## Additional Features and Constraints

### Bonus Features

1. Includes search functionality for books by title or author.
2. Implements pagination and token-based authentication.

### Constraints

1. Do not use third-party libraries.
2. Avoid using AI prompts to build the application.

Feel free to modify the code to suit your requirements or contribute to the project by submitting pull requests.

