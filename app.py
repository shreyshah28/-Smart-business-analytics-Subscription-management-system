import streamlit as st
import pandas as pd
import plotly.express as px
from backend import UserModule, SubscriptionManager, ActivityTracker, AdminAnalytics
from database import DB

# --- PAGE CONFIG ---
st.set_page_config(page_title="Edelhaus Analytics", page_icon="📊", layout="wide")

# --- INIT ---
db = DB()
user_sys = UserModule()
sub_sys = SubscriptionManager()
tracker = ActivityTracker()
admin_sys = AdminAnalytics()

# --- CSS STYLING ---
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; border-radius: 10px; padding: 15px; border-left: 5px solid #ff4b4b; }
    .nav-btn { width: 100%; text-align: left; padding: 10px; }
    div.stButton > button:first-child { text-align: left; width: 100%; } 
    div.stButton > button:first-child:hover { background: #f0f2f6; color: #ff4b4b; }
</style>
""", unsafe_allow_html=True)

# ================= STATE MANAGEMENT =================
is_user_logged_in = 'user_id' in st.session_state
is_admin_logged_in = 'admin_auth' in st.session_state

if 'admin_view' not in st.session_state:
    st.session_state['admin_view'] = 'Analytics'
if 'report_view' not in st.session_state:
    st.session_state['report_view'] = 'Overview'

# ================= 1. TOP LEVEL NAVIGATION =================
if not is_user_logged_in and not is_admin_logged_in:
    st.sidebar.title("🚪 Gateway")
    role_choice = st.sidebar.radio("Select Module", ["👤 User Module", "🛠️ Admin Module"])

    if role_choice == "👤 User Module":
        st.title("👤 User Access Portal")
        tab1, tab2 = st.tabs(["Login", "New Registration"])
        with tab1:
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            if st.button("Login", type="primary"):
                user = user_sys.login(email, password)
                if user:
                    st.session_state.update({'user_id': user[0], 'name': user[1], 'act_id': tracker.log_in(user[0])})
                    st.success("Login Successful!"); st.rerun()
                else: st.error("Invalid Credentials")

        with tab2:
            st.subheader("Create New Account")
            c1, c2 = st.columns(2)
            with c1:
                reg_name = st.text_input("Full Name")
                reg_pass = st.text_input("Create Password", type="password")
                reg_age = st.number_input("Age", 18, 100)
            with c2:
                reg_email = st.text_input("Email")
                reg_mobile = st.text_input("Mobile No")
                reg_country = st.selectbox("Country", ["India", "USA", "UK", "Canada", "Germany"])
            if st.button("Register Now"):
                res, msg = user_sys.register(reg_name, reg_email, reg_pass, reg_mobile, reg_age, reg_country)
                if res: st.success(msg)
                else: st.error(msg)

    elif role_choice == "🛠️ Admin Module":
        st.title("🛠️ Administrator Login")
        ad_id = st.text_input("Admin ID")
        ad_pass = st.text_input("Admin Password", type="password")
        if st.button("Access Dashboard"):
            if ad_id == "admin" and ad_pass == "admin123":
                st.session_state['admin_auth'] = True; st.rerun()
            else: st.error("Access Denied")

# ================= 2. USER DASHBOARD =================
elif is_user_logged_in:
    st.sidebar.title(f"👋 Hi, {st.session_state['name']}")
    user_menu = st.sidebar.radio("Menu", ["🏠 Main Menu (Plans)", "⚙️ Settings", "🧾 My Invoices"])
    
    if st.sidebar.button("Logout"):
        tracker.log_out(st.session_state['act_id'])
        del st.session_state['user_id']
        st.rerun()

    if user_menu == "🏠 Main Menu (Plans)":
        st.subheader("💎 Choose Your Subscription")
        c1, c2, c3 = st.columns(3)
        def plan_card(col, name, price, color, btn_key):
            with col:
                st.markdown(f"<div style='background:{color}; padding:20px; border-radius:10px; color:white; text-align:center;'><h3>{name}</h3><h1>₹{price}</h1><p>/month</p></div>", unsafe_allow_html=True)
                if st.button(f"Buy {name}", key=btn_key):
                    txt = sub_sys.buy_plan(st.session_state['user_id'], name, price)
                    st.success("Activated!"); st.download_button("Receipt", txt, "Invoice.txt")
        plan_card(c1, "Silver", 199, "#6c757d", "btn_s")
        plan_card(c2, "Gold", 399, "#ffc107", "btn_g")
        plan_card(c3, "Platinum", 799, "#0d6efd", "btn_p")

    elif user_menu == "⚙️ Settings":
        st.subheader("📝 Update Your Profile")
        curr_data = user_sys.get_user_details(st.session_state['user_id'])
        with st.form("update_form"):
            new_name = st.text_input("Full Name", value=curr_data[0])
            new_email = st.text_input("Email", value=curr_data[1])
            new_mobile = st.text_input("Mobile No", value=curr_data[2])
            new_country = st.text_input("Country", value=curr_data[3])
            new_pass = st.text_input("New Password", type="password")
            if st.form_submit_button("Save Changes"):
                p_to_save = new_pass if new_pass else "1234" 
                res, msg = user_sys.update_profile(st.session_state['user_id'], new_name, new_email, p_to_save, new_mobile, new_country)
                if res: st.success(msg)
                else: st.error(msg)

    elif user_menu == "🧾 My Invoices":
        st.subheader("📜 Invoice History")
        df_inv = sub_sys.get_user_invoices(st.session_state['user_id'])
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True)
            last_rec = df_inv.iloc[0]
            inv_txt = sub_sys.generate_invoice_text(st.session_state['user_id'], last_rec['plan_name'], last_rec['amount'], last_rec['start_date'])
            st.download_button("📥 Download Latest Invoice", inv_txt, f"Invoice.txt")
        else: st.info("No purchase history found.")

# ================= 3. ADMIN DASHBOARD (UPDATED) =================
elif is_admin_logged_in:
    
    with st.sidebar:
        st.title("🛠️ Admin Panel")
        
        if st.button("📊 Analytics Dashboard", use_container_width=True):
            st.session_state['admin_view'] = 'Analytics'
            st.rerun()

        if st.session_state['admin_view'] == 'Analytics':
            st.markdown("### 📑 Report Selection")
            report_select = st.radio("Show Report:", ["Overview", "Month-to-Month", "Yearly Sales"], label_visibility="collapsed")
            st.session_state['report_view'] = report_select

        if st.button("📑 Detailed Reports", use_container_width=True):
             st.session_state['admin_view'] = 'Comprehensive'
             st.rerun()

        if st.button("🗂️ Database Manager", use_container_width=True):
            st.session_state['admin_view'] = 'Database'
            st.rerun()

        if st.button("🚨 Security Audit", use_container_width=True):
            st.session_state['admin_view'] = 'Security'
            st.rerun()

        st.markdown("---")
        if st.button("Logout Admin"):
            del st.session_state['admin_auth']; st.rerun()

    # --- VIEW 1: ANALYTICS ---
    if st.session_state['admin_view'] == 'Analytics':
        st.title("🚀 Executive Analytics")
        
        # Unpack values including lifetime revenue
        curr_rev, prev_rev, growth, last_year_rev, count, lifetime_rev = admin_sys.get_monthly_comparison()

        if st.session_state['report_view'] == "Overview":
            st.subheader("📊 General Overview")
            
            # ROW 1: Immediate Monthly Stats
            m1, m2, m3 = st.columns(3)
            m1.metric("Current Month Revenue", f"₹{curr_rev:,.0f}", f"{growth}% vs Last Month")
            m2.metric("Last Month Revenue", f"₹{prev_rev:,.0f}")
            m3.metric("This Month Sales Count", count)
            
            st.write("") # Spacer
            
            # ROW 2: The Big Picture (2025 vs Lifetime)
            b1, b2 = st.columns(2)
            with b1:
                st.markdown(f"""
                    <div style="background-color: #d1e7dd; padding: 20px; border-radius: 10px; border-left: 5px solid #198754;">
                        <h4 style="color: #198754; margin:0;">Total Revenue (Last Year)</h4>
                        <h1 style="margin:0;">₹{last_year_rev:,.0f}</h1>
                    </div>
                """, unsafe_allow_html=True)
            with b2:
                st.markdown(f"""
                    <div style="background-color: #cfe2ff; padding: 20px; border-radius: 10px; border-left: 5px solid #0d6efd;">
                        <h4 style="color: #0d6efd; margin:0;">Lifetime Revenue (All Time)</h4>
                        <h1 style="margin:0;">₹{lifetime_rev:,.0f}</h1>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            
            # Trends and Plans
            c1, c2 = st.columns(2)
            with c1:
                 st.markdown("📈 **Revenue Trend**")
                 df_trend = admin_sys.get_revenue_trend()
                 if not df_trend.empty:
                    fig = px.line(df_trend, x='Date', y='Revenue', markers=True, template="plotly_white")
                    fig.update_traces(line_color='#ff4b4b', line_width=3)
                    st.plotly_chart(fig, use_container_width=True)
                 else: st.info("Not enough data for trends.")
            
            with c2:
                st.markdown("🍕 **Plan Popularity**")
                df_subs = admin_sys.get_all_data("subscriptions")
                if not df_subs.empty:
                    fig2 = px.pie(df_subs, names='plan_name', hole=0.4, template="plotly_white", color_discrete_sequence=['#C0C0C0', '#FFD700', '#E5E4E2'])
                    st.plotly_chart(fig2, use_container_width=True)
                else: st.info("No subscriptions yet.")
            
            st.markdown("---")
            
            # --- NEW FEATURES (Demographics & Conversion) ---
            st.subheader("🌍 User Demographics & Conversion")
            
            # Fetch Data
            # NOTE: Ensure you have added get_demographics_data() and get_recent_transactions() to backend.py
            try:
                df_country, total_u, paid_u = admin_sys.get_demographics_data()
                df_recent = admin_sys.get_recent_transactions()
                
                # ROW 3: Country & Conversion Charts
                c3, c4 = st.columns(2)
                
                with c3:
                    st.markdown("**📍 Users by Country**")
                    if not df_country.empty:
                        fig_map = px.bar(df_country, x='country', y='count', color='count', template="plotly_white", color_continuous_scale='Viridis')
                        st.plotly_chart(fig_map, use_container_width=True)
                    else: st.info("No user data available.")

                with c4:
                    st.markdown("**💰 Conversion Rate (Free vs Paid)**")
                    if total_u > 0:
                        free_u = total_u - paid_u
                        conv_data = pd.DataFrame({
                            'Status': ['Premium Subscribers', 'Free Users'],
                            'Count': [paid_u, free_u]
                        })
                        fig_conv = px.pie(conv_data, names='Status', values='Count', hole=0.6, color_discrete_sequence=['#0d6efd', '#e9ecef'])
                        st.plotly_chart(fig_conv, use_container_width=True)
                        conv_rate = round((paid_u / total_u) * 100, 1)
                        st.caption(f"🚀 **{conv_rate}%** of your registered users have bought a plan.")
                    else: st.info("No users registered yet.")

                # ROW 4: Recent Transactions
                st.markdown("### 🕒 Recent Purchases")
                if not df_recent.empty:
                    st.dataframe(df_recent, use_container_width=True, hide_index=True)
                else:
                    st.info("No recent transactions found.")
                    
            except AttributeError:
                st.error("⚠️ Please update backend.py with the new functions (get_demographics_data) to see these charts.")

        elif st.session_state['report_view'] == "Month-to-Month":
            st.subheader("🗓️ Month-to-Month Performance Report")
            df_month = admin_sys.get_monthly_breakdown()
            if not df_month.empty:
                fig_m = px.bar(df_month, x='Month', y='Revenue', text_auto=True, template="plotly_white", color='Revenue', color_continuous_scale='Blues')
                st.plotly_chart(fig_m, use_container_width=True)
                st.dataframe(df_month, use_container_width=True)
            else: st.info("No monthly data available.")

        elif st.session_state['report_view'] == "Yearly Sales":
            st.subheader("📅 Yearly Sales Report")
            df_year = admin_sys.get_yearly_breakdown()
            if not df_year.empty:
                fig_y = px.bar(df_year, x='Year', y='Revenue', text_auto=True, template="plotly_white", color='Revenue', color_continuous_scale='Greens')
                st.plotly_chart(fig_y, use_container_width=True)
                st.dataframe(df_year, use_container_width=True)
            else: st.info("No yearly data available.")

    # --- VIEW 2: HISTORICAL ARCHIVE (Detailed Reports) ---
    elif st.session_state['admin_view'] == 'Comprehensive':
        st.title("📑 Historical Archive & Reports")
        
        # 1. TABS: Switch between Yearly Overview and Monthly Drill-Down
        tab_archive, tab_annual = st.tabs(["🗓️ Monthly Archive (Drill-Down)", "📊 Annual Comprehensive"])
        
        with tab_archive:
            st.subheader("🔍 Retrieve Fixed Past Records")
            st.markdown("Select a Year and Month to view the frozen historical data.")

            # Selectors
            c1, c2, c3 = st.columns(3)
            with c1:
                sel_year = st.selectbox("Select Year", ["2024", "2025", "2026"], key="hist_year")
            with c2:
                sel_month = st.selectbox("Select Month", [
                    "January", "February", "March", "April", "May", "June", 
                    "July", "August", "September", "October", "November", "December"
                ], key="hist_month")
            with c3:
                # st.write("") # Spacer
                if st.button("📂 Fetch Monthly Report"):
                    st.session_state['show_history'] = True

            st.divider()

            # Logic to Show Data
            if st.session_state.get('show_history'):
                rev, sales, df_hist = admin_sys.get_specific_month_report(sel_year, sel_month)
                
                if not df_hist.empty:
                    st.success(f"✅ Archive Found: {sel_month} {sel_year}")
                    
                    # Metrics
                    m1, m2 = st.columns(2)
                    m1.metric("Total Revenue", f"₹{rev}")
                    m2.metric("Total Sales", sales)
                    
                    # Data Table
                    st.dataframe(df_hist, use_container_width=True)
                    
                    # CSV Download
                    csv_data = df_hist.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download This Report", csv_data, f"Report_{sel_year}_{sel_month}.csv", "text/csv")
                else:
                    st.warning(f"⚠️ No records found in the archive for {sel_month} {sel_year}.")

        with tab_annual:
            st.subheader("📅 Full Year Overview")
            sel_year_comp = st.selectbox("Select Financial Year", [2024, 2025, 2026], index=2, key="comp_year")
            
            if st.button(f"Generate Annual Report for {sel_year_comp}", type="primary"):
                df_comp = admin_sys.get_yearly_comprehensive_report(sel_year_comp)
                
                if not df_comp.empty:
                    st.dataframe(df_comp.style.format({"Revenue (₹)": "₹{:.2f}", "Growth (%)": "{:+.1f}%"}), use_container_width=True)
                    
                    csv = df_comp.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Annual CSV", csv, f"Annual_Report_{sel_year_comp}.csv", "text/csv")
                    
                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**User Activity vs Revenue**")
                        fig_dual = px.bar(df_comp, x='Month', y='Revenue (₹)', color='Active Users', title="Revenue & Traffic")
                        st.plotly_chart(fig_dual, use_container_width=True)
                    with c2:
                        st.markdown("**Plan Sales Distribution**")
                        df_melt = df_comp.melt(id_vars=['Month'], value_vars=['Silver Sales', 'Gold Sales', 'Platinum Sales'], var_name='Plan', value_name='Count')
                        fig_sales = px.bar(df_melt, x='Month', y='Count', color='Plan', barmode='group')
                        st.plotly_chart(fig_sales, use_container_width=True)
                else:
                    st.error(f"No data found for {sel_year_comp}.")

    # --- VIEW 3: DATABASE ---
    elif st.session_state['admin_view'] == 'Database':
        st.subheader("🗂️ System Database")
        tbl = st.selectbox("Select Table to View", ["users", "subscriptions", "user_activity"])
        df = admin_sys.get_all_data(tbl)
        st.dataframe(df, use_container_width=True, height=500)
        if not df.empty:
            st.download_button("📥 Download CSV", df.to_csv(index=False), f"{tbl}_data.csv")

    # --- VIEW 4: SECURITY ---
    elif st.session_state['admin_view'] == 'Security':
        st.subheader("🚨 Security Audit")
        risks = admin_sys.detect_security_risks()
        if not risks.empty:
            st.error(f"⚠️ Detected {len(risks)} Suspicious Activities!")
            st.dataframe(risks, use_container_width=True)
        else:
            st.success("✅ No Anomalies Detected.")