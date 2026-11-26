from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "data" / "processed"

st.set_page_config(page_title="Returns & Refund Analysis", page_icon="📦", layout="wide")
st.title("Product Returns & Refund Analysis")
st.caption("Synthetic e-commerce dataset | Academic analytics project")

kpi_path = OUT / "overall_kpis.csv"
detail_path = DATA / "order_return_analysis.csv"
if not kpi_path.exists() or not detail_path.exists():
    st.error("Analysis files not found. Run: python scripts/run_analysis.py")
    st.stop()

kpi = pd.read_csv(kpi_path).iloc[0]
df = pd.read_csv(detail_path)
df = df[df["order_status"] == "Completed"].copy()

st.sidebar.header("Filters")
cats = sorted(df.category.dropna().unique())
states = sorted(df.state.dropna().unique())
chosen_cats = st.sidebar.multiselect("Product category", cats, default=cats)
chosen_states = st.sidebar.multiselect("Customer state", states, default=states)
df = df[df.category.isin(chosen_cats) & df.state.isin(chosen_states)]
if df.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Completed orders", f"{df.order_id.nunique():,}")
c2.metric("Returned items", f"{int(df.is_returned.sum()):,}")
c3.metric("Refund amount", f"₹{df.refund_amount.sum():,.0f}")
c4.metric("Net sales after refunds", f"₹{df.net_after_refund.sum():,.0f}")

left,right = st.columns(2)
with left:
    cat = df.groupby("category").agg(items=("order_item_id","nunique"),returned=("is_returned","sum")).reset_index()
    cat["return_rate_pct"] = 100*cat['returned']/cat['items']
    st.plotly_chart(px.bar(cat,x="category",y="return_rate_pct",color="category",title="Return Rate by Category"),use_container_width=True)
with right:
    reason = df[df.is_returned].groupby("return_reason").size().reset_index(name="returns").sort_values("returns",ascending=False)
    st.plotly_chart(px.bar(reason,x="return_reason",y="returns",color="return_reason",title="Return Reasons"),use_container_width=True)

monthly = df[df.is_returned].assign(month=lambda x:x.return_date.astype(str).str[:7]).groupby("month",as_index=False).refund_amount.sum()
st.plotly_chart(px.line(monthly,x="month",y="refund_amount",markers=True,title="Monthly Refund Amount"),use_container_width=True)

prod = df.groupby(["product_name","category"],as_index=False).agg(refunds=("refund_amount","sum"),items=("order_item_id","nunique"),returned=("is_returned","sum"))
prod = prod.sort_values("refunds",ascending=False).head(10)
st.plotly_chart(px.bar(prod,x="product_name",y="refunds",color="category",title="Top 10 Products by Refund Amount"),use_container_width=True)

st.subheader("Detailed Order Item Records")
st.dataframe(df.sort_values("refund_amount",ascending=False),use_container_width=True,hide_index=True)
st.download_button("Download filtered data",df.to_csv(index=False).encode("utf-8"),"returns_refunds_filtered.csv","text/csv")
st.caption("All records are synthetic. Return rates are calculated at item level in category analysis.")
