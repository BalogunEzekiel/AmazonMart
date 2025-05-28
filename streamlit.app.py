import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from io import BytesIO
import datetime

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

menu = ["View Products", "Place Order", "Order History", "Add Product/Customer", "Track Orders"]
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

# --- Admin Panel ---
elif choice == "Add Product/Customer":
    st.subheader("👨‍💼 Admin Panel")
    tab1, tab2, tab3 = st.tabs(["Add Product", "Add Customer", "Dashboard"])

    # --- Add Product ---
    with tab1:
        st.text("Enter new product details")
        product name = st.text_input("name", key="product_name")
        category = st.text_input("category", key="product_category")
        price = st.number_input("price", min_value=0.0, step=0.01, key="product_price")
        stock quantity = st.number_input("stock_quantity", min_value=0, step=1, key="product_stock")
       
        if st.button("Add Product"):
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO products (name, category, price, stock_quantity) VALUES (:name, :category, :price, :stock_quantity)"),
                        {"name": name, "category": category, "price": price, "stock_quantity": stock_quantity}
                    )
                st.success("✅ Product added!")
            except Exception as e:
                st.error(f"❌ Error adding product: {e}")

        # Display all products after insertion
        try:
            with engine.connect() as conn:
                products_df = pd.read_sql(text("SELECT * FROM products ORDER BY product_id DESC"), conn)
            st.dataframe(products_df)
        except Exception as e:
            st.error(f"❌ Error loading products: {e}")

    # --- Add Customer ---
    with tab2:
        st.text("Enter new customer details")
        customer name = st.text_input("name", key="customer_name")  # Changed variable name too
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
        st.text("Data-Driven Insights (Coming soon)")

    with tab3:
        st.text("Data-Driven Insights")


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
