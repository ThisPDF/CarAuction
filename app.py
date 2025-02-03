import os
import sqlite3
import smtplib
import dotenv
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app

load_dotenv()
app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY')
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('CSRF_SECRET_KEY')
csrf = CSRFProtect(app)

DATABASE = 'app.db'
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure uploads folder exists
# ------------------------------------------------------------------------------
# 1. Database Initialization
# ------------------------------------------------------------------------------
def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_photos():
    import requests

    ACCESS_KEY = os.environ.get('UNSPLASH_API')
    url = "https://api.unsplash.com/search/photos"

    params = {
        "query": "cars",
        "per_page": 1,  # Number of images
        "orientation": "landscape"  # Optional: portrait, squarish
    }

    headers = {
        "Authorization": f"Client-ID {ACCESS_KEY}"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        results = data.get("results")
        if results and len(results) > 0:
            # Get a URL from the first result; you can choose a different size if you prefer.
            return results[0]["urls"]["regular"]
        else:
            # Fallback image URL or an empty string
            return ""
    else:
        print("Error:", response.json())
        return ""


# ------------------------------------------------------------------------------
# 2. Helper functions
# ------------------------------------------------------------------------------
def is_admin_user():
    """Check if the current session user is an admin."""
    if 'user_id' not in session:
        return False
    with get_db_connection() as conn:
        user = conn.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        return user and user['is_admin'] == 1
    return False

def send_email(recipient, subject, body):
    """
    Send an email using SMTP.
    Adjust the SMTP server and credentials to your environment.
    """
    sender_email = "nu_am_facut_asta@gmail.com"
    sender_password = "n-am e doar de test"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Using Gmail's SSL SMTP server as an example
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, msg.as_string())
        app.logger.info(f"Email sent to {recipient}")
    except Exception as e:
        app.logger.error(f"Failed to send email to {recipient}: {e}")

@app.context_processor
def utility_processor():
    return dict(is_admin_user=is_admin_user)

