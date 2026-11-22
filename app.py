from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st
from src.db import init_db, seed_if_empty, get_materials, add_material, update_material, delete_material, record_transaction, get_transactions, get_usage_features
from src.ml import classify_inventory, train_model, evaluate_model
from src.genai import generate_inventory_summary

st.set_page_config(page_title="Smart Inventory Firaza", page_icon="📦", layout="wide")
init_db(); seed_if_empty()

st.markdown('''<style>
.block-container{padding-top:1.6rem;padding-bottom:2rem;max-width:1450px}
[data-testid="stMetric"]{background:#f7f9fc;border:1px solid #e7ebf2;padding:14px 16px;border-radius:12px}
[data-testid="stSidebar"]{background:#f7f8fb}
.small-muted{color:#64748b;font-size:0.85rem}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.title("📦 Firaza Inventory")
    st.caption("Smart Warehouse & Inventory Management")
    page=st.radio("NAVIGATION", ["Dashboard","Materials","Stock Transactions","AI Inventory Summary","Model Evaluation"], label_visibility="collapsed")
    st.divider()
    st.caption("Prototype menggunakan synthetic/demo data. Bukan data operasional aktual Firaza.")

materials=[dict(x) for x in get_materials()]
usage=get_usage_features()
rows=[]
for m in materials:
    u=usage.get(m['material_id'], {'usage_7d':0,'usage_30d':0})
    result=classify_inventory(m['current_stock'],m['minimum_stock'],u['usage_7d'],u['usage_30d'],m['lead_time_days'])
    rows.append({**m,**u,**result})
df=pd.DataFrame(rows)

st.title("Smart Inventory Firaza")
st.caption("Pemantauan persediaan material dan rekomendasi prioritas restock berbasis AI")

if page=="Dashboard":
    if df.empty: st.info("Belum ada material. Tambahkan material melalui menu Materials.")
    else:
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total Materials",len(df)); c2.metric("Safe",int((df.status=="Safe").sum())); c3.metric("Need Attention",int((df.status=="Need Attention").sum())); c4.metric("Restock Priority",int((df.status=="Restock Priority").sum()))
        st.subheader("Inventory Overview")
        display=df[["sku","material_name","category","current_stock","minimum_stock","unit","usage_30d","status"]].copy()
        display.columns=["SKU","Material","Category","Current Stock","Minimum Stock","Unit","Usage (30d)","AI Status"]
        st.dataframe(display,use_container_width=True,hide_index=True)
        st.subheader("Materials Requiring Attention")
        urgent=df[df.status!="Safe"].sort_values(["status","current_stock"])
        if urgent.empty: st.success("Semua material berada pada status Safe berdasarkan aturan klasifikasi saat ini.")
        else: st.dataframe(urgent[["sku","material_name","current_stock","minimum_stock","usage_30d","lead_time_days","status"]],use_container_width=True,hide_index=True)

elif page=="Materials":
    st.subheader("Material Master Data")
    st.dataframe(df[["sku","material_name","category","unit","current_stock","minimum_stock","lead_time_days","supplier","status"]] if not df.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    with st.expander("＋ Add Material"):
        with st.form("add_material"):
            a,b=st.columns(2); sku=a.text_input("SKU *"); name=b.text_input("Material name *")
            category=a.selectbox("Category",["Packaging","Bahan Baku","Pelengkap","Lainnya"]); unit=b.selectbox("Unit",["pcs","roll","pack","sheet","meter","kg"])
            stock=a.number_input("Initial stock",min_value=0.0,value=0.0); minimum=b.number_input("Minimum stock",min_value=0.0,value=0.0)
            lead=a.number_input("Lead time (days)",min_value=1,value=3); supplier=b.text_input("Supplier")
            if st.form_submit_button("Save Material",type="primary"):
                try:
                    if not sku.strip() or not name.strip(): raise ValueError("SKU dan nama material wajib diisi.")
                    add_material(sku.strip(),name.strip(),category,unit,stock,minimum,int(lead),supplier.strip()); st.success("Material ditambahkan."); st.rerun()
                except Exception as e: st.error(str(e))
    with st.expander("✎ Edit / Delete Material"):
        if materials:
            choice=st.selectbox("Select material",materials,format_func=lambda x:f"{x['sku']} — {x['material_name']}")
            with st.form("edit_material"):
                a,b=st.columns(2); en=a.text_input("Material name",choice['material_name']); ec=b.selectbox("Category",["Packaging","Bahan Baku","Pelengkap","Lainnya"],index=["Packaging","Bahan Baku","Pelengkap","Lainnya"].index(choice['category']) if choice['category'] in ["Packaging","Bahan Baku","Pelengkap","Lainnya"] else 0)
                eu=a.selectbox("Unit",["pcs","roll","pack","sheet","meter","kg"],index=["pcs","roll","pack","sheet","meter","kg"].index(choice['unit']) if choice['unit'] in ["pcs","roll","pack","sheet","meter","kg"] else 0); emin=b.number_input("Minimum stock",min_value=0.0,value=float(choice['minimum_stock'])); el=a.number_input("Lead time (days)",min_value=1,value=int(choice['lead_time_days'])); es=b.text_input("Supplier",choice['supplier'] or "")
                if st.form_submit_button("Update Material",type="primary"):
                    update_material(choice['material_id'],en,ec,eu,emin,int(el),es); st.success("Material diperbarui."); st.rerun()
            if st.button("Delete Selected Material",type="secondary"):
                try: delete_material(choice['material_id']); st.success("Material dihapus."); st.rerun()
                except Exception as e: st.error(str(e))
        else: st.info("Belum ada material.")

elif page=="Stock Transactions":
    st.subheader("Record Stock Movement")
    if materials:
        options={f"{m['sku']} — {m['material_name']}":m['material_id'] for m in materials}
        with st.form("transaction_form"):
            selected=st.selectbox("Material",list(options)); tx_type=st.selectbox("Transaction type",["STOCK_IN","STOCK_OUT","STOCK_OPNAME"])
            qty=st.number_input("Quantity",min_value=0.01,value=1.0); note=st.text_input("Note / reference")
            submitted=st.form_submit_button("Record Transaction",type="primary")
            if submitted:
                try: record_transaction(options[selected],tx_type,qty,note); st.success("Transaksi tersimpan dan stok diperbarui."); st.rerun()
                except Exception as e: st.error(str(e))
    else: st.info("Tambahkan material terlebih dahulu.")
    st.subheader("Transaction History")
    tx=[dict(x) for x in get_transactions()]
    if tx:
        st.dataframe(pd.DataFrame(tx), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada transaksi.")

elif page=="AI Inventory Summary":
    st.subheader("AI-Generated Inventory Summary")
    st.write("Ringkasan dibuat dari data stok, histori stock-out, minimum stock, lead time, dan hasil klasifikasi.")
    if st.button("Generate Inventory Summary",type="primary",disabled=df.empty):
        with st.spinner("Menghubungi Gemini (maksimal 2 percobaan)..."):
            summary,source=generate_inventory_summary(rows)
        st.session_state["summary"]=summary; st.session_state["summary_source"]=source
    if "summary" in st.session_state:
        st.caption("Sumber: Gemini API" if st.session_state["summary_source"]=="gemini" else "Sumber: fallback berbasis aturan")
        st.markdown(st.session_state["summary"])
    st.caption("Rekomendasi merupakan decision support. Verifikasi stok fisik, pesanan mendatang, dan pemasok sebelum pembelian.")

elif page=="Model Evaluation":
    st.subheader("Machine Learning Model Evaluation")
    st.warning("Dataset dan label bersifat sintetis. Evaluasi ini mengukur kemampuan model meniru aturan label simulasi, bukan performa pada data historis aktual Firaza.")
    if st.button("Train & Evaluate Model",type="primary"):
        with st.spinner("Training dan evaluasi model..."): st.session_state["evaluation"]=evaluate_model()
    result=st.session_state.get("evaluation")
    if result:
        a,b,c=st.columns(3); a.metric("Accuracy",f"{result['accuracy']:.1%}"); b.metric("Macro F1",f"{result['macro_f1']:.1%}"); c.metric("Test Samples",result['test_samples'])
        st.dataframe(pd.DataFrame(result['report']).T,use_container_width=True)
        st.write("**Confusion matrix**"); st.dataframe(pd.DataFrame(result['confusion_matrix'],index=result['labels'],columns=result['labels']),use_container_width=True)
        st.caption(f"Model tersimpan: {result['model_path']}")
    else: st.info("Klik Train & Evaluate Model untuk menjalankan evaluasi dan menyimpan model.")

st.divider(); st.caption("Smart Inventory Firaza · Dicoding Capstone DB15-I033 · Synthetic demonstration data")
