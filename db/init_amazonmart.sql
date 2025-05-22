-- Create customers table
CREATE TABLE customers (
  CustomerID SERIAL PRIMARY KEY,
  FirstName VARCHAR(50) NOT NULL,
  LastName VARCHAR(50) NOT NULL,
  Email VARCHAR(100) NOT NULL UNIQUE,
  Phone VARCHAR(15),
  CHECK (Phone ~ '^[0-9]{10,15}$')
);

-- Create products table
CREATE TABLE products (
  ProductID SERIAL PRIMARY KEY,
  ProductName VARCHAR(100) NOT NULL,
  Price NUMERIC(10, 2) CHECK (Price > 0),
  StockQuantity INT CHECK (StockQuantity >= 0)
);

-- Create orders table
CREATE TABLE orders (
  OrderID SERIAL PRIMARY KEY,
  CustomerID INT REFERENCES customers(CustomerID),
  OrderDate TIMESTAMP NOT NULL,
  TotalAmount NUMERIC(10, 2) CHECK (TotalAmount > 0)
);

-- Create orderdetails table
CREATE TABLE orderdetails (
  OrderDetailID SERIAL PRIMARY KEY,
  OrderID INT REFERENCES orders(OrderID) ON DELETE CASCADE,
  ProductID INT REFERENCES products(ProductID),
  Quantity INT CHECK (Quantity > 0),
  Subtotal NUMERIC(10, 2) CHECK (Subtotal > 0)
);

-- Create addresses table
CREATE TABLE addresses (
  AddressID SERIAL PRIMARY KEY,
  CustomerID INT REFERENCES customers(CustomerID) ON DELETE CASCADE,
  Street VARCHAR(100),
  City VARCHAR(50),
  State VARCHAR(50),
  Country VARCHAR(50),
  ZipCode VARCHAR(10)
);

-- Create payments table
CREATE TABLE payments (
  PaymentID SERIAL PRIMARY KEY,
  OrderID INT REFERENCES orders(OrderID) ON DELETE CASCADE,
  PaymentDate TIMESTAMP NOT NULL,
  PaymentMethod VARCHAR(50),
  AmountPaid NUMERIC(10, 2),
  PaymentStatus VARCHAR(20) CHECK (PaymentStatus IN ('Pending', 'Completed', 'Failed'))
);

-- Create shipping table
CREATE TABLE shipping (
  ShippingID SERIAL PRIMARY KEY,
  OrderID INT REFERENCES orders(OrderID) ON DELETE CASCADE,
  ShippingAddressID INT REFERENCES addresses(AddressID),
  ShippingDate TIMESTAMP,
  DeliveryDate TIMESTAMP,
  ShippingMethod VARCHAR(50),
  ShippingStatus VARCHAR(20) CHECK (ShippingStatus IN ('Pending', 'Shipped', 'Delivered'))
);

-- Create logs table
CREATE TABLE logs (
  LogID SERIAL PRIMARY KEY,
  LogTime TIMESTAMP DEFAULT NOW(),
  LogMessage TEXT
);

-- Create returns table
CREATE TABLE returns (
  ReturnID SERIAL PRIMARY KEY,
  OrderID INT REFERENCES orders(OrderID) ON DELETE CASCADE,
  ProductID INT REFERENCES products(ProductID),
  QuantityReturned INT CHECK (QuantityReturned > 0),
  ReturnDate TIMESTAMP DEFAULT NOW(),
  RefundAmount NUMERIC(10, 2) CHECK (RefundAmount >= 0)
);

-- Insert sample data into customers
INSERT INTO customers (FirstName, LastName, Email, Phone) VALUES
('John', 'Doe', 'john.doe@example.com', '08012345678'),
('Jane', 'Smith', 'jane.smith@example.com', '08098765432'),
('Michael', 'Brown', 'michael.brown@example.com', '08123456789'),
('Emily', 'Davis', 'emily.davis@example.com', '08011223344'),
('Daniel', 'Wilson', 'daniel.wilson@example.com', '08099887766');

