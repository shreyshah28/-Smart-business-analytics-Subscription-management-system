import psycopg2
import random
import hashlib
from datetime import datetime, timedelta

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

print("🌱 Generating DIVERSE Historical Data (Multi-Country & Multi-OTT)...")

def h(p): return hashlib.sha256(p.encode()).hexdigest()

# 1. Create Admin
cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", 
                ("System Admin", "admin", h("admin123"), "ADMIN"))

names = ["Romil", "Shrey", "Mehul", "Neer", "Maya", "Abhay", "Nidhi", "Pavan", "Yash", "Rutvik", "Aditya", "Soham", "Riya", "Kavya", "John", "Alice", "Robert", "Emma"]
last_names = ["Shah", "Patel", "Mehta", "Trivedi", "Joshi", "Smith", "Johnson", "Williams", "Brown", "Jones"]
countries = ["India", "USA", "UK", "Germany", "Canada", "France", "Australia", "Japan"]
ott_services = ["Netflix", "Amazon Prime", "Disney+ Hotstar"]

total_users = 0

for year in [2024, 2025, 2026]:
    # 2026 only seeds Jan and Feb
    month_range = range(1, 13) if year < 2026 else range(1, 3)
    year_multiplier = 1.0 if year == 2024 else 1.4 

    for month in month_range:
        # Holiday spikes
        if month in [11, 12]: month_factor = 1.6
        else: month_factor = 1.0
        
        num_users_this_month = int(random.randint(20, 50) * year_multiplier * month_factor)
        
        for _ in range(num_users_this_month):
            fname, lname = random.choice(names), random.choice(last_names)
            full_name = f"{fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}{random.randint(1000,99999)}@demo.com"
            user_country = random.choice(countries)

            day = random.randint(1, 28)
            login_time = datetime(year, month, day, random.randint(9, 23), random.randint(0, 59))
            session_mins = random.randint(5, 180)
            logout_time = login_time + timedelta(minutes=session_mins)

            # Insert User
            cursor.execute("""
                INSERT INTO users (fullname, email, password, mobile, age, country, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id
            """, (full_name, email, h("1234"), "9876543210", random.randint(18, 50), user_country, login_time))
            uid = cursor.fetchone()[0]

            # Insert Activity
            cursor.execute("""
                INSERT INTO user_activity (user_id, login_time, logout_time, session_minutes) 
                VALUES (%s, %s, %s, %s)
            """, (uid, login_time, logout_time, session_mins))

            # Insert Subscription (OTT Specific)
            if random.random() > 0.3:
                service = random.choice(ott_services)
                plan_data = random.choices([("Silver", 199), ("Gold", 499), ("Platinum", 799)], weights=[40, 40, 20], k=1)[0]
                
                cursor.execute("""
                    INSERT INTO subscriptions (user_id, service_type, plan_name, amount, start_date, end_date) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (uid, service, plan_data[0], plan_data[1], login_time, login_time + timedelta(days=30)))

            total_users += 1

print(f"✅ SUCCESS! Generated {total_users} users with OTT subscriptions.")
conn.close()