import psycopg2
import random
import hashlib
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DB_PASS = "shrey28"

try:
    conn = psycopg2.connect(host="localhost", database="subscription_sys", user="postgres", password=DB_PASS)
    conn.autocommit = True
    cursor = conn.cursor()
    print("✅ Connected to Database.")
except Exception as e:
    print("❌ Connection Failed:", e); exit()

print("🚀 Adding NEW diverse data...")

def h(p): return hashlib.sha256(p.encode()).hexdigest()

names = ["Romil", "Shrey", "Mehul", "Neer", "Maya", "Abhay", "Nidhi", "Pavan", "Yash", "Rutvik", "Aditya", "Soham"]
last_names = ["Shah", "Patel", "Mehta", "Trivedi", "Joshi", "Vyas", "Desai", "Modi", "Bhatt", "Soni"]

# --- NEW: List of Countries ---
countries = ["India", "USA", "UK", "Germany", "Canada", "France", "Australia", "Japan"]

users_to_add = 30
target_year = 2026
target_month = 2 
new_users_count = 0

for _ in range(users_to_add):
    fname = random.choice(names)
    lname = random.choice(last_names)
    full_name = f"{fname} {lname}"
    email = f"{fname.lower()}.{lname.lower()}{random.randint(100000,999999)}@demo.com"
    
    # --- FIX: Pick a Random Country ---
    user_country = random.choice(countries)
    
    day = random.randint(1, 28) 
    login_time = datetime(target_year, target_month, day, random.randint(9, 23), random.randint(0, 59))
    session_mins = random.randint(5, 180)
    logout_time = login_time + timedelta(minutes=session_mins)

    try:
        # Insert User (Using variable user_country)
        cursor.execute("""
            INSERT INTO users (fullname, email, password, mobile, age, country, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id
        """, (full_name, email, h("1234"), "9876543210", random.randint(18, 50), user_country, login_time))
        uid = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO user_activity (user_id, login_time, logout_time, session_minutes) 
            VALUES (%s, %s, %s, %s)
        """, (uid, login_time, logout_time, session_mins))

        if random.random() > 0.2:
            plan_data = random.choice([("Silver", 199), ("Gold", 399), ("Platinum", 799)])
            cursor.execute("""
                INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date) 
                VALUES (%s, %s, %s, %s, %s)
            """, (uid, plan_data[0], plan_data[1], login_time, login_time + timedelta(days=30)))
        
        new_users_count += 1

    except Exception as e:
        print(f"⚠️ Skipped duplicate email: {email}")

print(f"✅ SUCCESS! Added {new_users_count} new users from mixed countries.")
conn.close()