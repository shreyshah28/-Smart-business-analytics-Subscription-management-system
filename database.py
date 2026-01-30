import psycopg2
import hashlib
import sys

# --- CONFIGURATION ---
DB_HOST = "localhost"
DB_NAME = "subscription_sys"
DB_USER = "postgres"
DB_PASS = "shrey28"  # <--- VERIFY THIS PASSWORD

class DB:
    def __init__(self):
        self.conn = None
        self.cursor = None
        try:
            self.conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            self.create_tables()
            print("✅ Database Connected Successfully")
        except Exception as e:
            print(f"\n❌ CRITICAL DATABASE ERROR: {e}\n")
            sys.exit(1)

    def create_tables(self):
        commands = [
            '''CREATE TABLE IF NOT EXISTS visitors (
                visitor_id SERIAL PRIMARY KEY, 
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY, 
                fullname VARCHAR(100), 
                email VARCHAR(100) UNIQUE, 
                password VARCHAR(255), 
                mobile VARCHAR(15), 
                age INTEGER, 
                country VARCHAR(50), 
                role VARCHAR(20) DEFAULT 'USER', 
                is_active BOOLEAN DEFAULT TRUE, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS subscriptions (
                subscription_id SERIAL PRIMARY KEY, 
                user_id INTEGER REFERENCES users(user_id), 
                plan_name VARCHAR(50), 
                amount DECIMAL(10,2), 
                start_date TIMESTAMP, 
                end_date TIMESTAMP, 
                status VARCHAR(20) DEFAULT 'ACTIVE'
            )''',
            '''CREATE TABLE IF NOT EXISTS user_activity (
                activity_id SERIAL PRIMARY KEY, 
                user_id INTEGER REFERENCES users(user_id), 
                login_time TIMESTAMP, 
                logout_time TIMESTAMP, 
                session_minutes INTEGER DEFAULT 0
            )'''
        ]
        
        for cmd in commands:
            self.cursor.execute(cmd)

        # Create Admin
        try:
            admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
            self.cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING", 
                               ("System Admin", "admin", admin_pass, "ADMIN"))
        except: pass

    def log_visitor(self):
        if self.cursor:
            self.cursor.execute("INSERT INTO visitors (visit_time) VALUES (CURRENT_TIMESTAMP)")

    def close(self):
        if self.cursor: self.cursor.close()
        if self.conn: self.conn.close()