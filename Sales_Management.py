import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# Connection details
host = "localhost"
port = "5432"
database = "TestDB"
username = "postgres"
password = "guvi2026"

# Connection string (URL format) -> postgres
engine_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
engine = create_engine(engine_string)

# Read tables
df1 = pd.read_sql_table("branches", con=engine)
df2 = pd.read_sql_table("customer_sales", con=engine)
df3 = pd.read_sql_table("users", con=engine)
df4 = pd.read_sql_table("payments_splits", con=engine)

if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "branch_id" not in st.session_state:
    st.session_state.branch_id = None
if "branch_name" not in st.session_state:
    st.session_state.branch_name = None


# Check user credentials
def verify_user(username, password):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT user_name,roles FROM users WHERE user_name = :u AND user_password = :p"),
            {"u": username, "p": password}
        )
        return result.fetchone()


if st.session_state.user is None:

    st.title("Welcome To Sales Management System")
    st.subheader("Please login to continue")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = verify_user(username, password)
        if user:
            st.session_state.user = user[0]
            st.session_state.role = user[1]
            st.session_state.branch_id = None
            st.session_state.branch_name = None

            
            if str(user[1]).strip().lower() != "super admin":
                with engine.connect() as conn:
                    branch = conn.execute(text("""
                        SELECT b.branch_id, b.branch_name
                        FROM users u
                        JOIN branches b ON u.branch_id = b.branch_id
                        WHERE u.user_name = :name
                    """), {"name": user[0]}).fetchone()
                if branch:
                    st.session_state.branch_id = branch[0]
                    st.session_state.branch_name = branch[1]

            st.success("Login Successful")
            st.rerun()

        else:
            st.error("Invalid credentials")
