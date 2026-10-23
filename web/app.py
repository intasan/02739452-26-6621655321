import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="ราคาสินค้าเกษตร", page_icon="🌾", layout="wide")
st.title("ราคาสินค้าเกษตรจากหลายแหล่ง")
st.caption("ข้อมูลจริงจาก PostgreSQL เท่านั้น — ไม่ใช้ข้อมูลจำลอง")
if os.getenv("VALIDATION_ENVIRONMENT"):
    st.info(os.environ["VALIDATION_ENVIRONMENT"])

@st.cache_resource
def database_engine():
    return create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

try:
    with database_engine().connect() as conn:
        df = pd.read_sql(text("""SELECT source, product_name, province, unit, price_min,
            price_max, (price_min + price_max)/2 AS average_price, observed_at,
            measurement_type FROM agricultural_prices ORDER BY observed_at DESC"""), conn)
except Exception:
    st.error("เชื่อมต่อ PostgreSQL ไม่ได้ กรุณาตรวจสอบ Docker และ DATABASE_URL")
    st.stop()

if df.empty:
    st.warning("ยังไม่มีข้อมูลจริง กรุณารัน DAG และตรวจสอบ Logs")
    st.stop()

for field in ("price_min", "price_max", "average_price"):
    df[field] = pd.to_numeric(df[field], errors="coerce")
df["observed_at"] = pd.to_datetime(df["observed_at"], errors="coerce").dt.date
df = df.dropna(subset=["observed_at", "average_price"])
if df.empty:
    st.warning("ไม่พบข้อมูลราคาที่ถูกต้อง")
    st.stop()

st.caption(f"ข้อมูลทั้งหมดในฐานข้อมูล: {len(df):,} รายการ | แหล่งข้อมูล: {', '.join(sorted(df.source.unique()))}")
with st.expander("สถานะ Pipeline ล่าสุด", expanded=False):
    try:
        with database_engine().connect() as status_conn:
            runs = pd.read_sql(text("""SELECT run_id, started_at, status, loaded_rows,
                rejected_rows, details FROM pipeline_runs ORDER BY started_at DESC LIMIT 5"""), status_conn)
        if runs.empty:
            st.caption("ยังไม่มีบันทึก Pipeline")
        else:
            latest = runs.iloc[0]
            st.caption(f"ผลล่าสุด: {latest['status']} | โหลด {int(latest.loaded_rows):,} | ปฏิเสธ {int(latest.rejected_rows):,}")
            details = latest['details'] if isinstance(latest['details'], dict) else {}
            st.caption(f"โหมดข้อมูล: {details.get('input_mode','live')} (verified_snapshot_replay คือการทดสอบซ้ำจากข้อมูลจริงที่บันทึกไว้)")
            for source, state in details.get('source_status', {}).items():
                st.caption(f"{source}: {'พร้อมใช้งาน' if state.get('ok') else 'ดึงข้อมูลไม่สำเร็จ'} | {state.get('extracted_rows',0)} รายการ")
            st.dataframe(runs.drop(columns=['details']), use_container_width=True, hide_index=True)
    except Exception:
        st.caption("ยังอ่านสถานะ Pipeline ไม่ได้; ตารางราคายังคงใช้งานได้")

st.subheader("ตัวกรองข้อมูล")
left, right = st.columns(2)
with left:
    products = st.multiselect("สินค้า", sorted(df.product_name.dropna().unique()),
                              default=sorted(df.product_name.dropna().unique()))
with right:
    sources = st.multiselect("แหล่งข้อมูล", sorted(df.source.dropna().unique()),
                             default=sorted(df.source.dropna().unique()))
dates = st.date_input("ช่วงวันที่", value=(df.observed_at.min(), df.observed_at.max()))
if not isinstance(dates, (tuple, list)) or len(dates) != 2:
    st.info("กรุณาเลือกวันเริ่มต้นและวันสิ้นสุด")
    st.stop()
filtered = df[df.product_name.isin(products) & df.source.isin(sources)]
filtered = filtered[(filtered.observed_at >= dates[0]) & (filtered.observed_at <= dates[1])]
if filtered.empty:
    st.info("ไม่พบข้อมูลตามตัวกรอง")
    st.stop()

