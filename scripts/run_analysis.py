from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
DB_DIR = ROOT / "database"
for folder in (RAW, PROCESSED, OUT, DB_DIR):
    folder.mkdir(parents=True, exist_ok=True)

def generate_data(seed=42):
    rng = np.random.default_rng(seed)
    n_customers, n_products, n_orders = 600, 100, 5000
    customers = pd.DataFrame({
        "customer_id": [f"C{i:05d}" for i in range(1, n_customers+1)],
        "customer_name": [f"Customer {i:04d}" for i in range(1, n_customers+1)],
        "city": rng.choice(["Delhi","Mumbai","Bengaluru","Pune","Jaipur","Lucknow","Hyderabad","Chennai"], n_customers),
        "state": rng.choice(["Delhi","Maharashtra","Karnataka","Rajasthan","Uttar Pradesh","Telangana","Tamil Nadu"], n_customers),
        "customer_type": rng.choice(["New","Returning","Loyal"], n_customers, p=[.25,.45,.30])
    })
    categories = ["Electronics","Fashion","Home & Kitchen","Beauty","Sports"]
    products = pd.DataFrame({
        "product_id": [f"P{i:04d}" for i in range(1,n_products+1)],
        "product_name": [f"Product {i:03d}" for i in range(1,n_products+1)],
        "category": rng.choice(categories, n_products),
        "unit_price": np.round(rng.uniform(199, 25000, n_products), 2)
    })
    dates = pd.to_datetime(rng.choice(pd.date_range("2025-01-01","2026-10-31"), n_orders))
    orders = pd.DataFrame({
        "order_id": [f"O{i:06d}" for i in range(1,n_orders+1)],
        "customer_id": rng.choice(customers.customer_id, n_orders),
        "order_date": dates.strftime("%Y-%m-%d"),
        "order_status": rng.choice(["Completed","Cancelled"], n_orders, p=[.94,.06])
    })
    item_rows = []
    for i, row in orders.iterrows():
        for j in range(int(rng.integers(1,4))):
            prod = products.iloc[int(rng.integers(0,n_products))]
            qty = int(rng.integers(1,4))
            discount = float(rng.choice([0,.05,.10,.15,.20]))
            total = round(qty * float(prod.unit_price) * (1-discount), 2)
            item_rows.append((f"OI{i+1:06d}_{j+1}", row.order_id, prod.product_id, qty, float(prod.unit_price), discount, total))
    items = pd.DataFrame(item_rows, columns=["order_item_id","order_id","product_id","quantity","unit_price","discount_pct","line_total"])
    completed_items = items[items.order_id.isin(orders.loc[orders.order_status=="Completed","order_id"])].reset_index(drop=True)
    # Category-dependent return probabilities create meaningful patterns.
    cat_map = products.set_index("product_id").category
    probs = completed_items.product_id.map(cat_map).map({
        "Electronics":.13, "Fashion":.22, "Home & Kitchen":.10, "Beauty":.07, "Sports":.11
    }).to_numpy()
    selected = rng.random(len(completed_items)) < probs
    returned = completed_items.loc[selected].copy()
    reasons = rng.choice(["Damaged","Wrong item","Not as described","Size/fit issue","Late delivery","Changed mind"], len(returned),
                         p=[.18,.13,.20,.22,.12,.15])
    order_date_map = orders.set_index("order_id").order_date
    return_dates = pd.to_datetime(returned.order_id.map(order_date_map)) + pd.to_timedelta(rng.integers(2,22,len(returned)), unit="D")
    returns = pd.DataFrame({
        "return_id":[f"R{i:06d}" for i in range(1,len(returned)+1)],
        "order_item_id":returned.order_item_id.to_numpy(),
        "return_date":return_dates.dt.strftime("%Y-%m-%d"),
        "return_quantity":returned.quantity.to_numpy(),
        "return_reason":reasons,
        "refund_amount":returned.line_total.to_numpy(),
        "return_status":"Approved"
    })
    customers.to_csv(RAW/"customers.csv", index=False)
    products.to_csv(RAW/"products.csv", index=False)
    orders.to_csv(RAW/"orders.csv", index=False)
    items.to_csv(RAW/"order_items.csv", index=False)
    returns.to_csv(RAW/"returns.csv", index=False)
    return customers, products, orders, items, returns

