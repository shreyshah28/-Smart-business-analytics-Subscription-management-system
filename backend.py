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
        except Exception: 
            return False, "Email already exists"

    def login(self, email, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        db.cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, hashed_pw))
        return db.cursor.fetchone()

    def update_profile(self, uid, name, email, password, mobile, country):
        # Only hash and update password if a new one is provided
        if password and len(password) >= 4:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            query = "UPDATE users SET fullname=%s, email=%s, password=%s, mobile=%s, country=%s WHERE user_id=%s"
            params = (name, email, hashed_pw, mobile, country, uid)
        else:
            query = "UPDATE users SET fullname=%s, email=%s, mobile=%s, country=%s WHERE user_id=%s"
            params = (name, email, mobile, country, uid)
            
        try:
            db.cursor.execute(query, params)
            db.conn.commit()
            return True, "Profile Updated Successfully"
        except Exception: 
            return False, "Error Updating Profile"

    def get_user_details(self, uid):
        db.cursor.execute("SELECT fullname, email, mobile, country, age FROM users WHERE user_id=%s", (uid,))
        return db.cursor.fetchone()

class SubscriptionManager:
    # Updated to handle the service_type (e.g., Netflix, Amazon)
    def buy_plan(self, user_id, plan_name, amount, service_type):
        start = datetime.now()
        end = start + timedelta(days=30)
        db.cursor.execute(
            "INSERT INTO subscriptions (user_id, plan_name, amount, start_date, end_date, service_type) VALUES (%s, %s, %s, %s, %s, %s)", 
            (user_id, plan_name, amount, start, end, service_type)
        )
        db.conn.commit()
        return self.generate_ott_invoice(user_id, service_type, plan_name, amount, start.strftime("%Y-%m-%d"))

    def get_user_invoices(self, user_id):
        # Added service_type to the historical view
        return pd.read_sql(f"SELECT service_type, plan_name, amount, start_date, end_date, status FROM subscriptions WHERE user_id={int(user_id)} ORDER BY start_date DESC", db.conn)

    def generate_ott_invoice(self, uid, service, plan, amt, date):
        return f"""
        ================================
               EDELHAUS STREAMING
        ================================
        User ID:    {uid}
        Service:    {service}
        Date:       {date}
        --------------------------------
        Plan:       {plan}
        Amount:     ₹{amt}
        Status:     ACTIVE
        ================================
        Enjoy your streaming!
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
            # Calculate minutes accurately
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
        now = datetime.now()
        
        curr_mask = (df['start_date'].dt.month == now.month) & (df['start_date'].dt.year == now.year)
        curr_rev = df[curr_mask]['amount'].sum()
        
        # Calculate previous month
        first_day_curr = now.replace(day=1)
        prev_month_date = first_day_curr - timedelta(days=1)
        prev_mask = (df['start_date'].dt.month == prev_month_date.month) & (df['start_date'].dt.year == prev_month_date.year)
        prev_rev = df[prev_mask]['amount'].sum()
        
        last_year_rev = df[df['start_date'].dt.year == (now.year - 1)]['amount'].sum()
        lifetime_rev = df['amount'].sum()
        total_sales_count = df[curr_mask].shape[0]

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
    
    def detect_security_risks(self):
        df = pd.read_sql("SELECT user_id, session_minutes, login_time FROM user_activity", db.conn)
        if df.empty or len(df) < 5: return pd.DataFrame() 

        data = df['session_minutes'].values
        mean, std_dev = np.mean(data), np.std(data)
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
        except Exception: 
            return "Unknown"
    def get_revenue_by_service(self):
        """Returns data for the Pie Chart"""
        query = "SELECT service_type, SUM(amount) as revenue FROM subscriptions GROUP BY service_type"
        return pd.read_sql(query, db.conn)

    def get_monthly_revenue_trend(self):
        """Returns data for the Line Chart (Monthly Growth)"""
        query = """
            SELECT TO_CHAR(start_date, 'YYYY-MM') as month, SUM(amount) as revenue 
            FROM subscriptions 
            GROUP BY month 
            ORDER BY month ASC
        """
        return pd.read_sql(query, db.conn)

    def get_plan_distribution(self):
        """Returns data for the Bar Chart (Plan popularity)"""
        query = "SELECT plan_name, COUNT(*) as sales FROM subscriptions GROUP BY plan_name"
        return pd.read_sql(query, db.conn)
    def get_monthly_breakdown(self):
        """Fetches revenue grouped by month for the 'Month-to-Month' view."""
        query = """
            SELECT TO_CHAR(start_date, 'YYYY-MM') as "Month", SUM(amount) as "Revenue" 
            FROM subscriptions 
            GROUP BY "Month" 
            ORDER BY "Month" ASC
        """
        df = pd.read_sql(query, db.conn)
        return df

    def get_yearly_breakdown(self):
        """Fetches revenue grouped by year for the 'Yearly Sales' view."""
        query = """
            SELECT TO_CHAR(start_date, 'YYYY') as "Year", SUM(amount) as "Revenue" 
            FROM subscriptions 
            GROUP BY "Year" 
            ORDER BY "Year" ASC
        """
        df = pd.read_sql(query, db.conn)
        return df

    def get_demographics_data(self):
        """Fetches user counts by country and conversion metrics."""
        query_country = "SELECT country, COUNT(*) as count FROM users GROUP BY country ORDER BY count DESC"
        df_country = pd.read_sql(query_country, db.conn)
        
        # Get total vs paid users for the conversion chart
        total_users = pd.read_sql("SELECT COUNT(*) FROM users", db.conn).iloc[0,0]
        paid_users = pd.read_sql("SELECT COUNT(DISTINCT user_id) FROM subscriptions", db.conn).iloc[0,0]
        
        return df_country, total_users, paid_users
    def get_specific_month_report(self, year, month_name):
        """Fetches detailed transaction records for a specific month and year."""
        # Mapping month names to numbers for the SQL query
        month_map = {
            "January": "01", "February": "02", "March": "03", "April": "04",
            "May": "05", "June": "06", "July": "07", "August": "08",
            "September": "09", "October": "10", "November": "11", "December": "12"
        }
        m_num = month_map.get(month_name)
        
        query = f"""
            SELECT 
                u.fullname AS "Customer Name", 
                s.service_type AS "Platform",
                s.plan_name AS "Plan", 
                s.amount AS "Amount", 
                s.start_date AS "Date"
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE TO_CHAR(s.start_date, 'YYYY') = '{year}' 
            AND TO_CHAR(s.start_date, 'MM') = '{m_num}'
            ORDER BY s.start_date DESC
        """
        df = pd.read_sql(query, db.conn)
        
        if df.empty:
            return 0, 0, pd.DataFrame()

        total_revenue = df['Amount'].sum()
        total_sales = len(df)
        
        return total_revenue, total_sales, df
    def get_yearly_comprehensive_report(self, year):
        """Generates a full year report including revenue, growth, and plan-wise sales."""
        # 1. Fetch Revenue and Plan counts per month
        query_subs = f"""
            SELECT 
                TO_CHAR(start_date, 'YYYY-MM') as "Month", 
                SUM(amount) as "Revenue",
                COUNT(CASE WHEN plan_name='Silver' OR plan_name='Mobile' THEN 1 END) as "Silver_Sales",
                COUNT(CASE WHEN plan_name='Gold' OR plan_name='Standard' THEN 1 END) as "Gold_Sales",
                COUNT(CASE WHEN plan_name='Platinum' OR plan_name='Premium' THEN 1 END) as "Platinum_Sales"
            FROM subscriptions 
            WHERE EXTRACT(YEAR FROM start_date) = {year}
            GROUP BY "Month" 
            ORDER BY "Month" ASC
        """
        df_subs = pd.read_sql(query_subs, db.conn)

        # 2. Fetch Active User Traffic per month
        query_act = f"""
            SELECT TO_CHAR(login_time, 'YYYY-MM') as "Month", 
            COUNT(DISTINCT user_id) as "Active_Users" 
            FROM user_activity 
            WHERE EXTRACT(YEAR FROM login_time) = {year} 
            GROUP BY "Month"
        """
        df_act = pd.read_sql(query_act, db.conn)

        if df_subs.empty:
            return pd.DataFrame()
        
        # 3. Merge Sales data with Traffic data
        df_final = pd.merge(df_subs, df_act, on='Month', how='left').fillna(0)
        
        # 4. Calculate Growth Percentage
        df_final['Growth (%)'] = df_final['Revenue'].pct_change().mul(100).round(1).fillna(0)
        
        # Rename columns to match what app.py expects
        df_final.columns = ['Month', 'Revenue (₹)', 'Silver Sales', 'Gold Sales', 'Platinum Sales', 'Active Users', 'Growth (%)']
        
        # Reorder columns for better readability
        return df_final[['Month', 'Revenue (₹)', 'Growth (%)', 'Active Users', 'Silver Sales', 'Gold Sales', 'Platinum Sales']]
    def get_yearly_breakdown(self):
        """Fetches revenue grouped by year with data type safety."""
        query = """
            SELECT 
                EXTRACT(YEAR FROM start_date)::INTEGER as "Year", 
                SUM(amount) as "Revenue" 
            FROM subscriptions 
            GROUP BY "Year" 
            ORDER BY "Year" ASC
        """
        df = pd.read_sql(query, db.conn)
        return df
    def get_revenue_trend(self):
        """Fetches daily revenue for the current month."""
        query = """
            SELECT start_date::date as "Date", SUM(amount) as "Revenue"
            FROM subscriptions
            WHERE TO_CHAR(start_date, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
            GROUP BY "Date" ORDER BY "Date" ASC
        """
        return pd.read_sql(query, db.conn)
    def get_low_engagement_users(self, threshold_mins=60):
        """Finds paid users with low watch time for mutual connection suggestions."""
        query = f"""
            SELECT u.fullname, u.email, SUM(a.session_minutes) as total_mins, s.service_type
            FROM users u
            JOIN user_activity a ON u.user_id = a.user_id
            JOIN subscriptions s ON u.user_id = s.user_id
            WHERE TO_CHAR(a.login_time, 'YYYY-MM') = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
            GROUP BY u.fullname, u.email, s.service_type
            HAVING SUM(a.session_minutes) < {threshold_mins}
        """
        # We try self.db.conn which is the standard for your AdminAnalytics class
        return pd.read_sql(query, db.conn)