else:

    # ---------- Sidebar ----------
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Dashboard & Reports", "Data Entry Workspace", "Advanced SQL Queries"],
        key="sidebar_nav"
    )

    is_super = str(st.session_state.role).replace(" ", "").lower() == "superadmin"

    st.sidebar.divider()
    st.sidebar.markdown(f"👤 **User:** {st.session_state.user}")
    st.sidebar.markdown(f"🛡️ **Role:** {st.session_state.role}")
    st.sidebar.markdown(f"🏢 **Branch:** {'All Branches' if is_super else st.session_state.branch_name}")

    if st.sidebar.button("Logout", key="sidebar_logout"):
        for key in ["user", "role", "branch_id", "branch_name"]:
            st.session_state[key] = None
        st.rerun()

    # ---------- Main ----------
    st.title("Sales Management System")
    st.success(f"Welcome {st.session_state.user}")

    # ---------- Role-based data scope ----------
   
    all_products = sorted(df2["product_name"].dropna().unique().tolist())

    if not is_super:
        if st.session_state.branch_id is None:
            st.error("No branch is assigned to your account. Please contact the Super Admin.")
            st.stop()
        df1 = df1[df1["branch_id"] == st.session_state.branch_id]
        df2 = df2[df2["branch_id"] == st.session_state.branch_id].copy()
        df4 = df4[df4["sale_id"].isin(df2["sale_id"])]

    # =====================================================
    # PAGE 1: DASHBOARD
    # =====================================================
    if page == "Dashboard & Reports":
        st.header("📊 Sales Dashboard")
        st.subheader("Filter Controls")

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        # Filters
        branches = df1['branch_name'].tolist()
        with col1:
            if is_super:
                selected_branch = st.selectbox("Select Branch", ["All"] + branches, index=0)
            else:
                st.selectbox("Branch", [st.session_state.branch_name], disabled=True)
                selected_branch = st.session_state.branch_name

        products = sorted(df2["product_name"].dropna().unique().tolist())
        with col2:
            selected_product = st.selectbox("Select Product", ["All"] + products, index=0)

        df2["sale_date"] = pd.to_datetime(df2["sale_date"])
        available_dates = df2["sale_date"].sort_values().dt.strftime("%Y-%m-%d").unique().tolist()

        if not available_dates:
            st.info("No sales records found.")
        else:
            with col3:
                start_date = st.selectbox("Select Start Date", available_dates, index=0, key="start_date_selectbox")
            with col4:
                end_date = st.selectbox("Select End Date", available_dates, index=len(available_dates) - 1, key="end_date_selectbox")

            filtered_df1 = df1.copy()
            filtered_df = df2.copy()

            if selected_branch != "All":
                filtered_df1 = filtered_df1[filtered_df1["branch_name"] == selected_branch]

            matching_branch_ids = filtered_df1["branch_id"].unique()
            filtered_df = filtered_df[filtered_df["branch_id"].isin(matching_branch_ids)]

            if selected_product != "All":
                filtered_df = filtered_df[filtered_df["product_name"] == selected_product]

            filtered_df = filtered_df[
                (filtered_df["sale_date"] >= pd.to_datetime(start_date)) &
                (filtered_df["sale_date"] <= pd.to_datetime(end_date))
            ]
            st.divider()

            st.subheader("📊 Financial Summary")
            m1, m2, m3, m4 = st.columns([5, 5, 5, 4])

            gross_total = filtered_df['gross_sales'].sum()
            received_total = filtered_df['received_amount'].sum()
            pending_total = filtered_df['pending_amount_gen'].sum()

            m1.metric("Overall Revenue (Gross)", f"₹{gross_total/100000:,.2f}L")
            m2.metric("Total Received Amount", f"₹{received_total/100000:,.2f}L")
            m3.metric("Total Pending Amount", f"₹{pending_total/100000:,.2f}L")

            pending_pct = (pending_total / gross_total * 100) if gross_total > 0 else 0
            m4.metric("Pending Collection Pct", f"{pending_pct:.1f}%")
            st.divider()
            st.subheader("Branch Sales Record Summary")
            st.dataframe(filtered_df, use_container_width=True)

    # =====================================================
    # PAGE 2: DATA ENTRY
    # =====================================================
    elif page == "Data Entry Workspace":
        st.title("📋 Operations Record Creator")

        tab1, tab2 = st.tabs(["Add New Sales Entry", "Log Payment Split Details"])

        with tab1:
            st.subheader("New Sale Generation")

            # Branch (locked for Admin)
            branches = df1["branch_name"].tolist()
            if is_super:
                selected_branch = st.selectbox("Select Target Branch", branches, key="entry_branch")
            else:
                st.selectbox("Target Branch", [st.session_state.branch_name], disabled=True, key="entry_branch_locked")
                selected_branch = st.session_state.branch_name

            # Customer & Product
            col1, col2 = st.columns(2)
            with col1:
                student_name = st.text_input("Customer Name", key="student_name")
            with col2:
                selected_course = st.selectbox("Select Product Name", all_products, key="entry_course")

            # Mobile & Date
            col3, col4 = st.columns(2)
            with col3:
                mobile = st.text_input("Mobile Number (10 digits)", key="mobile_number")
            with col4:
                joining_date = st.date_input("Sale Date", key="joining_date")

            # Gross Amount & Status
            gross_amount = st.number_input("Gross Sales Amount (₹)", min_value=0.0, format="%.2f", key="gross_amount")
            order_status = st.selectbox("Initial Order Status", ["Open", "Close"], key="order_status")

            if st.button("Submit Entry", key="submit_sales_entry"):
                if not (student_name.strip() and mobile.strip()):
                    st.error("Please fill in all required fields.")
                elif not (mobile.isdigit() and len(mobile) == 10):
                    st.error("Mobile number must be exactly 10 digits.")
                elif gross_amount <= 0:
                    st.error("Gross sales amount must be greater than 0.")
                else:
                    branch_id = int(df1[df1["branch_name"] == selected_branch]["branch_id"].values[0])

                    # Server-side guard: Admin can only add sales for their own branch
                    if not is_super and branch_id != st.session_state.branch_id:
                        st.error("You can only add sales for your own branch.")
                        st.stop()

                    try:
                        with engine.begin() as conn:
                            conn.execute(text(
                                "SELECT setval('customer_sales_sale_id_seq', "
                                "COALESCE((SELECT MAX(sale_id) FROM customer_sales), 1))"))
                            conn.execute(text("""
                                INSERT INTO customer_sales
                                    (branch_id, sale_date, customer_name, mobile_number, product_name, gross_sales, received_amount, status)
                                VALUES
                                    (:branch_id, :date, :name, :mobile_number, :product_name, :gross_sales, 0, :status)
                            """), {
                                "branch_id": branch_id,
                                "date": joining_date,
                                "name": student_name.strip(),
                                "mobile_number": mobile,
                                "product_name": selected_course,
                                "gross_sales": gross_amount,
                                "status": order_status
                            })
                        st.success("✅ Sale entry added successfully!")
                    except Exception as e:
                        st.error(f"❌ Could not save sale: {e}")

        with tab2:
            st.subheader("Log Payment Split Details")

            # Only sales with pending amount; Admin sees only their branch
            branch_filter = "" if is_super else "AND branch_id = :bid"
            with engine.connect() as conn:
                active_sales = pd.read_sql(text(f"""
                    SELECT sale_id, customer_name, product_name, pending_amount_gen
                    FROM customer_sales
                    WHERE (gross_sales - received_amount) > 0 {branch_filter}
                    ORDER BY sale_id
                """), conn, params={} if is_super else {"bid": st.session_state.branch_id})

            if active_sales.empty:
                st.info("No sales with pending amounts.")
            else:
                # label -> (sale_id, pending amount)
                options = {
                    f"ID {r.sale_id} - {r.customer_name} ({r.product_name}) - ₹{r.pending_amount_gen:,.2f} Pending":
                        (int(r.sale_id), float(r.pending_amount_gen))
                    for r in active_sales.itertuples()
                }

                selected_sale = st.selectbox("Select Target Active Sale", list(options.keys()), key="payment_sale")
                selected_sale_id, max_pending = options[selected_sale]

                # Payment details
                payment_channel = st.selectbox("Payment Collection Channel",
                                               ["Cash", "UPI", "Card"],
                                               key="payment_channel")

                split_amount = st.number_input("Collected Split Amount (₹)",
                                               min_value=0.01,
                                               max_value=max(max_pending, 0.01),
                                               format="%.2f",
                                               key="split_amount")

                payment_date = st.date_input("Payment Date", key="payment_date")

                # Submit
                if st.button("Apply Payment Allocation", key="apply_payment_btn"):

                    
                    with engine.connect() as conn:
                        owner_branch = conn.execute(
                            text("SELECT branch_id FROM customer_sales WHERE sale_id = :sid"),
                            {"sid": selected_sale_id},
                        ).scalar()

                    
                    if not is_super and owner_branch != st.session_state.branch_id:
                        st.error("You can only add payments for sales of your own branch.")
                        st.stop()

                    
                    try:
                        with engine.begin() as conn:
                            conn.execute(text(
                                "SELECT setval('payments_splits_payment_id_seq', "
                                "COALESCE((SELECT MAX(payment_id) FROM payments_splits), 1))"))
                            conn.execute(text("""
                                INSERT INTO payments_splits
                                    (sale_id, payment_date, amount_paid, payment_method)
                                VALUES
                                    (:sale_id, :payment_date, :amount_paid, :payment_method)
                            """), {
                                "sale_id": selected_sale_id,
                                "payment_date": payment_date,
                                "amount_paid": split_amount,
                                "payment_method": payment_channel
                            })
                        st.success("✅ Payment allocation applied successfully!")
                    except Exception as e:
                        st.error(f"❌ Could not save payment: {e}")

    # =====================================================
    # PAGE 3: SQL QUERIES
    # =====================================================
    elif page == "Advanced SQL Queries":
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
            "5. All records of a selected branch": {
                "tier": "Basic Queries",
                "sql": """
                    SELECT cs.* FROM customer_sales cs
                    JOIN branches b ON cs.branch_id = b.branch_id
                    WHERE b.branch_name = :bname
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
                    SELECT b.branch_name, SUM(cs.received_amount) AS total_received
                    FROM customer_sales cs
                    JOIN branches b ON cs.branch_id = b.branch_id
                    GROUP BY b.branch_name
                    ORDER BY total_received DESC
                """
            },
            "8. Total pending amount by branch": {
                "tier": "Aggregate Queries",
                "sql": """
                    SELECT b.branch_name,
                           SUM(cs.pending_amount_gen) AS total_pending
                    FROM customer_sales cs
                    JOIN branches b ON cs.branch_id = b.branch_id
                    GROUP BY b.branch_name
                """
            },
            "9. Total no of sales by branch": {
                "tier": "Aggregate Queries",
                "sql": """
                    SELECT b.branch_name, COUNT(*) AS total_sales
                    FROM customer_sales cs
                    JOIN branches b ON cs.branch_id = b.branch_id
                    GROUP BY b.branch_name
                    ORDER BY total_sales DESC
                """
            },
            "10. Total payments received per sale": {
                "tier": "Join Queries",
                "sql": """
                    SELECT cs.sale_id, cs.customer_name, cs.gross_sales,
                           COALESCE(SUM(ps.amount_paid), 0) AS total_payment
                    FROM customer_sales cs
                    LEFT JOIN payments_splits ps ON cs.sale_id = ps.sale_id
                    GROUP BY cs.sale_id, cs.customer_name, cs.gross_sales
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
                                      list(queries.keys()))
        st.markdown(f"**Query Classification Tier:** {queries[selected_query]['tier']}")

        base_sql = queries[selected_query]["sql"]
        params = {}

        # Query 5 needs a branch name
        if ":bname" in base_sql:
            params["bname"] = st.selectbox("Branch", df1["branch_name"].tolist(), key="q_branch")

        # Admin: restrict all three tables to their own branch with WITH clauses
        sql_to_run = base_sql
        if not is_super:
            sql_to_run = """
                WITH customer_sales AS (SELECT * FROM customer_sales WHERE branch_id = :scope_bid),
                     branches AS (SELECT * FROM branches WHERE branch_id = :scope_bid),
                     payments_splits AS (SELECT * FROM payments_splits
                                         WHERE sale_id IN (SELECT sale_id FROM customer_sales))
            """ + base_sql
            params["scope_bid"] = st.session_state.branch_id

        st.code(base_sql.strip(), language="sql")
        if not is_super:
            st.caption(f"🔒 Results are restricted to your branch: {st.session_state.branch_name}")

        if st.button("Execute Live Database Transaction", key="execute_sql_btn"):
            try:
                with engine.connect() as conn:
                    result_df = pd.read_sql(text(sql_to_run), conn, params=params)
                st.success(f"✅ Query executed successfully — {len(result_df)} rows returned")
                st.dataframe(result_df, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Query failed: {e}")