# ------------------------------------------------------------------------------
# 3. Routes
# ------------------------------------------------------------------------------
@app.before_request
def cleanup_expired_auctions():
    """Remove expired cars and their images, and move data to auction history."""
    now = datetime.now()
    with get_db_connection() as conn:
        expired_cars = conn.execute('SELECT * FROM cars WHERE auction_end_time <= ?', (now,)).fetchall()

        for car in expired_cars:
            car_id = car['id']
            # Remove images
            car_images = conn.execute('SELECT image_path FROM car_images WHERE car_id = ?', (car_id,)).fetchall()
            for image in car_images:
                image_path = os.path.join('static', image['image_path'])
                if os.path.exists(image_path):
                    os.remove(image_path)

            # Move auction details to auction_history
            if car['current_bid'] and car['highest_bidder']:
                conn.execute(
                    '''
                    INSERT INTO auction_history (car_id, final_price, winner, auction_end_time)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (car_id, car['current_bid'], car['highest_bidder'], car['auction_end_time'])
                )

        # Delete expired cars and their images from the database
        conn.execute('DELETE FROM cars WHERE auction_end_time <= ?', (now,))
        conn.execute('DELETE FROM car_images WHERE car_id NOT IN (SELECT id FROM cars)')

@app.route('/')
def home():
    """Render the home page with featured auctions and auctions about to end."""
    now = datetime.now()
    with get_db_connection() as conn:
        # Get auctions that are marked as featured and still active.
        featured_auctions = conn.execute(
            "SELECT * FROM cars WHERE auction_end_time > ? AND featured = 1",
            (now,)
        ).fetchall()
        # Get auctions that are ending soon (within the next 24 hours).
        ending_soon = conn.execute(
            "SELECT * FROM cars WHERE auction_end_time > ? AND auction_end_time < ?",
            (now, now + timedelta(hours=24))
        ).fetchall()

        # Build a dictionary of car images for all auctions.
        car_images = {}
        for auction in list(featured_auctions) + list(ending_soon):
            images = conn.execute(
                "SELECT image_path FROM car_images WHERE car_id = ?",
                (auction['id'],)
            ).fetchall()
            car_images[auction['id']] = [img['image_path'] for img in images]

    return render_template('index.html', featured_auctions=featured_auctions, ending_soon=ending_soon, car_images=car_images, background_image= get_photos())

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration (username, email, password)."""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            with get_db_connection() as conn:
                conn.execute(
                    'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                    (username, email, hashed_password)
                )
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            # Could be username or email conflict because both are UNIQUE
            flash('Username or Email already exists. Please choose another.', 'danger')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Debug: Print submitted form data
        print(request.form.to_dict())

        # Get form values
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')

        if not username_or_email or not password:
            flash('Username/Email and Password are required.', 'danger')
            return redirect(url_for('login'))

        with get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE username = ? OR email = ?',
                (username_or_email, username_or_email)
            ).fetchone()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                flash('Login successful!', 'success')
                return redirect(url_for('home'))

        flash('Invalid username/email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Handle user logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/car_listing', methods=['GET', 'POST'])
def car_listing():
    """Handle car posting by logged-in users."""
    if 'user_id' not in session:
        flash('You must be logged in to post a car.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        starting_price = float(request.form['starting_price'])
        auction_duration = request.form['auction_duration']

        # Calculate auction end time
        duration_map = {
            '24h': timedelta(hours=24),
            '48h': timedelta(hours=48),
            '1w': timedelta(weeks=1),
            '1m': timedelta(days=30),
        }
        auction_end_time = datetime.now() + duration_map.get(auction_duration, timedelta(hours=24))

        # Create directory for storing images
        car_upload_dir = os.path.join(UPLOAD_FOLDER, 'car-auctions')
        os.makedirs(car_upload_dir, exist_ok=True)

        # Save car details to database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO cars (user_id, title, description, starting_price, auction_end_time)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (session['user_id'], title, description, starting_price, auction_end_time)
            )
            car_id = cursor.lastrowid  # Get the ID of the newly inserted car

            # Handle multiple image uploads
            uploaded_files = request.files.getlist('images')
            for uploaded_file in uploaded_files:
                if uploaded_file and uploaded_file.filename:
                    filename = secure_filename(uploaded_file.filename)
                    file_path = os.path.join(car_upload_dir, f"{car_id}_{filename}")
                    uploaded_file.save(file_path)
                    relative_path = os.path.relpath(file_path, 'static')

                    # Save image path to car_images table
                    cursor.execute(
                        'INSERT INTO car_images (car_id, image_path) VALUES (?, ?)',
                        (car_id, relative_path)
                    )
            conn.commit()

        flash('Car posted successfully!', 'success')
        return redirect(url_for('cars_for_sale'))

    return render_template('car_listing.html')

@app.route('/cars_for_sale')
def cars_for_sale():
    """Display all cars with active auctions."""
    now = datetime.now()
    with get_db_connection() as conn:
        # Fetch cars with auctions that are still active
        cars = conn.execute('''
            SELECT
                cars.id,
                cars.title,
                cars.description,
                cars.starting_price,
                cars.current_bid,
                cars.auction_end_time
            FROM cars
            WHERE cars.auction_end_time > ?
        ''', (now,)).fetchall()

        # Fetch images for each car
        car_images = {}
        for car in cars:
            images = conn.execute('SELECT image_path FROM car_images WHERE car_id = ?', (car['id'],)).fetchall()
            car_images[car['id']] = [image['image_path'] for image in images]

    return render_template('cars_for_sale.html', cars=cars, car_images=car_images)

@app.route('/car-details/<int:car_id>')
def car_details(car_id):
    """Display detailed information about a specific car."""
    with get_db_connection() as conn:
        # Fetch the car details
        car = conn.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()
        if not car:
            return "Car not found", 404

        # Fetch images for this car
        images = conn.execute('SELECT image_path FROM car_images WHERE car_id = ?', (car_id,)).fetchall()
        car_images = [image['image_path'] for image in images]

    return render_template('car_details.html', car=car, car_images=car_images)

@app.route('/submit-contact', methods=['POST'])
def submit_contact():
    """Handle the submission of the contact form."""
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']

    with get_db_connection() as conn:
        conn.execute(
            'INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)',
            (name, email, message)
        )
    flash('Your message has been sent successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/contact')
def contact_form():
    """Render the contact form page."""
    return render_template('contact_form.html')

@app.route('/place_bid', methods=['POST'])
def place_bid():
    """Handle placing a bid on a car."""
    if 'user_id' not in session:
        flash('You must be logged in to place a bid.', 'warning')
        return redirect(url_for('login'))

    car_id = request.form.get('car_id')
    bid_increment = float(request.form.get('bid_increment', 0))

    if bid_increment < 100:
        flash('The minimum bid increment is 100 euros.', 'danger')
        return redirect(url_for('car_details', car_id=car_id))

    with get_db_connection() as conn:
        car = conn.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()
        if not car:
            flash('Car not found.', 'danger')
            return redirect(url_for('cars_for_sale'))

        # Check if auction is still active
        if datetime.now() > datetime.fromisoformat(car['auction_end_time']):
            flash('The auction has ended. You cannot place a bid.', 'danger')
            return redirect(url_for('car_details', car_id=car_id))

        current_bid = car['current_bid'] or car['starting_price']
        new_bid = current_bid + bid_increment

        # Update the car with the new bid
        conn.execute(
            'UPDATE cars SET current_bid = ?, highest_bidder = ? WHERE id = ?',
            (new_bid, session['user_id'], car_id)
        )
    flash(f'Your bid of €{new_bid:.2f} has been placed successfully!', 'success')
    return redirect(url_for('car_details', car_id=car_id))

# ------------------------------------------------------------------------------
# 4. Admin Routes
# ------------------------------------------------------------------------------
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    """Admin dashboard to view and manage database details."""
    if 'user_id' not in session:
        flash('You must be logged in as an admin to view this page.', 'warning')
        return redirect(url_for('login'))

    if not is_admin_user():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))

    with get_db_connection() as conn:
        users = conn.execute('SELECT * FROM users').fetchall()
        cars = conn.execute('''
            SELECT cars.id, cars.title, cars.current_bid, cars.auction_end_time,
                   cars.featured,
                   users.email AS highest_bidder_email
            FROM cars
            LEFT JOIN users ON cars.highest_bidder = users.id
        ''').fetchall()
        messages = conn.execute('SELECT * FROM contact_messages').fetchall()

    return render_template('admin_dashboard.html', users=users, cars=cars, messages=messages)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Delete a user account."""
    if 'user_id' not in session or not is_admin_user():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))

    with get_db_connection() as conn:
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.execute('DELETE FROM cars WHERE user_id = ?', (user_id,))  # Delete user's cars
    flash('User account deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    """Update user details."""
    if 'user_id' not in session or not is_admin_user():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))

    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    with get_db_connection() as conn:
        conn.execute(
            'UPDATE users SET username = ?, password = ? WHERE id = ?',
            (username, hashed_password, user_id)
        )
    flash('User details updated successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_message/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    """Delete a contact message."""
    if 'user_id' not in session or not is_admin_user():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))

    with get_db_connection() as conn:
        conn.execute('DELETE FROM contact_messages WHERE id = ?', (message_id,))
    flash('Message deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-auction/<int:car_id>', methods=['POST'])
def delete_auction(car_id):
    """Allow an admin to delete an auction, including removing images."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row

        # Remove images associated with the car
        car_images = conn.execute('SELECT image_path FROM car_images WHERE car_id = ?', (car_id,)).fetchall()
        for image in car_images:
            image_path = os.path.join('static', image['image_path'])
            if os.path.exists(image_path):
                os.remove(image_path)

        # Delete the car and its associated images from the database
        conn.execute('DELETE FROM car_images WHERE car_id = ?', (car_id,))
        conn.execute('DELETE FROM cars WHERE id = ?', (car_id,))

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_auction_time/<int:car_id>', methods=['POST'])
def update_auction_time(car_id):
    """Update auction end time."""
    if 'user_id' not in session or not is_admin_user():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))

    new_end_time = request.form.get('new_end_time')
    app.logger.info(f"Received new_end_time: {new_end_time} for car_id: {car_id}")

    try:
        new_end_time = datetime.strptime(new_end_time, '%Y-%m-%d %H:%M:%S')
        app.logger.info(f"Parsed new_end_time: {new_end_time}")
    except ValueError as e:
        app.logger.error(f"Date parsing error: {e}")
        flash('Invalid date format. Use YYYY-MM-DD HH:MM:SS.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        with get_db_connection() as conn:
            conn.execute('UPDATE cars SET auction_end_time = ? WHERE id = ?', (new_end_time, car_id))
            app.logger.info(f"Auction time updated for car_id: {car_id}")
            flash('Auction time updated successfully.', 'success')
    except Exception as e:
        app.logger.error(f"Database update error: {e}")
        flash('An error occurred while updating the auction time.', 'danger')

    return redirect(url_for('admin_dashboard'))

# --- New Admin Routes for Featuring Auctions ---

@app.route('/admin/feature_auction/<int:car_id>', methods=['POST'])
def feature_auction(car_id):
    """Mark an auction as featured."""
    if 'user_id' not in session or not is_admin_user():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    with get_db_connection() as conn:
        conn.execute('UPDATE cars SET featured = 1 WHERE id = ?', (car_id,))
        conn.commit()  # <-- Make sure to commit the change
    flash('Auction marked as featured.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unfeature_auction/<int:car_id>', methods=['POST'])
def unfeature_auction(car_id):
    """Remove the featured mark from an auction."""
    if 'user_id' not in session or not is_admin_user():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    with get_db_connection() as conn:
        conn.execute('UPDATE cars SET featured = 0 WHERE id = ?', (car_id,))
        conn.commit()  # <-- Commit the change
    flash('Auction unfeatured.', 'info')
    return redirect(url_for('admin_dashboard'))


# ------------------------------------------------------------------------------
# 5. Main Entry
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
