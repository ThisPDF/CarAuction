from app import get_db_connection
def init_db():
    """Create tables if they don't exist."""
    with get_db_connection() as conn:
        # Create users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0
            )
        ''')
        #cars table
        conn.execute('''
                    CREATE TABLE IF NOT EXISTS cars (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        starting_price REAL NOT NULL,
                        current_bid REAL,
                        highest_bidder INTEGER,
                        auction_end_time TEXT NOT NULL
                    )
                ''')
        #car images
        conn.execute('''
                    CREATE TABLE IF NOT EXISTS car_images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        car_id INTEGER NOT NULL,
                        image_path TEXT NOT NULL,
                        FOREIGN KEY (car_id) REFERENCES cars (id) ON DELETE CASCADE
                    )
                ''')
        # Create contact_messages table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')

        # Create auction_history table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS auction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id INTEGER NOT NULL,
                final_price REAL NOT NULL,
                winner INTEGER NOT NULL,
                auction_end_time TEXT NOT NULL
            )
        ''')
