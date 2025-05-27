import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

host = "db.fbkriebmhjectmlyrems.supabase.co"
port = 5432
database = "postgres"
user = "postgres"
password = "Hephzibah@1414"

# PostgreSQL credentials
# db_user = "postgres"
# db_pass = "Hephzibah@1414"
# db_host = "localhost"
# db_port = "5432"
# db_name = "amazonmart"

# Properly encode special characters in the password (like @)
encoded_pass = quote_plus(password)

# postgresql://postgres:encoded_pass@db.fbkriebmhjectmlyrems.supabase.co:5432/postgres

engine = create_engine(f'postgresql+psycopg2://{user}:{encoded_pass}@{host}:{port}/{database}')
# engine = create_engine(f'postgres+psycopg2://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}')

# Create engine
# engine = create_engine(f'postgresql+psycopg2://postgresql:Hephzibah@141@localhost:5432/amazonmart')
# DATABASE_URL = "postgresql://admin:secret@localhost:5432/salesdb"




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
            customers_df = pd.read_sql("SELECT customerid, firstname || ' ' || lastname AS fullname FROM customers", conn)
            customer_map = {f"{row.fullname} (ID: {row.customerid})": row.customerid for row in customers_df.itertuples()}

            customer_choice = st.selectbox("Select Customer", list(customer_map.keys()))

            # Load products
            products_df = pd.read_sql("SELECT productid, productname FROM products", conn)
            product_map = {f"{row.productname} (ID: {row.productid})": row.productid for row in products_df.itertuples()}

            selected_products = st.multiselect("Select Products", list(product_map.keys()))
            quantities = []
            for prod in selected_products:
                qty = st.number_input(f"Quantity for {prod}", min_value=1, step=1, key=prod)
                quantities.append(qty)

            if st.button("Place Order"):
                if selected_products and quantities:
                    customer_id = customer_map[customer_choice]
                    product_ids = [product_map[p] for p in selected_products]
                    
                    # Convert product_ids and quantities to PostgreSQL arrays
                    with engine.begin() as trans:
                        conn.execute(
                            text("CALL PlaceMultiProductOrder(:cust_id, :prod_ids::INTEGER[], :qtys::INTEGER[])"),
                            {
                                "cust_id": customer_id,
                                "prod_ids": product_ids,
                                "qtys": quantities
                            }
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