def main():
    customers, products, orders, items, returns = generate_data()
    customers.to_csv(PROCESSED/"customers.csv", index=False)
    products.to_csv(PROCESSED/"products.csv", index=False)
    orders.to_csv(PROCESSED/"orders.csv", index=False)
    items.to_csv(PROCESSED/"order_items.csv", index=False)
    returns.to_csv(PROCESSED/"returns.csv", index=False)

    db = DB_DIR/"returns_analysis.db"
    if db.exists(): db.unlink()
    conn = sqlite3.connect(db)
    conn.executescript((ROOT/"sql"/"schema.sql").read_text(encoding="utf-8"))
    for name, df in [("customers",customers),("products",products),("orders",orders),("order_items",items),("returns",returns)]:
        df.to_sql(name, conn, if_exists="append", index=False)

    # Export each named SQL query result separately.
    sql_text = (ROOT/"sql"/"queries.sql").read_text(encoding="utf-8")
    chunks = [x.strip() for x in sql_text.split(";") if x.strip()]
    for i, query in enumerate(chunks, 1):
        if query.lstrip().startswith("--"):
            query = "\n".join(line for line in query.splitlines() if not line.strip().startswith("--")).strip()
        if query:
            pd.read_sql_query(query, conn).to_csv(OUT/f"q{i}_result.csv", index=False)

    # Main line-level analysis dataset.
    detail = (items.merge(orders, on="order_id")
              .merge(products[["product_id","product_name","category"]], on="product_id")
              .merge(customers[["customer_id","state","customer_type"]], on="customer_id")
              .merge(returns[["order_item_id","return_date","return_reason","refund_amount"]], on="order_item_id", how="left"))
    detail["is_returned"] = detail["return_id"].notna() if "return_id" in detail else detail["refund_amount"].notna()
    detail["refund_amount"] = detail["refund_amount"].fillna(0)
    detail["net_after_refund"] = detail["line_total"] - detail["refund_amount"]
    detail.to_csv(PROCESSED/"order_return_analysis.csv", index=False)

    completed = detail[detail.order_status=="Completed"]
    total_orders = orders.loc[orders.order_status=="Completed","order_id"].nunique()
    returned_orders = completed.loc[completed.is_returned,"order_id"].nunique()
    summary = pd.DataFrame([{
        "total_completed_orders": total_orders,
        "returned_orders": returned_orders,
        "order_return_rate_pct": round(100*returned_orders/total_orders,2) if total_orders else 0,
        "total_order_items": len(completed),
        "returned_items": int(completed.is_returned.sum()),
        "item_return_rate_pct": round(100*completed.is_returned.mean(),2) if len(completed) else 0,
        "total_refunds": round(float(completed.refund_amount.sum()),2),
        "sales_before_refunds": round(float(completed.line_total.sum()),2),
        "net_sales_after_refunds": round(float(completed.net_after_refund.sum()),2)
    }])
    summary.to_csv(OUT/"overall_kpis.csv", index=False)

    # Charts saved as PNG.
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        sns.set_theme(style="whitegrid")
        cat = completed.groupby("category").agg(items=("order_item_id","nunique"),returned=("is_returned","sum")).reset_index()
        cat["return_rate_pct"] = 100*cat['returned']/cat['items']
        plt.figure(figsize=(9,5)); plt.bar(cat["category"], cat["return_rate_pct"])
        plt.xticks(rotation=20,ha="right"); plt.title("Return Rate by Product Category"); plt.tight_layout()
        plt.savefig(OUT/"return_rate_by_category.png",dpi=150); plt.close()
        reason = returns.groupby("return_reason").size().sort_values(ascending=False)
        plt.figure(figsize=(9,5)); reason.plot(kind="bar"); plt.title("Return Reasons"); plt.ylabel("Number of Returns")
        plt.xticks(rotation=25,ha="right"); plt.tight_layout(); plt.savefig(OUT/"return_reasons.png",dpi=150); plt.close()
        monthly = returns.assign(month=returns.return_date.str[:7]).groupby("month").refund_amount.sum()
        plt.figure(figsize=(10,5)); monthly.plot(marker="o"); plt.title("Monthly Refund Amount"); plt.ylabel("Refund Amount (INR)")
        plt.xticks(rotation=45); plt.tight_layout(); plt.savefig(OUT/"monthly_refunds.png",dpi=150); plt.close()
    except ImportError:
        print("Matplotlib/Seaborn unavailable; skipped PNG chart export.")

    conn.close()
    print("Analysis complete.")
    print(summary.to_string(index=False))
    print(f"SQLite database: {db}")
    print(f"CSV outputs: {OUT}")

if __name__ == "__main__":
    main()
