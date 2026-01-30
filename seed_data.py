import psycopg2
import random
import hashlib
from datetime import datetime, timedelta
import math
# --- CONFIG ---
DB_PASS = "shrey28"  # <--- YOUR PASSWORD

try:
    conn = psycopg2.connect(host="localhost", database="subscription_sys", user="postgres", password=DB_PASS)
    conn.autocommit = True
    cursor = conn.cursor()
    print("✅ Connected to Database.")
except Exception as e:
    print("❌ Connection Failed. Make sure pgAdmin is running and password is correct.")
    print(f"Error: {e}")
    exit()

print("🧹 CLEARING OLD DATA (Truncate)...")
# TRUNCATE is faster than DELETE and resets ID counters
cursor.execute("TRUNCATE users, subscriptions, user_activity, visitors RESTART IDENTITY CASCADE")

print("🌱 SEEDING NEW DATA (With Realistic Names)...")

def h(p): return hashlib.sha256(p.encode()).hexdigest()

# 1. Create Admin
admin_pass = h("admin123")
cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", 
               ("System Admin", "admin", admin_pass, "ADMIN"))

# 2. Realistic Name Lists
first_names = [
    "Romil", "Shrey", "Mehul", "Neer", "Maya", "Abhay", "Nidhi", "Pavan", 
    "Yash", "Rutvik", "Devarsh", "Dhruvi", "Meet", "Mitali", "Riya", "Arjun", 
    "Saanvi", "Vivaan", "Aarav", "Priya", "Rahul", "Anjali", "Vikram"
]

last_names = [
    "Shah", "Patel", "Mehta", "Trivedi", "Joshi", "Vyas", "Desai", 
    "Bhatt", "Parikh", "Gupta", "Sharma", "Singh", "Modi"
]
country_name=["USA","INDIA","UK","GERMANY","JAPAN","RUSSIA"]

# 3. Loop to create 50 Users
for i in range(1, 201): 
    # Pick random names
    fname = random.choice(first_names)
    lname = random.choice(last_names)
    
    full_name = f"{fname} {lname}"
    # Create email like: shrey.shah1@demo.com (using 'i' to ensure it's unique)
    email = f"{fname.lower()}.{lname.lower()}{random.randint(1000, 99999)}@demo.com"
    
    days_ago = random.randint(0, 60)
    creation_date = datetime.now() - timedelta(days=days_ago)
    country=random.choice(country_name)

    try:
        # Insert User
        cursor.execute(
            "INSERT INTO users (fullname, email, password, mobile, age, country, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id", 
            (full_name, email, h("1234"), "9876543210", random.randint(18, 60),country, creation_date)
        )
        uid = cursor.fetchone()[0]

        # Add Subscription (80% chance)
        if random.random() > 0.2: 
            plan = random.choice([("Silver", 199), ("Gold", 399), ("Platinum", 799)])
            sub_start = creation_date + timedelta(minutes=random.randint(10, 100))
            sub_end = sub_start + timedelta(days=30)
            
            cursor.execute(
                "INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date) VALUES (%s,%s,%s,%s,%s)", 
                (uid, plan[0], plan[1], sub_start, sub_end)
            )

        # Add Activity
        login_t = creation_date
        session_mins = random.randint(5, 120)
        logout_t = login_t + timedelta(minutes=session_mins)
        
        cursor.execute(
            "INSERT INTO user_activity (user_id, login_time, logout_time, session_minutes) VALUES (%s,%s,%s,%s)", 
            (uid, login_t, logout_t, session_mins)
        )
        
    except Exception as e:
        print(f"Skipped duplicate or error: {e}")

print(f"✅ Database Reset & Seeded Successfully with {i} users!")
conn.close()