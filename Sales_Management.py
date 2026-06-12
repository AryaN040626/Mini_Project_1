import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

#DB Connection
host = "localhost"
port = "5432"
database = "TestDB"
username = "postgres"
password = "guvi2026"

engine_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
engine = create_engine(engine_string)

df1 = pd.read_sql_table("branches", con=engine)
df2 = pd.read_sql_table("customer_sales", con=engine)
df3 = pd.read_sql_table("users", con=engine)
df4 = pd.read_sql_table("payments_splits", con=engine)

#Session State
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "branch_id" not in st.session_state:
    st.session_state.branch_id = None
if "branch_name" not in st.session_state:
    st.session_state.branch_name = None

#Verify User
def verify_user(username, password):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT u.user_name, u.roles, u.branch_id, b.branch_name
                FROM users u
                LEFT JOIN branches b ON u.branch_id = b.branch_id
                WHERE u.user_name = :u AND u.user_password = :p
            """),
            {"u": username, "p": password}
        )
        return result.fetchone()

#Login Page
if st.session_state.user is None:
    st.title("Welcome To Sales Management System")
    st.subheader("Please login to continue")

    login_username = st.text_input("Username")
    login_password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = verify_user(login_username, login_password)
        if user:
            st.session_state.user       = user[0]  # user_name
            st.session_state.role       = user[1]  # roles
            st.session_state.branch_id  = user[2]  # branch_id
            st.session_state.branch_name = user[3] # branch_name
            st.success("Login Successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

#Main Application
else:
    role = st.session_state.role

    #Sidebar
    st.sidebar.title("Navigation")

    if role == "Admin":
        page = st.sidebar.radio("Go to", ["Dashboard & Reports", "Data Entry Workspace"])
    elif role == "Super Admin":
        page = st.sidebar.radio("Go to", ["Dashboard & Reports", "Data Entry Workspace", "Advanced SQL Queries"])

    st.sidebar.divider()
    st.sidebar.markdown(f"👤 **User:** {st.session_state.user}")
    st.sidebar.markdown(f"🔑 **Role:** {st.session_state.role}")
    if role == "Admin":
        st.sidebar.markdown(f"🏢 **Branch:** {st.session_state.branch_name}")

    if st.sidebar.button("Log Out", key="sidebar_logout"):
        st.session_state.user = None
        st.session_state.role  = None
        st.session_state.branch_name = None
   
        st.rerun()

    elif role == "Super Admin":
        st.title("📈 Sales Dashboard")
        st.success(f"Welcome {st.session_state.user} ({st.session_state.role})")

        if st.button("Logout", key="sales_dashboard_logout"):
            st.session_state.user = None
            st.rerun()
        st.subheader("Customer Sales")
        st.dataframe(df2, use_container_width=True)


    if page == "Dashboard & Reports":
        st.title("📈 Student Enrollment Dashboard")
        st.subheader("Filter Controls")
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        #Branch Filter
        if role == "Admin":
            branches = [st.session_state.branch_name]
        else:
            branches = df1["branch_name"].tolist()

        with col1:
            if role == "Admin":
                selected_branch = st.selectbox(
                    "Select Branch",
                    [st.session_state.branch_name],
                    index=0,
                    key="branch_select",
                )
            else:
                selected_branch = st.selectbox("Select Branch", ["All"] + branches, index=0, key="branch_select")

        products = df2["product_name"].unique().tolist()
        with col2:
            selected_product = st.selectbox("Select Product", ["All"] + products, index=0, key="product_select")

        df2["sale_date"] = pd.to_datetime(df2["sale_date"])
        available_dates = df2["sale_date"].sort_values().dt.strftime("%Y-%m-%d").unique().tolist()

        with col3:
            start_date = st.selectbox("Select Start Date", available_dates, index=0, key="start_date_selectbox")
        with col4:
            end_date = st.selectbox("Select End Date", available_dates, index=len(available_dates) - 1, key="end_date_selectbox")

        # Apply Filters
        filtered_df1 = df1.copy()
        filtered_df  = df2.copy()

        if role == "Admin":
          
            filtered_df = filtered_df[filtered_df["branch_id"] == df3[df3["user_name"] == st.session_state.user]["branch_id"].values[0]]
        else:
            
            if selected_branch != "All":
                filtered_df1 = filtered_df1[filtered_df1["branch_name"] == selected_branch]
                matching_branch_ids = filtered_df1["branch_id"].unique()
                filtered_df = filtered_df[filtered_df["branch_id"].isin(matching_branch_ids)]

        #Product Filter
        if selected_product != "All":
            filtered_df = filtered_df[filtered_df["product_name"] == selected_product]

        #Date Filter 
        filtered_df = filtered_df[
            (filtered_df["sale_date"] >= start_date) &
            (filtered_df["sale_date"] <= end_date)
        ]

        st.divider()
        st.subheader("📊 Financial Summary")

        if filtered_df.empty:
            st.warning("No records found for the selected filters.")
        else:
            m1, m2, m3, m4 = st.columns([5, 5, 5, 4])

            m1.metric("Overall Revenue (Gross)", f"₹{filtered_df['gross_sales'].sum()/100000:,.2f}L")
            m2.metric("Total Received Amount",   f"₹{filtered_df['received_amount'].sum()/100000:,.2f}L")
            m3.metric("Total Pending Amount",    f"₹{filtered_df['pending_amount_gen'].sum()/100000:,.2f}L")

            gross_total = filtered_df["gross_sales"].sum()
            pending_pct = (filtered_df["pending_amount_gen"].sum() / gross_total * 100) if gross_total > 0 else 0
            m4.metric("Pending Collection Pct", f"{pending_pct:.1f}%")

            st.divider()

            if role == "Admin":
                st.subheader("📋 Branch Course Records")
                st.markdown(f"🏢 Showing records for **{st.session_state.branch_name}** branch only")
            else:
                st.subheader("📋 Branch Sales Report")

            st.dataframe(filtered_df, use_container_width=True)
            st.markdown(f"Total Records: **{len(filtered_df)}**")
    elif page == "Data Entry Workspace":
        st.title("📋 Operations Record Creator")
        tab1, tab2 = st.tabs(["Add New Sales Entry", "Log Payment Split Details"])

        with tab1:
            st.subheader("New Sale Generation")

            if role == "Admin":
                selected_branch = st.selectbox(
                    "Select Target Branch",
                    [st.session_state.branch_name],
                    index=0,
                    key="entry_branch",
                )
            else:
                branches = df1["branch_name"].tolist()
                selected_branch = st.selectbox("Select Target Branch", branches, key="entry_branch")

            col1, col2 = st.columns(2)

            with col1:
                student_name = st.text_input("Student Name", key="student_name")
            with col2:
                products = df2["product_name"].unique().tolist()
                selected_course = st.selectbox("Select Course Name", products, key="entry_course")

            col3, col4 = st.columns(2)
            with col3:
                mobile = st.text_input("Mobile Number", key="mobile_number")
            with col4:
                joining_date = st.date_input("Joining Date", key="joining_date")

            gross_amount = st.number_input("Gross Sales Amount (₹)", min_value=0.0, format="%.2f", key="gross_amount")
            order_status = st.selectbox("Initial Order Status", ["Open", "Close"], key="order_status")

            if st.button("Submit Entry", key="submit_sales_entry"):
                if student_name and mobile:
                    with engine.connect() as conn:
                        branch_id = int(df1[df1["branch_name"] == selected_branch]["branch_id"].values[0])
                        conn.execute(text("SELECT setval('customer_sales_sale_id_seq', (SELECT MAX(sale_id) FROM customer_sales))"))
                        conn.commit()
                        conn.execute(text("""
                            INSERT INTO customer_sales
                                (branch_id, sale_date, customer_name, mobile_number, product_name, gross_sales, received_amount, status)
                            VALUES
                                (:branch_id, :sale_date, :customer_name, :mobile_number, :product_name, :gross_sales, 0, :status)
                        """), {
                            "branch_id":     branch_id,
                            "sale_date":     joining_date,
                            "customer_name": student_name,
                            "mobile_number": mobile,
                            "product_name":  selected_course,
                            "gross_sales":   gross_amount,
                            "status":        order_status
                        })
                        conn.commit()
                    st.success("✅ Sale entry added successfully!")
                else:
                    st.error("Please fill in all required fields.")

        with tab2:
            st.subheader("Log Payment Split Details")

            with engine.connect() as conn:
                if role == "Admin":
                    active_sales = pd.read_sql(text("""
                        SELECT cs.sale_id, cs.product_name, cs.pending_amount_gen
                        FROM customer_sales cs
                        WHERE (cs.gross_sales - cs.received_amount) > 0
                        AND cs.branch_id = :branch_id
                    """), conn, params={"branch_id": st.session_state.branch_id})
                else:
                    active_sales = pd.read_sql(text("""
                        SELECT sale_id, product_name, pending_amount_gen
                        FROM customer_sales
                        WHERE (gross_sales - received_amount) > 0
                    """), conn)

            sale_options = [
                f"ID {row['sale_id']} - ({row['product_name']}) - ₹{row['pending_amount_gen']} Pending"
                for _, row in active_sales.iterrows()
            ]

            selected_sale    = st.selectbox("Select Target Active Sale ID Asset", sale_options, key="payment_sale")
            selected_sale_id = int(selected_sale.split(" ")[1]) if selected_sale else None

            payment_channel = st.selectbox("Payment Collection Channel", ["Cash", "UPI", "Card"], key="payment_channel")
            split_amount    = st.number_input("Collected Split Amount Balance (₹)", min_value=0.01, format="%.2f", key="split_amount")
            payment_date    = st.date_input("Payment Date", key="payment_date")

            if st.button("Apply Payment Allocation", key="apply_payment_btn"):
                if selected_sale_id and split_amount > 0:
                    with engine.connect() as conn:
                        conn.execute(text("SELECT setval('payments_splits_payment_id_seq', (SELECT MAX(payment_id) FROM payments_splits))"))
                        conn.commit()
                        conn.execute(text("""
                            INSERT INTO payments_splits
                                (sale_id, payment_date, amount_paid, payment_method)
                            VALUES
                                (:sale_id, :payment_date, :amount_paid, :payment_method)
                        """), {
                            "sale_id":        selected_sale_id,
                            "payment_date":   payment_date,
                            "amount_paid":    split_amount,
                            "payment_method": payment_channel
                        })
                        conn.commit()
                    st.success("✅ Payment allocation applied successfully!")
                else:
                    st.error("Please fill in all required fields.")
    elif page == "Advanced SQL Queries":
        if role == "Super Admin":
            st.title("🖥️ Live SQL Business Analytics Engine")
            st.write("Select and execute queries to audit records from your tables.")

            queries = {
                "1. Retrieve all records from the sales table": {
                    "tier": "Basic Queries",
                    "sql": "SELECT * FROM customer_sales"
                },
                "2. Retrieve all branches": {
                    "tier": "Basic Queries",
                    "sql": "SELECT * FROM branches"
                },
                "3. Retrieve all payment splits": {
                    "tier": "Basic Queries",
                    "sql": "SELECT * FROM payments_splits"
                },
                "4. All Open sales": {
                    "tier": "Basic Queries",
                    "sql": "SELECT * FROM customer_sales WHERE status = 'Open'"
                },
                "5. All records from Chennai branch": {
                    "tier": "Basic Queries",
                    "sql": """
                        SELECT cs.* FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        WHERE b.branch_name = 'Chennai'
                    """
                },
                "6. Total revenue by branch": {
                    "tier": "Aggregate Queries",
                    "sql": """
                        SELECT b.branch_name, SUM(cs.gross_sales) AS total_revenue
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        GROUP BY b.branch_name
                        ORDER BY total_revenue DESC
                    """
                },
                "7. Total received amount by branch": {
                    "tier": "Aggregate Queries",
                    "sql": """
                        SELECT b.branch_name, SUM(cs.received_amount) AS total_received_amount
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        GROUP BY b.branch_name
                        ORDER BY total_received_amount DESC
                    """
                },
                "8. Total pending amount by branch": {
                    "tier": "Aggregate Queries",
                    "sql": """
                        SELECT b.branch_name, SUM(cs.pending_amount_gen) AS total_pending_amount
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        GROUP BY b.branch_name
                        ORDER BY SUM(cs.pending_amount_gen) DESC
                    """
                },
                "9. Total no of sales by branch": {
                    "tier": "Aggregate Queries",
                    "sql": """
                        SELECT b.branch_name, COUNT(cs.sale_id) AS total_sales
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        GROUP BY b.branch_name
                        ORDER BY total_sales DESC
                    """
                },
                "10. Total payments received per sale": {
                    "tier": "Join Queries",
                    "sql": """
                        SELECT cs.*,SUM(ps.amount_paid) AS total_payment
                        FROM customer_sales cs
                        JOIN payments_splits ps ON cs.sale_id = ps.sale_id
                        GROUP BY cs.sale_id
                        ORDER BY cs.sale_id
                    """
                },
                "11. Sales joined with branch name": {
                    "tier": "Join Queries",
                    "sql": """
                        SELECT cs.*, b.branch_name
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        ORDER BY cs.sale_id
                    """
                },
                "12. Sales joined with branch admin name": {
                    "tier": "Join Queries",
                    "sql": """
                        SELECT cs.*, b.branch_admin_name
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        ORDER BY cs.sale_id
                    """
                },
                "13. Branch wise total gross sale": {
                    "tier": "Join Queries",
                    "sql": """
                        SELECT b.branch_name, SUM(cs.gross_sales) AS total_gross_sale
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        GROUP BY b.branch_name
                    """
                },
                "14. Branch with highest gross sale": {
                    "tier": "Financial Tracking Queries",
                    "sql": """
                        SELECT b.branch_name, SUM(cs.gross_sales) AS total_gross_sale
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        GROUP BY b.branch_name
                        ORDER BY total_gross_sale DESC
                        LIMIT 1
                    """
                },
                "15. Top 3 branches with highest total gross sale": {
                    "tier": "Financial Tracking Queries",
                    "sql": """
                        SELECT b.branch_name, SUM(cs.gross_sales) AS total_gross_sale
                        FROM customer_sales cs
                        JOIN branches b ON cs.branch_id = b.branch_id
                        GROUP BY b.branch_name
                        ORDER BY total_gross_sale DESC
                        LIMIT 3
                    """
                },
                "16. Monthly revenue summary": {
                    "tier": "Financial Tracking Queries",
                    "sql": """
                        SELECT
                            TO_CHAR(sale_date, 'YYYY') AS year,
                            TO_CHAR(sale_date, 'MM') AS month,
                            SUM(gross_sales) AS total_revenue
                        FROM customer_sales
                        GROUP BY year, month
                        ORDER BY year, month
                    """
                },
            }

            selected_query = st.selectbox("Choose Targeted Predefined Operational Query",
                                          list(queries.keys()), key="sql_query_select")
            st.markdown(f"**Query Classification Tier:** {queries[selected_query]['tier']}")
            st.code(queries[selected_query]["sql"], language="sql")

            if st.button("Execute Live Database Transaction", key="execute_sql_btn"):
                try:
                    with engine.connect() as conn:
                        result_df = pd.read_sql(text(queries[selected_query]["sql"]), conn)
                    st.success(f"✅ Query executed successfully — {len(result_df)} rows returned")
                    st.dataframe(result_df, use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Query failed: {e}")
