import psycopg2
import random
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
DB_HOST = "localhost"
DB_NAME = "subscription_sys"
DB_USER = "postgres"
DB_PASS = "admin123" # <--- UPDATE THIS

conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
conn.autocommit = True
cursor = conn.cursor()

print("💥 Destroying old tables...")
cursor.execute("DROP TABLE IF EXISTS users CASCADE")
cursor.execute("DROP TABLE IF EXISTS subscriptions CASCADE")
cursor.execute("DROP TABLE IF EXISTS user_activity CASCADE")
cursor.execute("DROP TABLE IF EXISTS visitors CASCADE")

print("🏗️ Re-creating tables via reset script...")
# Re-run Create logic (Same as database.py)
cursor.execute("CREATE TABLE visitors (visitor_id SERIAL PRIMARY KEY, visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
cursor.execute("CREATE TABLE users (user_id SERIAL PRIMARY KEY, fullname VARCHAR(100), email VARCHAR(100) UNIQUE, password VARCHAR(255), mobile VARCHAR(15), age INTEGER, country VARCHAR(50), role VARCHAR(20) DEFAULT 'USER', is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
cursor.execute("CREATE TABLE subscriptions (subscription_id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(user_id), plan_name VARCHAR(50), amount DECIMAL(10,2), start_date TIMESTAMP, end_date TIMESTAMP, status VARCHAR(20) DEFAULT 'ACTIVE')")
cursor.execute("CREATE TABLE user_activity (activity_id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(user_id), login_time TIMESTAMP, logout_time TIMESTAMP, session_minutes INTEGER DEFAULT 0)")

# Seed Admin
def get_hash(pw): return hashlib.sha256(pw.encode()).hexdigest()
cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", ("Admin", "admin", get_hash("admin123"), "ADMIN"))

print("🌱 Seeding Data...")
names = ["Amit", "Sarah", "Rahul", "Priya", "John", "David"]
for i in range(1, 51):
    name = f"{random.choice(names)}_{i}"
    email = f"user{i}@test.com"
    # Postgres uses %s
    cursor.execute("INSERT INTO users (fullname, email, password, mobile, age, country) VALUES (%s, %s, %s, %s, %s, %s) RETURNING user_id", 
                  (name, email, get_hash("1234"), "9999999999", random.randint(18, 50), "India"))
    uid = cursor.fetchone()[0]
    
    if random.random() > 0.2:
        plan = random.choice([("Silver", 199), ("Gold", 399)])
        start = datetime.now() - timedelta(days=random.randint(0, 30))
        end = start + timedelta(days=30)
        cursor.execute("INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date) VALUES (%s, %s, %s, %s, %s)", 
                      (uid, plan[0], plan[1], start, end))
    
    start = datetime.now() - timedelta(days=random.randint(0, 5))
    cursor.execute("INSERT INTO user_activity (user_id, login_time, session_minutes) VALUES (%s, %s, %s)", (uid, start, random.randint(10, 120)))

for _ in range(100): cursor.execute("INSERT INTO visitors (visit_time) VALUES (CURRENT_TIMESTAMP)")

conn.close()
print("✅ Postgres Database Ready!")