st.subheader("แนวโน้มราคาตามวันที่")
st.caption("เลือกสินค้าและประเภทข้อมูลหนึ่งกลุ่ม เพื่อไม่ให้เปรียบเทียบราคาคนละหน่วย")
groups = sorted(set(zip(filtered.product_name, filtered.unit, filtered.measurement_type)))
selection = st.selectbox("สินค้าสำหรับกราฟแนวโน้มและ KPI", groups,
                         format_func=lambda x: f"{x[0]} | {x[1]} | {x[2]}")
trend_df = filtered[(filtered.product_name == selection[0]) &
                    (filtered.unit == selection[1]) &
                    (filtered.measurement_type == selection[2])].copy()
a, b, c, d = st.columns(4)
a.metric("จำนวนรายการ (สินค้าที่เลือก)", f"{len(trend_df):,}")
b.metric("ราคาเฉลี่ย", f"{trend_df.average_price.mean():,.2f}")
c.metric("ราคาสูงสุด", f"{trend_df.price_max.max():,.2f}")
d.metric("ราคาต่ำสุด", f"{trend_df.price_min.min():,.2f}")
st.caption(f"หน่วย: {selection[1]} | ประเภท: {selection[2]}")
trend = trend_df.groupby(["observed_at", "source"], as_index=False).average_price.mean()
trend["date_label"] = trend.observed_at.astype(str)
fig = px.line(trend, x="date_label", y="average_price", color="source", markers=True,
              labels={"date_label": "วันที่", "average_price": f"ราคาเฉลี่ย ({selection[1]})", "source": "แหล่งข้อมูล"})
fig.update_xaxes(type="category", tickangle=-35)
fig.update_layout(margin=dict(l=10, r=10, t=15, b=10), hovermode="x unified", height=350)
st.plotly_chart(fig, use_container_width=True)
if trend.observed_at.nunique() < 2:
    st.info("สินค้าที่เลือกมีข้อมูลเพียงวันเดียว จึงยังแสดงแนวโน้มการเปลี่ยนแปลงราคาไม่ได้")

st.subheader("เปรียบเทียบราคาเฉลี่ยระหว่างสินค้า")
st.caption("เปรียบเทียบเฉพาะข้อมูลที่มีหน่วยและประเภทการวัดเดียวกัน เพื่อไม่ให้ตัวเลขคลาดเคลื่อน")
comparison_groups = sorted(set(zip(filtered.unit, filtered.measurement_type)))
unit_group = st.selectbox("หน่วยและประเภทข้อมูลสำหรับเปรียบเทียบ", comparison_groups,
                          format_func=lambda x: f"{x[0]} | {x[1]}")
comparison = filtered[(filtered.unit == unit_group[0]) &
                      (filtered.measurement_type == unit_group[1])]
comparison_date = st.selectbox("วันที่สำหรับเปรียบเทียบราคา", sorted(comparison.observed_at.unique(), reverse=True))
comparison = comparison[comparison.observed_at == comparison_date]
bar_data = comparison.groupby(["product_name", "source"], as_index=False).average_price.mean()
top_names = bar_data.groupby('product_name').average_price.mean().nlargest(20).index
bar_data = bar_data[bar_data.product_name.isin(top_names)]
bar = px.bar(bar_data, x="average_price", y="product_name", color="source", barmode="group", orientation="h",
             labels={"average_price": f"ราคาเฉลี่ย ({unit_group[0]})", "product_name": "สินค้า", "source": "แหล่งข้อมูล"},
             text_auto=".2f")
bar.update_layout(height=max(320, 36 * len(bar_data) + 100),
                  margin=dict(l=10, r=10, t=15, b=10), yaxis={"categoryorder": "total ascending"})
st.caption(f"วันที่ {comparison_date} | หน่วย {unit_group[0]} | ประเภท {unit_group[1]} | ไม่รวมราคาคนละวันหรือคนละประเภท")
st.plotly_chart(bar, use_container_width=True)
if bar_data.source.nunique() < 2:
    st.info("วันที่และประเภทนี้มีข้อมูลจากแหล่งเดียว จึงยังไม่ใช่การเปรียบเทียบข้ามแหล่ง")

st.subheader("รายการราคาตามตัวกรอง")
st.caption(f"แสดง {len(filtered):,} รายการจากฐานข้อมูล")
st.dataframe(filtered.sort_values("observed_at", ascending=False),
             use_container_width=True, hide_index=True)
