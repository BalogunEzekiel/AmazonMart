import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import psycopg2

DB_HOST = "your-db-host.supabase.co"
DB_PORT = "5432"
DB_NAME = "your-db-name"
DB_USER = "your-db-user"
DB_PASS = "your-db-password"

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=secrets(host),
        port=secrets(port),
        database=secrets(database),
        user=secrets(user),
        password=secrets(password),
        sslmode='require'
    )

def run_query(query):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

st.title("📦 AmazonMart Order Management")

menu = ["View Products", "Place Order", "Order History"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "View Products":
    st.subheader("Available Products")
    try:
        df = pd.read_sql("SELECT * FROM products", engine)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading products: {e}")

elif choice == "Place Order":
    st.subheader("🛒 Place New Order")
    try:
        with engine.connect() as conn:
            # Load customers
            customers_df = pd.read_sql(
                "SELECT customerid, firstname || ' ' || lastname AS fullname FROM customers", conn
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

                    with engine.begin() as trans:
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
        df = pd.read_sql(query, engine)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error fetching order history: {e}")
