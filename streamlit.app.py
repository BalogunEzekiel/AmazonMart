import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime

# Database connection setup
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="amazonmart",
        user="postgres",
        password="Hephzibah@1414"
    )
    
# App title
st.title("📦 AmazonMart Order Management")

menu = ["View Products", "Place Order", "Order History"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "View Products":
    st.subheader("Available Products")
    conn = None  # ✅ Declare before try
    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM products ORDER BY productid", conn)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading products: {e}")
    finally:
        if conn:  # ✅ Only close if connection succeeded
            conn.close()

elif choice == "Place Order":
    st.subheader("🛒 Place New Order")
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get customers and products
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
            if selected_products and quantities:
                product_ids = [product_map[p] for p in selected_products]
                cur.callproc('PlaceMultiProductOrder', [customer_map[customer_choice], product_ids, quantities])
                conn.commit()
                st.success("Order placed successfully!")
            else:
                st.warning("Please select at least one product and specify quantities.")
    except Exception as e:
        st.error(f"Error placing order: {e}")
    finally:
        if conn:
            conn.close()

elif choice == "Order History":
    st.subheader("📜 Order History")
    try:
        conn = get_connection()
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
    finally:
        if conn:
            conn.close()
