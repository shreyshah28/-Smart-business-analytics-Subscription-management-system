import pandas as pd
import hashlib
import re
import numpy as np
from datetime import datetime, timedelta
from database import DB

db = DB()

class UserModule:
    def register(self, name, email, password, mobile, age, country):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email): return False, "Invalid Email Format"
        if len(password) < 4: return False, "Password too short"
        
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        try:
            # POSTGRES: Use %s
            db.cursor.execute(
                "INSERT INTO users (fullname, email, password, mobile, age, country) VALUES (%s, %s, %s, %s, %s, %s)", 
                (name, email, hashed_pw, mobile, age, country)
            )
            db.conn.commit()
            return True, "Registration Successful"
        except: return False, "Email already exists"

    def login(self, email, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        # POSTGRES: Use %s
        db.cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, hashed_pw))
        return db.cursor.fetchone()

    def update_profile(self, uid, name, email, password, mobile, country):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        try:
            db.cursor.execute(
                "UPDATE users SET fullname=%s, email=%s, password=%s, mobile=%s, country=%s WHERE user_id=%s", 
                (name, email, hashed_pw, mobile, country, uid)
            )
            db.conn.commit()
            return True, "Profile Updated Successfully"
        except: return False, "Error Updating Profile"

    def get_user_details(self, uid):
        db.cursor.execute("SELECT fullname, email, mobile, country, age FROM users WHERE user_id=%s", (uid,))
        return db.cursor.fetchone()

class SubscriptionManager:
    def buy_plan(self, user_id, plan_name, amount):
        start = datetime.now()
        end = start + timedelta(days=30)
        
        # Postgres accepts datetime objects directly
        db.cursor.execute(
            "INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date) VALUES (%s, %s, %s, %s, %s)", 
            (user_id, plan_name, amount, start, end)
        )
        db.conn.commit()
        return self.generate_invoice_text(user_id, plan_name, amount, start.strftime("%Y-%m-%d"))

    def get_user_invoices(self, user_id):
        return pd.read_sql(f"SELECT plan_name, amount, start_date, end_date, status FROM subscriptions WHERE user_id={int(user_id)} ORDER BY start_date DESC", db.conn)

    def generate_invoice_text(self, uid, plan, amt, date):
        return f"""
        ================================
                EDELHAUS INVOICE
        ================================
        User ID:    {uid}
        Date:       {date}
        --------------------------------
        Plan:       {plan}
        Amount:     ₹{amt}
        Status:     PAID
        ================================
        Thank you for your business.
        """

class ActivityTracker:
    def log_in(self, uid):
        now = datetime.now()
        # POSTGRES: Use RETURNING to get the ID
        db.cursor.execute(
            "INSERT INTO user_activity (user_id, login_time) VALUES (%s, %s) RETURNING activity_id", 
            (uid, now)
        )
        db.conn.commit()
        return db.cursor.fetchone()[0]

    def log_out(self, aid):
        now = datetime.now()
        db.cursor.execute("SELECT login_time FROM user_activity WHERE activity_id=%s", (aid,))
        res = db.cursor.fetchone()
        if res:
            start = res[0] # Postgres gives datetime object directly
            mins = int((now - start).total_seconds() / 60)
            
            db.cursor.execute(
                "UPDATE user_activity SET logout_time=%s, session_minutes=%s WHERE activity_id=%s", 
                (now, mins, aid)
            )
            db.conn.commit()

