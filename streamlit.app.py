import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from io import BytesIO
import datetime
import numpy as np

# --- Database Connection ---
@st.cache_resource
def get_engine():
    try:
        host = st.secrets["supabase"]["host"]
        port = st.secrets["supabase"]["port"]
        database = st.secrets["supabase"]["database"]
        user = st.secrets["supabase"]["user"]
        password = st.secrets["supabase"]["password"]

        encoded_password = quote_plus(password)
        DATABASE_URL = (
            f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}?sslmode=require"
        )

        return create_engine(DATABASE_URL)

    except KeyError as e:
        st.error(f"Missing secret key: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Database connection error: {e}")
        st.stop()

engine = get_engine()

# --- Helper: Download Function ---
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return output

# --- Streamlit UI ---
st.title("📦 AmazonMart Order Management")

menu = ["View Products", "Place Order", "Order History", "Track Orders", "Admin Panel"]
choice = st.sidebar.selectbox("Navigation", menu)

# --- View Products ---
if choice == "View Products":
    st.subheader("📋 Available Products")
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM products"), conn)

        search_term = st.text_input("Search Product")
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False, na=False)]

        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        excel_data = convert_df_to_excel(df)

        st.download_button("Download CSV", csv, "products.csv", "text/csv")

    except Exception as e:
        st.error(f"Error loading products: {e}")

# --- Place Order ---
elif choice == "Place Order":
    st.subheader("🛒 Place New Order")
    try:
        with engine.connect() as conn:
            customers_df = pd.read_sql(text("SELECT customer_id, name AS fullname FROM customers"), conn)
            customer_map = {f"{row.fullname} (ID: {row.customer_id})": row.customer_id for row in customers_df.itertuples()}
            customer_choice = st.selectbox("Select Customer", list(customer_map.keys()))

            products_df = pd.read_sql(text("SELECT product_id, name FROM products"), conn)
            product_map = {f"{row.name} (ID: {row.product_id})": row.product_id for row in products_df.itertuples()}
            selected_products = st.multiselect("Select Products", list(product_map.keys()))
            quantities = [st.number_input(f"Quantity for {prod}", min_value=1, step=1, key=prod) for prod in selected_products]

        if st.button("Place Order"):
            if selected_products and quantities:
                customer_id = customer_map[customer_choice]
                product_ids = [product_map[p] for p in selected_products]
                try:
                    with engine.begin() as conn:
                        conn.execute(
                            text("CALL PlaceMultiProductOrder(:customer_id, :product_ids, :qtys)"),
                            {"customer_id": customer_id, "product_ids": product_ids, "qtys": quantities}
                        )
                    st.success("✅ Order placed successfully!")
                except Exception as e:
                    st.error(f"❌ Error placing order: {e}")
            else:
                st.warning("⚠️ Please select products and quantities.")
    except Exception as e:
        st.error(f"❌ Error loading customer/product data: {e}")

# --- Order History ---
elif choice == "Order History":
    st.subheader("📜 Order History")
    try:
        query = """
            SELECT o.order_id, c.name AS customer, o.order_date, p.name AS product,
                   oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) AS total_amount
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN order_items oi ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            ORDER BY o.order_date DESC
            LIMIT 50
        """
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)

        st.dataframe(df)

        csv = df.to_csv(index=False).encode('utf-8')
        excel_data = convert_df_to_excel(df)

        st.download_button("Download CSV", csv, "order_history.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ Error fetching order history: {e}")

# --- Real-Time Order Tracking ---
elif choice == "Track Orders":
    st.subheader("📡 Real-Time Order Tracking")
    try:
        query = """
            SELECT o.order_id, c.name AS customer, o.order_date, p.name AS product,
                   oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) AS total_amount
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN order_items oi ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.order_date >= CURRENT_DATE - INTERVAL '1 day'
            ORDER BY o.order_date DESC
        """
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        st.dataframe(df)
    except Exception as e:
        st.error(f"❌ Error fetching live orders: {e}")

# --- Admin Panel ---
elif choice == "Admin Panel":
    st.subheader("👨‍💼 Admin Panel")
    tab1, tab2, tab3 = st.tabs(["Add Product", "Add Customer", "Dashboard"])