-- Insert sample data into products
INSERT INTO products (ProductName, Price, StockQuantity) VALUES
('Samsung Galaxy S22', 350000.00, 20),
('Apple iPhone 14', 450000.00, 15),
('HP Pavilion Laptop', 280000.00, 10),
('Sony WH-1000XM5 Headphones', 150000.00, 30),
('Logitech MX Master 3 Mouse', 45000.00, 50);

-- Insert sample addresses
INSERT INTO addresses (CustomerID, Street, City, State, Country, ZipCode) VALUES
(1, '123 Allen Ave', 'Ikeja', 'Lagos', 'Nigeria', '100001'),
(2, '456 Marina Rd', 'Victoria Island', 'Lagos', 'Nigeria', '101241'),
(3, '789 Garki Area 2', 'Abuja', 'FCT', 'Nigeria', '900211'),
(4, '12 Okumagba Ave', 'Warri', 'Delta', 'Nigeria', '332211'),
(5, '87 Osogbo Rd', 'Osogbo', 'Osun', 'Nigeria', '230101');

-- Create indexes
CREATE INDEX idx_products_productid ON products(ProductID);
CREATE INDEX idx_orders_customerid ON orders(CustomerID);
CREATE INDEX idx_orderdetails_orderid ON orderdetails(OrderID);
CREATE INDEX idx_payments_orderid ON payments(OrderID);

-- Function: PlaceMultiProductOrder
CREATE OR REPLACE FUNCTION PlaceMultiProductOrder(
  in_customer_id INT,
  in_product_ids INT[],
  in_quantities INT[]
)
RETURNS VOID AS $$
DECLARE
  idx INT;
  product_id INT;
  quantity INT;
  available_stock INT;
  product_price NUMERIC(10,2);
  subtotal NUMERIC(10,2);
  total_amount NUMERIC(10,2) := 0;
  new_order_id INT;
  customer_exists BOOLEAN;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM customers WHERE CustomerID = in_customer_id
  ) INTO customer_exists;

  IF NOT customer_exists THEN
    RAISE EXCEPTION 'Customer ID % does not exist.', in_customer_id;
  END IF;

  IF array_length(in_product_ids, 1) <> array_length(in_quantities, 1) THEN
    RAISE EXCEPTION 'Mismatched product IDs and quantities array lengths.';
  END IF;

  INSERT INTO orders (CustomerID, OrderDate, TotalAmount)
  VALUES (in_customer_id, NOW(), 0)
  RETURNING OrderID INTO new_order_id;

  FOR idx IN 1..array_length(in_product_ids, 1) LOOP
    product_id := in_product_ids[idx];
    quantity := in_quantities[idx];

    SELECT Price, StockQuantity INTO product_price, available_stock
    FROM products WHERE ProductID = product_id;

    IF NOT FOUND THEN
      RAISE EXCEPTION 'Product ID % not found.', product_id;
    END IF;

    IF available_stock < quantity THEN
      RAISE EXCEPTION 'Insufficient stock for Product ID %.', product_id;
    END IF;

    subtotal := product_price * quantity;
    total_amount := total_amount + subtotal;

    INSERT INTO orderdetails (OrderID, ProductID, Quantity, Subtotal)
    VALUES (new_order_id, product_id, quantity, subtotal);

    UPDATE products SET StockQuantity = StockQuantity - quantity
    WHERE ProductID = product_id;

    INSERT INTO logs(LogMessage)
    VALUES ('Product ' || product_id || ' x' || quantity || ' added to Order ' || new_order_id);
  END LOOP;

  UPDATE orders SET TotalAmount = total_amount WHERE OrderID = new_order_id;

  INSERT INTO logs(LogMessage)
  VALUES ('Order ' || new_order_id || ' placed successfully. Total: ' || total_amount);
END;
$$ LANGUAGE plpgsql;
