import streamlit as st
import pandas as pd
import plotly.express as px
from backend import UserModule, SubscriptionManager, ActivityTracker, AdminAnalytics
from database import DB

# --- PAGE CONFIG ---
st.set_page_config(page_title="Edelhaus Streaming", page_icon="🎬", layout="wide")

# --- INIT ---
@st.cache_resource
def init_db():
    return DB()

db = init_db()
user_sys = UserModule()
sub_sys = SubscriptionManager()
tracker = ActivityTracker()
admin_sys = AdminAnalytics()

# --- CSS STYLING ---
st.markdown("""
<style>
    .metric-card { background-color: #1c2128; border-radius: 10px; padding: 15px; border-left: 5px solid #ff4b4b; color: white; }
    div.stButton > button:first-child { border-radius: 8px; transition: 0.3s; }
    .ott-card {
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        color: white;
        font-weight: bold;
        margin-bottom: 10px;
        border: 2px solid transparent;
        transition: 0.3s;
    }
    .ott-card:hover { border: 2px solid white; transform: scale(1.02); cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# ================= STATE MANAGEMENT =================
is_user_logged_in = 'user_id' in st.session_state
is_admin_logged_in = 'admin_auth' in st.session_state

if 'admin_view' not in st.session_state:
    st.session_state['admin_view'] = 'Analytics'
if 'report_view' not in st.session_state:
    st.session_state['report_view'] = 'Overview'

# ================= 1. GATEWAY (LOGIN/REG) =================
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
                reg_country = st.selectbox("Country", ["India", "USA", "UK", "Canada", "Germany", "France", "Japan", "Australia"])
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

# ================= 2. USER DASHBOARD (OTT HUB) =================
elif is_user_logged_in:
    st.sidebar.title(f"👋 Hi, {st.session_state['name']}")
    user_menu = st.sidebar.radio("Menu", ["🏠 OTT Hub", "⚙️ Settings", "🧾 Billing History"])
    
    if st.sidebar.button("Logout"):
        tracker.log_out(st.session_state['act_id'])
        del st.session_state['user_id']
        st.rerun()

    if user_menu == "🏠 OTT Hub":
        st.title("🎬 Explore Premium Services")
        ott_data = {
            "Netflix": {"color": "#E50914", "desc": "Movies, TV shows, and more."},
            "Amazon Prime": {"color": "#00A8E1", "desc": "Originals, Movies & Free Delivery."},
            "Disney+ Hotstar": {"color": "#001339", "desc": "Disney, Marvel, Pixar & Live Sports."}
        }
        
        c1, c2, c3 = st.columns(3)
        cols = [c1, c2, c3]
        for i, (name, info) in enumerate(ott_data.items()):
            with cols[i]:
                st.markdown(f"""<div class="ott-card" style="background-color: {info['color']};">
                    <h2>{name}</h2><p style="font-weight: normal; opacity: 0.9;">{info['desc']}</p></div>""", unsafe_allow_html=True)
                if st.button(f"View {name} Plans", key=f"select_{name}", use_container_width=True):
                    st.session_state['selected_ott'] = name

        if 'selected_ott' in st.session_state:
            target = st.session_state['selected_ott']
            st.divider()
            st.subheader(f"💎 Available Plans for {target}")
            
            plans = []
            if target == "Netflix": 
                plans = [("Mobile", 149, "480p"), ("Standard", 499, "1080p"), ("Premium", 649, "4K+HDR")]
            elif target == "Amazon Prime": 
                plans = [("Lite", 799, "HD"), ("Prime", 999, "All-in-one"), ("Annual", 1499, "Yearly")]
            elif target == "Disney+ Hotstar": 
                plans = [("Super", 899, "2 Screens"), ("Prem. Mo", 299, "4K"), ("Prem. Yr", 1499, "4K")]

            pc1, pc2, pc3 = st.columns(3)
            p_cols = [pc1, pc2, pc3]
            for i, (p_name, p_price, p_feat) in enumerate(plans):
                with p_cols[i]:
                    with st.container(border=True):
                        st.markdown(f"### {p_name}")
                        st.markdown(f"## ₹{p_price}")
                        st.write(f"✅ {p_feat}")
                        if st.button(f"Get {p_name}", key=f"buy_{target}_{p_name}", type="primary", use_container_width=True):
                            txt = sub_sys.buy_plan(st.session_state['user_id'], p_name, p_price, target)
                            st.success(f"Activated {p_name} for {target}!")
                            st.download_button("📥 Receipt", txt, f"Invoice_{target}.txt")

    elif user_menu == "🧾 Billing History":
        st.subheader("📜 Subscription History")
        df_inv = sub_sys.get_user_invoices(st.session_state['user_id'])
        if not df_inv.empty:
            st.dataframe(df_inv, use_container_width=True)
        else: st.info("No active subscriptions found.")

# ================= 3. ADMIN DASHBOARD =================
elif is_admin_logged_in:
    with st.sidebar:
        st.title("🛠️ Admin Panel")
        
        # --- NAVIGATION BUTTONS ---
        if st.button("📊 Analytics Dashboard", use_container_width=True):
            st.session_state['admin_view'] = 'Analytics'
        
        if st.session_state['admin_view'] == 'Analytics':
            st.session_state['report_view'] = st.radio("Show Report:", ["Overview", "Month-to-Month", "Yearly Sales"])

        if st.button("🤝 Mutual Connections", use_container_width=True):
            st.session_state['admin_view'] = 'Connections'

        if st.button("📑 Detailed Archive", use_container_width=True):
            st.session_state['admin_view'] = 'Comprehensive'

        if st.button("🗂️ Database Manager", use_container_width=True):
            st.session_state['admin_view'] = 'Database'

        if st.button("🚨 Security Audit", use_container_width=True):
            st.session_state['admin_view'] = 'Security'

        st.divider()
        if st.button("Logout Admin"):
            del st.session_state['admin_auth']; st.rerun()

    # --- VIEW: ANALYTICS ---
    if st.session_state['admin_view'] == 'Analytics':
        st.title("🚀 Business Intelligence")
        curr_rev, prev_rev, growth, last_year_rev, count, lifetime_rev = admin_sys.get_monthly_comparison()

        if st.session_state['report_view'] == "Overview":
            st.subheader("📊 General Overview")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Current Month Revenue", f"₹{curr_rev:,.0f}", f"{growth}% vs Last Month")
            m2.metric("Last Month Revenue", f"₹{prev_rev:,.0f}")
            m3.metric("This Month Sales Count", count)

            st.write("") 
            
            b1, b2 = st.columns(2)
            b1.metric("Lifetime Revenue (All Time)", f"₹{lifetime_rev:,.0f}")
            b2.metric("Last Year Total Sales", f"₹{last_year_rev:,.0f}")

            st.divider()

            g1, g2 = st.columns(2)
            with g1:
                st.markdown("📈 **Platform Market Share (Revenue)**")
                df_subs = admin_sys.get_all_data("subscriptions")
                if not df_subs.empty:
                    fig_pie = px.pie(df_subs, names='service_type', values='Revenue', hole=0.5, 
                                     color_discrete_map={"Netflix": "#E50914", "Amazon Prime": "#00A8E1", "Disney+ Hotstar": "#001339"})
                    st.plotly_chart(fig_pie, use_container_width=True)

            with g2:
                st.markdown("🌍 **Revenue Contribution by Country**")
                try:
                    df_u = admin_sys.get_all_data("users")
                    df_geo = df_u.merge(df_subs, on="user_id")
                    df_map = df_geo.groupby("country")["Revenue"].sum().reset_index()
                    fig_bar = px.bar(df_map, x='country', y='Revenue', color='Revenue', template="plotly_white")
                    st.plotly_chart(fig_bar, use_container_width=True)
                except: st.info("Geographic data unavailable.")

            st.divider()
            
            with st.container():
                st.markdown("🚀 **User Conversion Status**")
                try:
                    df_country, total_u, paid_u = admin_sys.get_demographics_data()
                    conv_df = pd.DataFrame({"Status": ["Paid", "Free"], "Count": [paid_u, total_u - paid_u]})
                    fig_conv = px.pie(conv_df, names="Status", values="Count", hole=0.7, color_discrete_sequence=["#28a745", "#e9ecef"])
                    st.plotly_chart(fig_conv, use_container_width=True)
                except: st.info("Conversion data unavailable.")

        elif st.session_state['report_view'] == "Month-to-Month":
            st.subheader("🗓️ Monthly Revenue Trends")
            df_trend = admin_sys.get_monthly_breakdown()
            if not df_trend.empty:
                fig = px.line(df_trend, x='Month', y='Revenue', markers=True, line_shape="spline")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_trend, use_container_width=True)

        elif st.session_state['report_view'] == "Yearly Sales":
            st.subheader("📅 Yearly Sales Report")
            df_year = admin_sys.get_yearly_breakdown()
            if not df_year.empty:
                fig_y = px.bar(df_year, x='Year', y='Revenue', text_auto=True, color='Revenue', color_continuous_scale='Greens')
                st.plotly_chart(fig_y, use_container_width=True)

    # --- VIEW: MUTUAL CONNECTIONS (NEW) ---
    elif st.session_state['admin_view'] == 'Connections':
        st.title("🤝 Mutual Connections & Engagement")
        st.info("Analyze low-engagement users to suggest shared plans.")
        
        # --- FILTERS & SORTING ---
        c1, c2 = st.columns(2)
        with c1:
            limit = st.slider("Engagement Threshold (mins)", 10, 300, 60)
        with c2:
            # New: Sort by Platform or Plan
            sort_choice = st.selectbox("Sort List By:", ["Default", "OTT Platform", "Activity (Lowest First)", "Plan Type"])

        df_low = admin_sys.get_low_engagement_users(limit)
        
        if not df_low.empty:
            # 1. Logic for Sorting
            if sort_choice == "OTT Platform":
                df_low = df_low.sort_values(by="service_type")
            elif sort_choice == "Activity (Lowest First)":
                df_low = df_low.sort_values(by="total_mins", ascending=True)
            elif sort_choice == "Plan Type":
                # Assuming 'plan_name' is included in your backend query
                if 'plan_name' in df_low.columns:
                    df_low = df_low.sort_values(by="plan_name")

            # 2. Logic for Grouping (Optional: Show only specific OTT)
            platforms = ["All"] + list(df_low['service_type'].unique())
            selected_platform = st.multiselect("Filter by Platform:", platforms, default="All")
            
            if "All" not in selected_platform:
                df_low = df_low[df_low['service_type'].isin(selected_platform)]

            # --- DISPLAY ---
            st.warning(f"Found {len(df_low)} potential matches based on your filters.")
            st.dataframe(df_low, use_container_width=True)
            
            # --- ACTION ---
            if st.button("📢 Launch Targeted Campaign"):
                st.success(f"Processing connections for {len(df_low)} users...")
                # You can add logic here to group people by the same platform!
        else:
            st.success("No users found for these criteria.")

    # --- VIEW: COMPREHENSIVE ---
    elif st.session_state['admin_view'] == 'Comprehensive':
        st.title("📑 Historical Archive")
        tab_drill, tab_annual = st.tabs(["🔍 Monthly Drill-Down", "📊 Annual Report"])
        
        with tab_drill:
            c1, c2 = st.columns(2)
            y = c1.selectbox("Year", ["2024", "2025", "2026"])
            m = c2.selectbox("Month", ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
            if st.button("Fetch Monthly Archive"):
                rev, sls, df_hist = admin_sys.get_specific_month_report(str(y), m)
                if not df_hist.empty:
                    st.success(f"Records for {m} {y}")
                    st.metric("Total Revenue", f"₹{rev}")
                    st.dataframe(df_hist, use_container_width=True)
                else: st.warning("No records found for this period.")

        with tab_annual:
            sel_yr = st.selectbox("Select Financial Year", [2024, 2025, 2026], index=1)
            if st.button("Generate Annual Comprehensive"):
                df_comp = admin_sys.get_yearly_comprehensive_report(sel_yr)
                if not df_comp.empty:
                    st.dataframe(df_comp, use_container_width=True)
                    fig_annual = px.bar(df_comp, x='Month', y='Revenue (₹)', title=f"Annual Performance {sel_yr}")
                    st.plotly_chart(fig_annual, use_container_width=True)

    # --- VIEW: DATABASE ---
    elif st.session_state['admin_view'] == 'Database':
        st.subheader("🗂️ System Database")
        tbl = st.selectbox("View Table", ["users", "subscriptions", "user_activity"])
        st.dataframe(admin_sys.get_all_data(tbl), use_container_width=True)

    # --- VIEW: SECURITY ---
    elif st.session_state['admin_view'] == 'Security':
        st.subheader("🚨 Security Audit")
        risks = admin_sys.detect_security_risks()
        if not risks.empty:
            st.error(f"Detected {len(risks)} Suspicious Sessions")
            st.dataframe(risks, use_container_width=True)
        else: st.success("No security anomalies detected.")