# --- Add Product Tab ---
    with tab1:
        st.markdown("### ➕ Add Product")
        mode = st.radio("Select Mode", ["New Product", "Existing Product"])

        try:
            with engine.connect() as conn:
                categories_df = pd.read_sql("SELECT DISTINCT category FROM products", conn)
                product_list_df = pd.read_sql("SELECT * FROM products ORDER BY name", conn)
        except Exception as e:
            st.error(f"Error loading data: {e}")

        if mode == "New Product":
            name = st.text_input("Product Name")
            category = st.selectbox("Category", categories_df['category'].unique())
            price = st.number_input("Price", min_value=0.0, step=0.01)
            quantity = st.number_input("Stock Quantity", min_value=0, step=1)

            if st.button("Add New Product"):
                if name and category:
                    try:
                        with engine.begin() as conn:
                            conn.execute(
                                text("INSERT INTO products (name, category, price, stock_quantity) VALUES (:name, :category, :price, :quantity)"),
                                {"name": name, "category": category, "price": price, "quantity": quantity}
                            )
                        st.success("✅ New product added!")
                    except Exception as e:
                        st.error(f"Error adding product: {e}")
                else:
                    st.warning("Please fill all required fields.")

        else:  # Existing Product
            existing_product = st.selectbox("Select Existing Product", product_list_df['name'])
            selected = product_list_df[product_list_df['name'] == existing_product].iloc[0]
            st.text_input("Category", value=selected['category'], disabled=True)
            price = st.number_input("Price", min_value=0.0, step=0.01, value=float(selected['price']))
            quantity = st.number_input("Add Quantity", min_value=0, step=1)

            if st.button("Update Existing Product"):
                try:
                    with engine.begin() as conn:
                        # Always update price and add to stock_quantity for the same product_id
                        conn.execute(
                            text("""
                                UPDATE products 
                                SET price = :price,
                                    stock_quantity = stock_quantity + :quantity 
                                WHERE product_id = :pid
                            """),
                            {
                                "price": float(price),
                                "quantity": int(quantity),
                                "pid": int(selected['product_id'])
                            }
                        )
        st.success("✅ Product updated successfully.")
    except Exception as e:
        st.error(f"Error updating product: {e}")

                    st.success("Product updated successfully.")
                except Exception as e:
                    st.error(f"Error updating product: {e}")

        # Show current products
        try:
            with engine.connect() as conn:
                df = pd.read_sql("SELECT * FROM products ORDER BY product_id DESC", conn)
                st.dataframe(df)
        except Exception as e:
            st.error(f"Error loading products: {e}")

    # --- Add Customer ---
    with tab2:
        st.text("Enter new customer details")
        customer_name = st.text_input("name", key="customer_name")  # Changed variable name too
        email = st.text_input("email", key="customer_email")
        city = st.text_input("city", key="customer_city")
        country = st.text_input("country", key="customer_country")
        registration_date = st.date_input("registration_date", value=datetime.date.today(), key="customer_reg_date")

        if st.button("Add Customer"):
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO customers (name, email, city, country, registration_date) VALUES (:name, :email, :city, :country, :registration_date)"),
                        {
                            "name": cust_name,
                            "email": email,
                            "city": city,
                            "country": country,
                            "registration_date": registration_date
                        }
                    )
                st.success("✅ Customer added!")
            except Exception as e:
                st.error(f"❌ Error adding customer: {e}")

        # Display all customers after insertion
        try:
            with engine.connect() as conn:
                customers_df = pd.read_sql(text("SELECT * FROM customers ORDER BY customer_id DESC"), conn)
            st.dataframe(customers_df)
        except Exception as e:
            st.error(f"❌ Error loading customers: {e}")

    # --- Placeholder Dashboard tab ---

    with tab3:
        st.title("📊 Admin Dashboard")

        # Expandable Insight Sections
        with st.expander("👥 Customer Insights", expanded=False):
            try:
                with engine.connect() as conn:
                    total_customers = pd.read_sql(
                        "SELECT COUNT(DISTINCT customer_id) AS total_customers FROM customers", conn)
                    st.metric("Total Customers", total_customers['total_customers'][0])
    
                    by_country = pd.read_sql("""
                        SELECT country, COUNT(customer_id) AS num_customers
                        FROM customers
                        GROUP BY country
                        ORDER BY num_customers DESC
                    """, conn)
                    st.bar_chart(by_country.set_index("country"))
    
                    by_city = pd.read_sql("""
                        SELECT city, country, COUNT(customer_id) AS num_customers
                        FROM customers
                        GROUP BY city, country
                        ORDER BY num_customers DESC
                        LIMIT 10
                    """, conn)
                    st.write("### 🏙️ Top 10 Cities by Customers")
                    st.dataframe(by_city)
    
                    top_spenders = pd.read_sql("""
                        SELECT
                            c.customer_id,
                            c.name,
                            c.email,
                            SUM(p.amount) AS total_spending
                        FROM customers c
                        JOIN orders o ON c.customer_id = o.customer_id
                        JOIN payments p ON o.order_id = p.order_id
                        GROUP BY c.customer_id, c.name, c.email
                        ORDER BY total_spending DESC
                        LIMIT 10
                    """, conn)
                    st.write("### 💰 Top 10 Customers by Spending")
                    st.dataframe(top_spenders)
    
                    monthly_regs = pd.read_sql("""
                        SELECT
                            TO_CHAR(registration_date, 'YYYY-MM') AS registration_month,
                            COUNT(customer_id) AS new_customers
                        FROM customers
                        GROUP BY registration_month
                        ORDER BY registration_month
                    """, conn)
                    st.write("### 📅 Monthly Customer Registrations")
                    st.line_chart(monthly_regs.set_index("registration_month"))
    
                    yearly_regs = pd.read_sql("""
                        SELECT
                            EXTRACT(YEAR FROM registration_date) AS registration_year,
                            COUNT(customer_id) AS new_customers
                        FROM customers
                        GROUP BY registration_year
                        ORDER BY registration_year
                    """, conn)
                    st.write("### 🗓️ Yearly Customer Registrations")
                    st.bar_chart(yearly_regs.set_index("registration_year"))
    
            except Exception as e:
                st.error(f"❌ Error loading Customer Insights: {e}")
    
        with st.expander("📦 Orders Analysis", expanded=False):
            try:
                with engine.connect() as conn:
                    order_status = pd.read_sql("""
                        SELECT status, COUNT(order_id) AS count
                        FROM orders
                        GROUP BY status
                        ORDER BY count DESC
                    """, conn)
                    st.write("### 📦 Orders by Status")
                    st.bar_chart(order_status.set_index("status"))
    
                    orders_by_month = pd.read_sql("""
                        SELECT TO_CHAR(order_date, 'YYYY-MM') AS order_month, COUNT(order_id) AS num_orders
                        FROM orders
                        GROUP BY order_month
                        ORDER BY order_month
                    """, conn)
                    st.write("### 📅 Monthly Orders")
                    st.line_chart(orders_by_month.set_index("order_month"))
    
                    top_customers = pd.read_sql("""
                        SELECT c.name, COUNT(o.order_id) AS total_orders
                        FROM customers c
                        JOIN orders o ON c.customer_id = o.customer_id
                        GROUP BY c.name
                        ORDER BY total_orders DESC
                        LIMIT 10
                    """, conn)
                    st.write("### 🏆 Top 10 Customers by Orders")
                    st.dataframe(top_customers)
    
            except Exception as e:
                st.error(f"❌ Error loading Orders Analysis: {e}")
    
        with st.expander("🛍️ Product Analysis", expanded=False):
            try:
                with engine.connect() as conn:
                    top_products = pd.read_sql("""
                        SELECT p.name, SUM(oi.quantity) AS total_sold
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.product_id
                        GROUP BY p.name
                        ORDER BY total_sold DESC
                        LIMIT 10
                    """, conn)
                    st.write("### 🛍️ Top 10 Best-Selling Products")
                    st.dataframe(top_products)
    
                    category_sales = pd.read_sql("""
                        SELECT category, SUM(oi.quantity) AS total_quantity
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.product_id
                        GROUP BY category
                        ORDER BY total_quantity DESC
                    """, conn)
                    st.write("### 🗂️ Sales by Product Category")
                    st.bar_chart(category_sales.set_index("category"))
    
            except Exception as e:
                st.error(f"❌ Error loading Product Analysis: {e}")
    
        with st.expander("💳 Payment Insights", expanded=False):
            try:
                with engine.connect() as conn:
                    payment_methods = pd.read_sql("""
                        SELECT payment_method, COUNT(payment_id) AS num_payments
                        FROM payments
                        GROUP BY payment_method
                        ORDER BY num_payments DESC
                    """, conn)
                    st.write("### 💳 Payment Methods Distribution")
                    st.bar_chart(payment_methods.set_index("payment_method"))
    
                    monthly_revenue = pd.read_sql("""
                        SELECT TO_CHAR(payment_date, 'YYYY-MM') AS pay_month, SUM(amount) AS total_revenue
                        FROM payments
                        GROUP BY pay_month
                        ORDER BY pay_month
                    """, conn)
                    st.write("### 📈 Monthly Revenue")
                    st.line_chart(monthly_revenue.set_index("pay_month"))
    
            except Exception as e:
                st.error(f"❌ Error loading Payment Insights: {e}")
