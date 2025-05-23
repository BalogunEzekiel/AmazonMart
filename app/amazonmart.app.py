import streamlit as st
import pandas as pd

# Uncomment and edit this if running locally
# import psycopg2
# def get_connection():
#     return psycopg2.connect(
#         host="localhost",
#         port="5432",
#         database="amazonmart",
#         user="postgres",
#         password="Hephzibah@1414"
#     )

# Use Streamlit experimental connection (make sure to configure this on Streamlit Cloud)
conn = st.experimental_connection("postgresql")

st.title("📦 AmazonMart Order Management")

menu = ["View Products", "Place Order", "Order History"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "View Products":
    st.subheader("Available Products")
    try:
        df = conn.query("SELECT * FROM products ORDER BY productid")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading products: {e}")

elif choice == "Place Order":
    st.subheader("🛒 Place New Order")
    try:
        # Load customers
        customers_df = conn.query("SELECT customerid, firstname || ' ' || lastname AS fullname FROM customers")
        customer_map = {f"{row.fullname} (ID: {row.customerid})": row.customerid for row in customers_df.itertuples()}

        customer_choice = st.selectbox("Select Customer", list(customer_map.keys()))

        # Load products
        products_df = conn.query("SELECT productid, productname FROM products")
        product_map = {f"{row.productname} (ID: {row.productid})": row.productid for row in products_df.itertuples()}

        selected_products = st.multiselect("Select Products", list(product_map.keys()))
        quantities = []
        for prod in selected_products:
            qty = st.number_input(f"Quantity for {prod}", min_value=1, step=1, key=prod)
            quantities.append(qty)

        if st.button("Place Order"):
            if selected_products and quantities:
                product_ids = [product_map[p] for p in selected_products]
                # Note: Streamlit's connection API may not support callproc directly; 
                # you might need to run a parameterized query or a function call via SQL
                # Example raw SQL call for stored procedure, adjust for your DB:
                sql = "CALL PlaceMultiProductOrder(%s, %s, %s);"
                conn.execute(sql, (customer_map[customer_choice], product_ids, quantities))
                st.success("Order placed successfully!")
            else:
                st.warning("Please select at least one product and specify quantities.")
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
        df = conn.query(query)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error fetching order history: {e}")
