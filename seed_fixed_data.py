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

print("🧹 Clearing old data...")
cursor.execute("TRUNCATE TABLE users, subscriptions, user_activity, visitors RESTART IDENTITY CASCADE")

print("🌱 Generating DIVERSE Historical Data (Multi-Country)...")

def h(p): return hashlib.sha256(p.encode()).hexdigest()

# 1. Create Admin
cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", 
               ("System Admin", "admin", h("admin123"), "ADMIN"))

names = ["Romil", "Shrey", "Mehul", "Neer", "Maya", "Abhay", "Nidhi", "Pavan", "Yash", "Rutvik", "Aditya", "Soham", "Riya", "Kavya", "John", "Alice", "Robert", "Emma"]
last_names = ["Shah", "Patel", "Mehta", "Trivedi", "Joshi", "Smith", "Johnson", "Williams", "Brown", "Jones"]

# --- NEW: List of Countries ---
countries = ["India", "USA", "UK", "Germany", "Canada", "France", "Australia", "Japan"]

total_users = 0

for year in [2024, 2025, 2026]:
    month_range = range(1, 13) if year < 2026 else range(1, 2)
    year_multiplier = 1.0 if year == 2024 else 1.3 

    for month in month_range:
        if month in [11, 12]: month_factor = 1.5
        elif month == 2: month_factor = 0.8
        else: month_factor = 1.0
        
        base_users = random.randint(25, 80)
        num_users_this_month = int(base_users * year_multiplier * month_factor)
        
        for _ in range(num_users_this_month):
            fname = random.choice(names)
            lname = random.choice(last_names)
            full_name = f"{fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}{random.randint(1000,99999)}@demo.com"
            
            # --- FIX: Pick a Random Country ---
            user_country = random.choice(countries)

            if month == 2: day = random.randint(1, 28)
            elif month in [4, 6, 9, 11]: day = random.randint(1, 30)
            else: day = random.randint(1, 31)
            
            login_time = datetime(year, month, day, random.randint(9, 23), random.randint(0, 59))
            session_mins = random.randint(5, 180)
            logout_time = login_time + timedelta(minutes=session_mins)

            # Insert User (Using variable user_country instead of "India")
            cursor.execute("""
                INSERT INTO users (fullname, email, password, mobile, age, country, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id
            """, (full_name, email, h("1234"), "9876543210", random.randint(18, 50), user_country, login_time))
            uid = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO user_activity (user_id, login_time, logout_time, session_minutes) 
                VALUES (%s, %s, %s, %s)
            """, (uid, login_time, logout_time, session_mins))

            if random.random() > 0.3:
                plan_data = random.choices([("Silver", 199), ("Gold", 399), ("Platinum", 799)], weights=[30, 50, 20], k=1)[0]
                cursor.execute("""
                    INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (uid, plan_data[0], plan_data[1], login_time, login_time + timedelta(days=30)))

            total_users += 1

print(f"✅ SUCCESS! Generated {total_users} users from different countries.")
conn.close()