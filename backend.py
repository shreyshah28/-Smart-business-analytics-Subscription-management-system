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
            db.cursor.execute(
                "INSERT INTO users (fullname, email, password, mobile, age, country) VALUES (%s, %s, %s, %s, %s, %s)", 
                (name, email, hashed_pw, mobile, age, country)
            )
            db.conn.commit()
            return True, "Registration Successful"
        except: return False, "Email already exists"

    def login(self, email, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
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
            start = res[0]
            mins = int((now - start).total_seconds() / 60)
            
            db.cursor.execute(
                "UPDATE user_activity SET logout_time=%s, session_minutes=%s WHERE activity_id=%s", 
                (now, mins, aid)
            )
            db.conn.commit()

class AdminAnalytics:
    def get_monthly_comparison(self):
        df = pd.read_sql("SELECT amount, start_date FROM subscriptions", db.conn)
        if df.empty: return 0, 0, 0, 0, 0, 0
        
        df['start_date'] = pd.to_datetime(df['start_date'])
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        first_day_curr = current_date.replace(day=1)
        prev_date = first_day_curr - timedelta(days=1)
        prev_month = prev_date.month
        prev_month_year = prev_date.year
        
        curr_rev = df[(df['start_date'].dt.month == current_month) & (df['start_date'].dt.year == current_year)]['amount'].sum()
        prev_rev = df[(df['start_date'].dt.month == prev_month) & (df['start_date'].dt.year == prev_month_year)]['amount'].sum()
        last_year_rev = df[df['start_date'].dt.year == (current_year - 1)]['amount'].sum()
        lifetime_rev = df['amount'].sum()
        total_sales_count = df[(df['start_date'].dt.month == current_month) & (df['start_date'].dt.year == current_year)].shape[0]

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
        df = pd.read_sql("SELECT DATE(start_date) as Date, SUM(amount) as Revenue FROM subscriptions GROUP BY DATE(start_date) ORDER BY Date", db.conn)
        if not df.empty and len(df) > 1:
            df.columns = ['Date', 'Revenue']
            df['Day'] = range(len(df))
            p = np.poly1d(np.polyfit(df['Day'], df['Revenue'], 1))
            df['Trend_Line'] = p(df['Day'])
            return df
        return pd.DataFrame()

    def get_monthly_breakdown(self):
        query = "SELECT TO_CHAR(start_date, 'YYYY-MM') as Month, SUM(amount) as Revenue FROM subscriptions GROUP BY Month ORDER BY Month"
        df = pd.read_sql(query, db.conn)
        if not df.empty: df.columns = ['Month', 'Revenue']
        return df

    def get_yearly_breakdown(self):
        query = "SELECT TO_CHAR(start_date, 'YYYY') as Year, SUM(amount) as Revenue FROM subscriptions GROUP BY Year ORDER BY Year"
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
            outliers['User Name'] = outliers['user_id'].apply(lambda x: self.get_user_name(x))
            return outliers[['User Name', 'session_minutes', 'risk_score', 'login_time']]
        return pd.DataFrame()

    def get_user_name(self, uid):
        try:
            db.cursor.execute("SELECT fullname FROM users WHERE user_id=%s", (uid,))
            return db.cursor.fetchone()[0]
        except: return "Unknown"

    def get_yearly_comprehensive_report(self, year):
        query_subs = f"""
            SELECT TO_CHAR(start_date, 'YYYY-MM') as Month, SUM(amount) as Revenue,
            COUNT(CASE WHEN plan_name='Silver' THEN 1 END) as Silver_Sold,
            COUNT(CASE WHEN plan_name='Gold' THEN 1 END) as Gold_Sold,
            COUNT(CASE WHEN plan_name='Platinum' THEN 1 END) as Platinum_Sold
            FROM subscriptions WHERE EXTRACT(YEAR FROM start_date) = {year}
            GROUP BY Month ORDER BY Month
        """
        df_subs = pd.read_sql(query_subs, db.conn)

        query_act = f"SELECT TO_CHAR(login_time, 'YYYY-MM') as Month, COUNT(DISTINCT user_id) as Active_Users FROM user_activity WHERE EXTRACT(YEAR FROM login_time) = {year} GROUP BY Month"
        df_act = pd.read_sql(query_act, db.conn)

        if df_subs.empty: return pd.DataFrame()
        
        df_final = pd.merge(df_subs, df_act, on='month', how='left').fillna(0)
        df_final['Revenue'] = df_final['revenue'].astype(float)
        df_final['Growth_Pct'] = df_final['revenue'].pct_change().mul(100).round(1).fillna(0)
        
        df_final = df_final[['month', 'revenue', 'Growth_Pct', 'active_users', 'silver_sold', 'gold_sold', 'platinum_sold']]
        df_final.columns = ['Month', 'Revenue (₹)', 'Growth (%)', 'Active Users', 'Silver Sales', 'Gold Sales', 'Platinum Sales']
        
        return df_final

    # FIXED AND INDENTED CORRECTLY INSIDE CLASS
    def get_specific_month_report(self, year, month_name):
        month_map = {
            "January": "01", "February": "02", "March": "03", "April": "04",
            "May": "05", "June": "06", "July": "07", "August": "08",
            "September": "09", "October": "10", "November": "11", "December": "12"
        }
        m_num = month_map.get(month_name)
        
        query = f"""
            SELECT 
                u.fullname AS "Customer Name", 
                s.plan_name AS "Plan", 
                s.amount AS "Amount", 
                s.start_date AS "Purchase Date"
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE TO_CHAR(s.start_date, 'YYYY') = '{year}' 
            AND TO_CHAR(s.start_date, 'MM') = '{m_num}'
            ORDER BY s.start_date DESC
        """
        df = pd.read_sql(query, db.conn)
        
        if df.empty: return 0, 0, pd.DataFrame()

        total_revenue = df['Amount'].sum()
        total_sales = len(df)
        
        return total_revenue, total_sales, df

    def get_demographics_data(self):
        query_country = "SELECT country, COUNT(*) as count FROM users GROUP BY country ORDER BY count DESC"
        df_country = pd.read_sql(query_country, db.conn)
        total_users = pd.read_sql("SELECT COUNT(*) FROM users", db.conn).iloc[0,0]
        paid_users = pd.read_sql("SELECT COUNT(DISTINCT user_id) FROM subscriptions", db.conn).iloc[0,0]
        return df_country, total_users, paid_users
        
    def get_recent_transactions(self):
        query = """
            SELECT u.fullname, s.plan_name, s.amount, s.start_date 
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            ORDER BY s.start_date DESC LIMIT 5
        """
        return pd.read_sql(query, db.conn)