class AdminAnalytics:
    def get_monthly_comparison(self):
        df = pd.read_sql("SELECT amount, start_date FROM subscriptions", db.conn)
        if df.empty: return 0, 0, 0, 0, 0, 0  # Added one more zero for Lifetime
        
        # Ensure standard datetime format
        df['start_date'] = pd.to_datetime(df['start_date'])
        
        # 1. Determine Dates
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        # Previous Month Logic (Handles January going back to December)
        first_day_curr = current_date.replace(day=1)
        prev_date = first_day_curr - timedelta(days=1)
        prev_month = prev_date.month
        prev_month_year = prev_date.year
        
        # 2. Calculate Revenues
        # A. Current Month (Jan 2026)
        curr_rev = df[
            (df['start_date'].dt.month == current_month) & 
            (df['start_date'].dt.year == current_year)
        ]['amount'].sum()
        
        # B. Previous Month (Dec 2025)
        prev_rev = df[
            (df['start_date'].dt.month == prev_month) & 
            (df['start_date'].dt.year == prev_month_year)
        ]['amount'].sum()
        
        # C. Last Year Total (2025) - The Big Number
        last_year_rev = df[df['start_date'].dt.year == (current_year - 1)]['amount'].sum()
        
        # D. Lifetime Total
        lifetime_rev = df['amount'].sum()
        
        # E. Sales Count (Current Month)
        total_sales_count = df[
            (df['start_date'].dt.month == current_month) & 
            (df['start_date'].dt.year == current_year)
        ].shape[0]

        # 3. Growth Calculation
        growth = 0
        if prev_rev > 0:
            growth = round(((curr_rev - prev_rev) / prev_rev) * 100, 1)
            
        return curr_rev, prev_rev, growth, last_year_rev, total_sales_count, lifetime_rev

    def get_all_data(self, tbl):
        allowed = ["users", "subscriptions", "user_activity"]
        if tbl not in allowed: return pd.DataFrame()
        df = pd.read_sql(f"SELECT * FROM {tbl}", db.conn)
        if tbl == 'subscriptions' and not df.empty:
            df.rename(columns={'amount': 'Revenue'}, inplace=True)
        return df
    
    def get_revenue_trend(self):
        # POSTGRES: Use DATE()
        df = pd.read_sql("SELECT DATE(start_date) as Date, SUM(amount) as Revenue FROM subscriptions GROUP BY DATE(start_date) ORDER BY Date", db.conn)
        if not df.empty and len(df) > 1:
            df.columns = ['Date', 'Revenue']
            df['Day'] = range(len(df))
            p = np.poly1d(np.polyfit(df['Day'], df['Revenue'], 1))
            df['Trend_Line'] = p(df['Day'])
            return df
        return pd.DataFrame()

    def get_monthly_breakdown(self):
        # POSTGRES: Use TO_CHAR
        query = """
            SELECT TO_CHAR(start_date, 'YYYY-MM') as Month, SUM(amount) as Revenue 
            FROM subscriptions 
            GROUP BY Month 
            ORDER BY Month
        """
        df = pd.read_sql(query, db.conn)
        if not df.empty: df.columns = ['Month', 'Revenue']
        return df

    def get_yearly_breakdown(self):
        # POSTGRES: Use TO_CHAR
        query = """
            SELECT TO_CHAR(start_date, 'YYYY') as Year, SUM(amount) as Revenue 
            FROM subscriptions 
            GROUP BY Year 
            ORDER BY Year
        """
        df = pd.read_sql(query, db.conn)
        if not df.empty: df.columns = ['Year', 'Revenue']
        return df

    def detect_security_risks(self):
        df = pd.read_sql("SELECT user_id, session_minutes, login_time FROM user_activity", db.conn)
        if df.empty or len(df) < 5: return pd.DataFrame() 

        data = df['session_minutes'].values
        mean = np.mean(data)
        std_dev = np.std(data)
        
        if std_dev == 0: return pd.DataFrame()

        z_scores = (data - mean) / std_dev
        outliers = df[np.abs(z_scores) > 2.5].copy()
        
        if not outliers.empty:
            outliers['risk_score'] = np.round(np.abs(z_scores[np.abs(z_scores) > 2.5]), 2)
            # POSTGRES: Fetch name using ID
            outliers['User Name'] = outliers['user_id'].apply(lambda x: self.get_user_name(x))
            return outliers[['User Name', 'session_minutes', 'risk_score', 'login_time']]
        return pd.DataFrame()

    def get_user_name(self, uid):
        try:
            db.cursor.execute("SELECT fullname FROM users WHERE user_id=%s", (uid,))
            return db.cursor.fetchone()[0]
        except: return "Unknown"

    def get_yearly_comprehensive_report(self, year):
        # POSTGRES: Use TO_CHAR and EXTRACT
        query_subs = f"""
            SELECT 
                TO_CHAR(start_date, 'YYYY-MM') as Month, 
                SUM(amount) as Revenue,
                COUNT(CASE WHEN plan_name='Silver' THEN 1 END) as Silver_Sold,
                COUNT(CASE WHEN plan_name='Gold' THEN 1 END) as Gold_Sold,
                COUNT(CASE WHEN plan_name='Platinum' THEN 1 END) as Platinum_Sold
            FROM subscriptions 
            WHERE EXTRACT(YEAR FROM start_date) = {year}
            GROUP BY Month 
            ORDER BY Month
        """
        df_subs = pd.read_sql(query_subs, db.conn)

        query_act = f"""
            SELECT TO_CHAR(login_time, 'YYYY-MM') as Month, COUNT(DISTINCT user_id) as Active_Users
            FROM user_activity
            WHERE EXTRACT(YEAR FROM login_time) = {year}
            GROUP BY Month
        """
        df_act = pd.read_sql(query_act, db.conn)

        if df_subs.empty: return pd.DataFrame()
        
        df_final = pd.merge(df_subs, df_act, on='month', how='left').fillna(0)
        df_final['Revenue'] = df_final['revenue'].astype(float)
        df_final['Growth_Pct'] = df_final['revenue'].pct_change().mul(100).round(1).fillna(0)
        
        df_final = df_final[['month', 'revenue', 'Growth_Pct', 'active_users', 'silver_sold', 'gold_sold', 'platinum_sold']]
        df_final.columns = ['Month', 'Revenue (₹)', 'Growth (%)', 'Active Users', 'Silver Sales', 'Gold Sales', 'Platinum Sales']
        
        return df_final

    # --- THIS IS THE FIX FOR YOUR ERROR ---
    def get_specific_month_report(self, year, month_name):
        month_map = {
            "January": "01", "February": "02", "March": "03", "April": "04",
            "May": "05", "June": "06", "July": "07", "August": "08",
            "September": "09", "October": "10", "November": "11", "December": "12"
        }
        m_num = month_map.get(month_name)
        
        # POSTGRES: Use TO_CHAR(start_date, 'YYYY') instead of strftime
        query = f"""
            SELECT plan_name, amount, start_date 
            FROM subscriptions 
            WHERE TO_CHAR(start_date, 'YYYY') = '{year}' 
            AND TO_CHAR(start_date, 'MM') = '{m_num}'
        """
        df = pd.read_sql(query, db.conn)
        
        if df.empty: return 0, 0, pd.DataFrame()

        total_revenue = df['amount'].sum()
        total_sales = len(df)
        
        return total_revenue, total_sales, df
    # ... inside AdminAnalytics class ...

    def get_demographics_data(self):
        # 1. Get Users by Country
        query_country = "SELECT country, COUNT(*) as count FROM users GROUP BY country ORDER BY count DESC"
        df_country = pd.read_sql(query_country, db.conn)
        
        # 2. Get Conversion Stats (Total Users vs Paid Users)
        total_users = pd.read_sql("SELECT COUNT(*) FROM users", db.conn).iloc[0,0]
        paid_users = pd.read_sql("SELECT COUNT(DISTINCT user_id) FROM subscriptions", db.conn).iloc[0,0]
        
        return df_country, total_users, paid_users
        
    def get_recent_transactions(self):
        # Get last 5 sales with User Name
        query = """
            SELECT u.fullname, s.plan_name, s.amount, s.start_date 
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            ORDER BY s.start_date DESC LIMIT 5
        """
        return pd.read_sql(query, db.conn)