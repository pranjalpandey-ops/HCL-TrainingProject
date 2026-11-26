-- Q1: Overall return rate
SELECT
  COUNT(DISTINCT CASE WHEN r.return_id IS NOT NULL THEN o.order_id END) AS returned_orders,
  COUNT(DISTINCT o.order_id) AS total_orders,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN r.return_id IS NOT NULL THEN o.order_id END)
        / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS return_rate_pct
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN returns r ON oi.order_item_id = r.order_item_id
WHERE o.order_status = 'Completed';

-- Q2: Return rate by category
SELECT p.category,
       COUNT(DISTINCT oi.order_item_id) AS sold_items,
       COUNT(DISTINCT r.order_item_id) AS returned_items,
       ROUND(100.0 * COUNT(DISTINCT r.order_item_id) /
             NULLIF(COUNT(DISTINCT oi.order_item_id), 0), 2) AS return_rate_pct
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id
LEFT JOIN returns r ON r.order_item_id = oi.order_item_id
WHERE o.order_status = 'Completed'
GROUP BY p.category
ORDER BY return_rate_pct DESC;

-- Q3: Refund by product
SELECT p.product_name, p.category, ROUND(SUM(r.refund_amount), 2) AS total_refund
FROM returns r
JOIN order_items oi ON oi.order_item_id = r.order_item_id
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_name, p.category
ORDER BY total_refund DESC
LIMIT 10;

-- Q4: Return reasons
SELECT return_reason, COUNT(*) AS return_count,
       ROUND(SUM(refund_amount), 2) AS refund_amount
FROM returns
GROUP BY return_reason
ORDER BY return_count DESC;

-- Q5: Monthly returns
SELECT substr(return_date, 1, 7) AS return_month,
       COUNT(*) AS return_count,
       ROUND(SUM(refund_amount), 2) AS refund_amount
FROM returns
GROUP BY substr(return_date, 1, 7)
ORDER BY return_month;

-- Q6: Return rate by customer type
SELECT c.customer_type,
       COUNT(DISTINCT oi.order_item_id) AS sold_items,
       COUNT(DISTINCT r.order_item_id) AS returned_items,
       ROUND(100.0 * COUNT(DISTINCT r.order_item_id) /
             NULLIF(COUNT(DISTINCT oi.order_item_id), 0), 2) AS return_rate_pct
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
LEFT JOIN returns r ON r.order_item_id = oi.order_item_id
WHERE o.order_status = 'Completed'
GROUP BY c.customer_type
ORDER BY return_rate_pct DESC;

-- Q7: Net sales after refunds by state
SELECT c.state,
       ROUND(SUM(oi.line_total), 2) AS sales_before_refunds,
       ROUND(COALESCE(SUM(r.refund_amount), 0), 2) AS refunds,
       ROUND(SUM(oi.line_total) - COALESCE(SUM(r.refund_amount), 0), 2) AS net_sales
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
LEFT JOIN returns r ON r.order_item_id = oi.order_item_id
WHERE o.order_status = 'Completed'
GROUP BY c.state
ORDER BY net_sales DESC;
