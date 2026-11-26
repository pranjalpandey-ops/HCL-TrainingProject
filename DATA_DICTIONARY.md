# Data Dictionary

## customers.csv
- customer_id: unique customer identifier
- customer_name: synthetic customer label
- city, state: customer geography
- customer_type: New, Returning, or Loyal

## products.csv
- product_id: unique product identifier
- product_name: synthetic product label
- category: product category
- unit_price: list price in INR

## orders.csv
- order_id: unique order identifier
- customer_id: customer placing order
- order_date: order date
- order_status: Completed or Cancelled

## order_items.csv
- order_item_id: unique order-line identifier
- order_id, product_id: related order and product
- quantity, unit_price, discount_pct
- line_total: discounted line value

## returns.csv
- return_id: unique return identifier
- order_item_id: original order line
- return_date, return_quantity, return_reason
- refund_amount: refund value in INR
- return_status: approval status
