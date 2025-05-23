import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Initialize connection only once
# Use cache_resource to cache the DB connection
@st.cache_resource
def init_connection():
    return psycopg2.connect(**st.secrets["postgres"])

conn = init_connection()

# Use cache_data to cache query results
@st.cache_data(ttl=600)
def run_query(query):
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()
        
# App title
st.title("📦 AmazonMart Order Management")

# Sidebar navigation
menu = ["View Products", "Place Order", "Order History"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "View Products":
    st.subheader("Available Products")
    try:
        df = pd.read_sql("SELECT * FROM products ORDER BY productid", conn)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading products: {e}")

elif choice == "Place Order":
    st.subheader("🛒 Place New Order")
    try:
        cur = conn.cursor()

        # Fetch customer and product data
        cur.execute("SELECT customerid, firstname || ' ' || lastname FROM customers")
        customers = cur.fetchall()
        customer_map = {f"{name} (ID: {cid})": cid for cid, name in customers}
        customer_choice = st.selectbox("Select Customer", list(customer_map.keys()))

        cur.execute("SELECT productid, productname FROM products")
        products = cur.fetchall()
        product_map = {f"{name} (ID: {pid})": pid for pid, name in products}

        selected_products = st.multiselect("Select Products", list(product_map.keys()))
        quantities = []
        for prod in selected_products:
            qty = st.number_input(f"Quantity for {prod}", min_value=1, step=1)
            quantities.append(qty)

        if st.button("Place Order"):
            if selected_products and all(qty > 0 for qty in quantities):
                product_ids = [product_map[p] for p in selected_products]
                cur.callproc('PlaceMultiProductOrder', [customer_map[customer_choice], product_ids, quantities])
                conn.commit()
                st.success("Order placed successfully!")
            else:
                st.warning("Please select at least one product and specify valid quantities.")
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
        df = pd.read_sql(query, conn)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error fetching order history: {e}")
