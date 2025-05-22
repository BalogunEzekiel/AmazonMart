# app.py

import streamlit as st
import psycopg2
import pandas as pd

# Connect to PostgreSQL
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="amazonmart",
        user="your_username",
        password="your_password"
    )

# Load customer data
def load_customers():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM customers", conn)
    conn.close()
    return df

# Streamlit UI
st.title("📦 AmazonMart Dashboard")

st.subheader("👤 Customer List")
customers_df = load_customers()
st.dataframe(customers_df)
