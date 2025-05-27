import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# --- Database Connection ---
@st.cache_resource
def get_engine():
    """
    Create and cache SQLAlchemy engine with SSL enforced.
    """
    try:
        host = st.secrets["supabase"]["host"]
        port = st.secrets["supabase"]["port"]
        database = st.secrets["supabase"]["database"]
        user = st.secrets["supabase"]["user"]
        password = st.secrets["supabase"]["password"]

        # URL-encode password to handle special characters
        encoded_password = quote_plus(password)

        # Build connection string with sslmode=require
        DATABASE_URL = (f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}"
            "?sslmode=require"
        )

        engine = create_engine(DATABASE_URL)
        return engine

    except KeyError as e:
        st.error(f"Missing secret key: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Database connection error: {e}")
        st.stop()

# Initialize engine
engine = get_engine()

# --- Streamlit UI ---
st.title("📦 AmazonMart Order Management")

menu = ["View Products", "Place Order", "Order History"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "View Products":
    st.subheader("Available Products")
    try:
        with engine.connect() as conn:
            df = pd.read_sql("SELECT * FROM products", conn)
            st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading products: {e}")

elif choice == "Place Order":
    st.subheader("🛒 Place New Order")
    try:
        with engine.connect() as conn:
            # Load customers
            customers_df = pd.read_sql(
                "SELECT customer_id, firstname || ' ' || lastname AS fullname FROM customers", conn
            )
            customer_map = {
                f"{row.fullname} (ID: {row.customerid})": row.customerid for row in customers_df.itertuples()
            }

            customer_choice = st.selectbox("Select Customer", list(customer_map.keys()))

            # Load products
            products_df = pd.read_sql("SELECT productid, productname FROM products", conn)
            product_map = {
                f"{row.productname} (ID: {row.productid})": row.productid for row in products_df.itertuples()
            }

            selected_products = st.multiselect("Select Products", list(product_map.keys()))
            quantities = []
            for prod in selected_products:
                qty = st.number_input(f"Quantity for {prod}", min_value=1, step=1, key=prod)
                quantities.append(qty)

            if st.button("Place Order"):
                if selected_products and quantities:
                    customer_id = customer_map[customer_choice]
                    product_ids = [product_map[p] for p in selected_products]

                    with conn.begin() as trans:  # Start transaction
                        conn.execute(
                            text(
                                "CALL PlaceMultiProductOrder(:cust_id, :prod_ids::INTEGER[], :qtys::INTEGER[])"
                            ),
                            {
                                "cust_id": customer_id,
                                "prod_ids": product_ids,
                                "qtys": quantities,
                            },
                        )
                    st.success("Order placed successfully!")
                else:
                    st.warning("Please select products and quantities.")
    except Exception as e:
        st.error(f"Error placing order: {e}")

elif choice == "Order History":
    st.subheader("📜 Order History")
    try:
        query = """
            SELECT o.orderid, c.firstname || ' ' || c.lastname AS customer, o.orderdate, o.totalamount,
                   p.productname, od.quantity, od.subtotal
            FROM orders o
            JOIN customers c ON o.customerid = c.customerid
            JOIN orderdetails od ON o.orderid = od.orderid
            JOIN products p ON od.productid = p.productid
            ORDER BY o.orderdate DESC
        """
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            st.dataframe(df)
    except Exception as e:
        st.error(f"Error fetching order history: {e}")
