import psycopg2
import random
import hashlib
from datetime import datetime, timedelta

# --- CONFIG ---
DB_PASS = "shrey28"  # <--- VERIFY PASSWORD

conn = psycopg2.connect(host="localhost", database="subscription_sys", user="postgres", password=DB_PASS)
conn.autocommit = True
cursor = conn.cursor()

print("🧹 CLEARING OLD DATA (Truncate)...")
cursor.execute("TRUNCATE users, subscriptions, user_activity, visitors RESTART IDENTITY CASCADE")

print("🌱 SEEDING NEW DATA (Historical & Logic Applied)...")

def h(p): return hashlib.sha256(p.encode()).hexdigest()

admin_pass = h("admin123")
cursor.execute("INSERT INTO users (fullname, email, password, role) VALUES (%s, %s, %s, %s)", 
               ("System Admin", "admin", admin_pass, "ADMIN"))

for i in range(1, 51): 
    name = f"User_{i}"
    email = f"user_{i}@demo.com"
    days_ago = random.randint(0, 60)
    creation_date = datetime.now() - timedelta(days=days_ago)

    try:
        cursor.execute(
            "INSERT INTO users (fullname, email, password, mobile, age, country, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id", 
            (name, email, h("1234"), "9876543210", random.randint(18, 60), "USA", creation_date)
        )
        uid = cursor.fetchone()[0]

        if random.random() > 0.2: 
            plan = random.choice([("Silver", 199), ("Gold", 399), ("Platinum", 799)])
            sub_start = creation_date + timedelta(minutes=random.randint(10, 100))
            sub_end = sub_start + timedelta(days=30)
            
            cursor.execute(
                "INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date) VALUES (%s,%s,%s,%s,%s)", 
                (uid, plan[0], plan[1], sub_start, sub_end)
            )

        login_t = creation_date
        session_mins = random.randint(5, 120)
        logout_t = login_t + timedelta(minutes=session_mins)
        
        cursor.execute(
            "INSERT INTO user_activity (user_id, login_time, logout_time, session_minutes) VALUES (%s,%s,%s,%s)", 
            (uid, login_t, logout_t, session_mins)
        )
        
    except Exception as e:
        print(f"Error on {email}: {e}")

print(f"✅ Database Reset & Seeded Successfully!")
conn.close()