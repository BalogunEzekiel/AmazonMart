from datetime import datetime
import streamlit as st
import psycopg2
import pandas as pd

# Database connection setup using provided details
def get_connection():
    return psycopg2.connect(
        host="localhost",
        port="5432",
        database="amazonmart",
        user="postgres",
        password="Hephzibah@1414"
    )

# Streamlit App Title
st.title("📦 AmazonMart Order Management")

# Sidebar Menu
menu = ["View Products", "Place Order", "Order History"]
choice = st.sidebar.selectbox("Navigation", menu)

# View Products
if choice == "View Products":
    st.subheader("Available Products")
    try:
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM products ORDER BY productid", conn)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading products: {e}")
    finally:
        conn.close()

# Place Order
elif choice == "Place Order":
    st.subheader("🛒 Place New Order")
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Load customers
        cur.execute("SELECT customerid, firstname || ' ' || lastname FROM customers")
        customers = cur.fetchall()
        customer_map = {f"{name} (ID: {cid})": cid for cid, name in customers}
        customer_choice = st.selectbox("Select Customer", list(customer_map.keys()))

        # Load products
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
        conn.close()

# Order History
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
        conn.close()
