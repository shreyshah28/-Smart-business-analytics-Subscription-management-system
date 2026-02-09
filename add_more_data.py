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

print("🚀 Simulating NEW OTT subscriptions for Feb 2026...")

def h(p): return hashlib.sha256(p.encode()).hexdigest()

names = ["Romil", "Shrey", "Mehul", "Neer", "Maya", "Abhay", "Nidhi", "Pavan", "Yash", "Rutvik"]
last_names = ["Shah", "Patel", "Mehta", "Trivedi", "Joshi", "Vyas", "Desai"]
countries = ["India", "USA", "UK", "Germany", "Canada", "France"]
ott_services = ["Netflix", "Amazon Prime", "Disney+ Hotstar"]

users_to_add = 20
new_users_count = 0

for _ in range(users_to_add):
    full_name = f"{random.choice(names)} {random.choice(last_names)}"
    email = f"{full_name.replace(' ', '').lower()}{random.randint(10000,99999)}@stream.com"
    user_country = random.choice(countries)
    
    # Target: February 2026
    day = random.randint(1, 9) # Up to current date
    login_time = datetime(2026, 2, day, random.randint(9, 23), random.randint(0, 59))
    session_mins = random.randint(10, 120)

    try:
        cursor.execute("""
            INSERT INTO users (fullname, email, password, mobile, age, country, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id
        """, (full_name, email, h("1234"), "9999988888", random.randint(18, 45), user_country, login_time))
        uid = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO user_activity (user_id, login_time, logout_time, session_minutes) 
            VALUES (%s, %s, %s, %s)
        """, (uid, login_time, login_time + timedelta(minutes=session_mins), session_mins))

        if random.random() > 0.2:
            service = random.choice(ott_services)
            plan_data = random.choice([("Standard", 499), ("Premium", 799)])
            
            cursor.execute("""
                INSERT INTO subscriptions (user_id, service_type, plan_name, amount, start_date, end_date) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (uid, service, plan_data[0], plan_data[1], login_time, login_time + timedelta(days=30)))
        
        new_users_count += 1
    except:
        continue

print(f"✅ SUCCESS! Added {new_users_count} new subscriptions to the database.")
conn.close()