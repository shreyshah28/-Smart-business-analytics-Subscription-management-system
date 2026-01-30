import psycopg2
import random
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
DB_PASS = "shrey28"  # <--- YOUR PASSWORD

try:
    conn = psycopg2.connect(host="localhost", database="subscription_sys", user="postgres", password=DB_PASS)
    conn.autocommit = True
    cursor = conn.cursor()
    print("✅ Database Connected Successfully")
except Exception as e:
    print("❌ Connection Failed:", e)
    exit()

print("🧹 Cleaning old data...")

# FIX: Use TRUNCATE CASCADE to delete everything safely in one go
cursor.execute("TRUNCATE TABLE users, subscriptions, user_activity, visitors RESTART IDENTITY CASCADE")

print("🌱 Seeding History (2024-2026)...")

def h(p): return hashlib.sha256(p.encode()).hexdigest()

# 1. Create Admin
cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", 
               ("System Admin", "admin", h("admin123"), "ADMIN"))

names = ["Romil", "Shrey", "Mehul", "Neer", "Maya", "Abhay", "Nidhi", "Pavan", "Yash", "Rutvik"]
last_names = ["Shah", "Patel", "Mehta", "Trivedi", "Joshi", "Vyas", "Desai"]

# 2. Generate 300 users across 3 years
for i in range(1, 301):
    fname = random.choice(names)
    lname = random.choice(last_names)
    full_name = f"{fname} {lname}"
    email = f"{fname.lower()}.{lname.lower()}{random.randint(1000,99999)}@demo.com"
    
    # Randomly pick a year: 2024, 2025, or 2026
    year = random.choice([2024, 2025, 2026])
    month = random.randint(1, 12)
    
    # Handle February & Month lengths safely
    if month == 2: day = random.randint(1, 28)
    elif month in [4, 6, 9, 11]: day = random.randint(1, 30)
    else: day = random.randint(1, 31)
    
    # Create the specific date
    creation_date = datetime(year, month, day, random.randint(8, 20), random.randint(0, 59))
    
    # Insert User
    cursor.execute("INSERT INTO users (fullname, email, password, mobile, age, country, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id", 
                   (full_name, email, h("1234"), "9876543210", random.randint(18, 60), "India", creation_date))
    uid = cursor.fetchone()[0]

    # Add Subscription (linked to that date)
    if random.random() > 0.2:
        plan = random.choice([("Silver", 199), ("Gold", 399), ("Platinum", 799)])
        s_date = creation_date
        e_date = creation_date + timedelta(days=30)
        
        cursor.execute("INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date) VALUES (%s, %s, %s, %s, %s)", 
                       (uid, plan[0], plan[1], s_date, e_date))

    # Add Activity
    cursor.execute("INSERT INTO user_activity (user_id, login_time, session_minutes) VALUES (%s, %s, %s)", 
                   (uid, creation_date, random.randint(5, 120)))

print("✅ Historical Data Created Successfully!")
conn.close()