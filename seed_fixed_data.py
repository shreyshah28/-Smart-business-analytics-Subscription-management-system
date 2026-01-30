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

print("🌱 Generating REALISTIC Historical Data (Different every month)...")

def h(p): return hashlib.sha256(p.encode()).hexdigest()

# 1. Create Admin
cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", 
               ("System Admin", "admin", h("admin123"), "ADMIN"))

names = ["Romil", "Shrey", "Mehul", "Neer", "Maya", "Abhay", "Nidhi", "Pavan", "Yash", "Rutvik", "Aditya", "Soham", "Riya", "Kavya","Pranav","Dishant","Mahir","Divya","Shurti","Henil","Shreya","Kavy","Khush","Kunj","Priya","Nitya"]
last_names = ["Shah", "Patel", "Mehta", "Trivedi", "Joshi", "Vyas", "Desai", "Modi", "Bhatt", "Soni","Sardhara","Raiyani","Doshi","Vaghela","Ambani","Thakkar"]

total_users = 0

# --- LOOP THROUGH YEARS ---
for year in [2024, 2025, 2026]:
    
    # 2026 only has data until January
    month_range = range(1, 13) if year < 2026 else range(1, 2)
    
    # GROWTH FACTOR: 2025 is 30% busier than 2024
    year_multiplier = 1.0 if year == 2024 else 1.3 

    for month in month_range:
        
        # SEASONALITY: Nov/Dec are busy (1.5x), Feb is slow (0.8x)
        if month in [11, 12]: month_factor = 1.5
        elif month == 2: month_factor = 0.8
        else: month_factor = 1.0
        
        # Calculate users for this specific month (Base 15 * Year Growth * Seasonality)
        # Using randomness so even similar months have different numbers
        base_users = random.randint(30, 70)
        num_users_this_month = int(base_users * year_multiplier * month_factor)
        
        for _ in range(num_users_this_month):
            fname = random.choice(names)
            lname = random.choice(last_names)
            full_name = f"{fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}{random.randint(1000,99999)}@demo.com"
            
            # Date Logic
            if month == 2: day = random.randint(1, 28)
            elif month in [4, 6, 9, 11]: day = random.randint(1, 30)
            else: day = random.randint(1, 31)
            
            # Random Time (9 AM to 11 PM)
            login_time = datetime(year, month, day, random.randint(9, 23), random.randint(0, 59))
            
            # Session Duration (Random)
            session_mins = random.randint(5, 180)
            logout_time = login_time + timedelta(minutes=session_mins)

            # Insert User
            cursor.execute("""
                INSERT INTO users (fullname, email, password, mobile, age, country, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id
            """, (full_name, email, h("1234"), "9876543210", random.randint(18, 50), "India", login_time))
            uid = cursor.fetchone()[0]

            # Insert Activity
            cursor.execute("""
                INSERT INTO user_activity (user_id, login_time, logout_time, session_minutes) 
                VALUES (%s, %s, %s, %s)
            """, (uid, login_time, logout_time, session_mins))

            # Insert Subscription (Only 70% buy, plans vary)
            if random.random() > 0.3:
                # Weighted Choice: Gold is most popular
                plan_data = random.choices(
                    [("Silver", 199), ("Gold", 399), ("Platinum", 799)], 
                    weights=[30, 50, 20], k=1
                )[0]
                
                cursor.execute("""
                    INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (uid, plan_data[0], plan_data[1], login_time, login_time + timedelta(days=30)))

            total_users += 1

print(f"✅ SUCCESS! Generated {total_users} unique records.")
print("📈 Data includes Growth Trends (2025 > 2024) and Seasonality (Dec > Feb).")
conn.close()