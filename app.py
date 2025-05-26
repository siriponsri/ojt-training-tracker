import streamlit as st
import pandas as pd
import gzip
import pickle
import subprocess
from sheets_connector import (
    get_training_matrix,
    get_form_links,
    get_training_status,
    update_training_status, 
    remove_training_status
)

st.set_page_config(page_title="OJT Tracker", page_icon="📋", layout="centered")

# ---------- CSS: Mobile-first ----------
st.markdown("""
    <style>
    body {
        background-color: #1c1f23;
        color: #f5f7f8;
    }
    .stApp {
        font-family: "Segoe UI", sans-serif;
        padding-left: 5px;
        padding-right: 5px;
    }
    .title {
        font-size: 6vw;
        color: #00a89d;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .summary {
        background-color: #2b2f36;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1.2rem;
        font-size: 4.2vw;
    }
    .card {
        background-color: #2e333a;
        padding: 1rem;
        margin: 0.6rem 0;
        border-left: 5px solid #038599;
        border-radius: 10px;
        width: 100%;
    }
    .doc-title {
        font-size: 4.5vw;
        font-weight: bold;
        color: #f4ce14;
        word-break: break-word;
    }
    .status-done {
        color: #8dffb2;
        font-weight: bold;
        font-size: 4vw;
    }
    .status-pending {
        color: #ffc9c9;
        font-weight: bold;
        font-size: 4vw;
    }
    a {
        color: #5ecbec;
        font-size: 4vw;
        font-weight: bold;
    }
    @media (min-width: 768px) {
        .title { font-size: 28px; }
        .doc-title, .status-done, .status-pending, a { font-size: 16px; }
        .summary { font-size: 16px; }
    }
    </style>
""", unsafe_allow_html=True)

# ---------- Load cached data ----------
def load_fresh_data():
    df_matrix = get_training_matrix()
    df_links = get_form_links()
    df_status = get_training_status()
    return df_matrix, df_links, df_status

@st.cache_data(ttl=120)
def load_cached_data():
    return load_fresh_data()

# ---------- Header ----------
st.markdown('<div class="title">📋 ระบบติดตามการอบรม OJT</div>', unsafe_allow_html=True)

emp_input = st.text_input("กรุณากรอกรหัสพนักงานของคุณ:", max_chars=20).strip().lower()

# ---------- ADMIN DASHBOARD ----------
if emp_input == "admin":
    st.subheader("📊 ADMIN: สรุปผลการอบรมพนักงาน")

    # 🔄 ปุ่มโหลดข้อมูลใหม่
    if st.button("🔄 โหลดข้อมูลจาก Google Sheets ใหม่"):
        try:
            result = subprocess.run(["python", "generate_pickle.py"], check=True, capture_output=True, text=True)
            st.success("✅ โหลดข้อมูลใหม่สำเร็จแล้ว!")
            st.text(result.stdout)
            st.stop()
        except subprocess.CalledProcessError as e:
            st.error("❌ เกิดข้อผิดพลาดในการโหลดข้อมูล")
            st.text(e.stderr)
            st.stop()

    # แสดงสรุป
    df_matrix, df_links, df_status = load_cached_data()

    for _, emp_row in df_matrix.iterrows():
        emp_id = str(emp_row['id']).strip()
        full_name = emp_row['full_name']

        required_docs = [
            col for col in df_matrix.columns
            if col not in ['id', 'full_name'] and str(emp_row[col]).strip().upper() == 'TRUE'
        ]

        done_docs = []
        pending_docs = []

        for doc_no in required_docs:
            doc_info = df_links[df_links['doc_no'].astype(str).str.strip() == str(doc_no).strip()]
            if doc_info.empty:
                continue
            doc_name = doc_info.iloc[0]['doc_name']

            status_row = df_status[
                (df_status['id'].astype(str) == emp_id) &
                (df_status['doc_name'].astype(str).str.strip() == doc_name.strip())
            ]

            done = not status_row.empty and str(status_row.iloc[0]['completed_status']).strip().upper() == 'Y'
            if done:
                done_docs.append(doc_no)
            else:
                pending_docs.append(f"{doc_no}: {doc_name}")

        with st.expander(f"👤 {full_name} ({emp_id})"):
            st.markdown(f"""
            ✅ ทำแล้ว: **{len(done_docs)} / {len(required_docs)}**  
            ❌ เหลืออีก: **{len(pending_docs)} แบบฟอร์ม**
            """)

            if pending_docs:
                st.markdown("**ฟอร์มที่ยังไม่ได้ทำ:**")
                for item in pending_docs:
                    st.markdown(f"- {item}")

    st.stop()

# ---------- USER MODE ----------
if emp_input:
    try:
        df_matrix, df_links, df_status = load_cached_data()

        if emp_input not in df_matrix['id'].astype(str).str.lower().values:
            st.error("❌ ไม่พบรหัสพนักงานนี้ในระบบ กรุณาตรวจสอบอีกครั้ง")
            st.stop()

        emp_row = df_matrix[df_matrix['id'].astype(str).str.lower() == emp_input].iloc[0]
        full_name = emp_row['full_name']
        st.success(f"👋 ยินดีต้อนรับคุณ **{full_name}**")

        required_docs = [
            col for col in df_matrix.columns
            if col not in ['id', 'full_name'] and str(emp_row[col]).strip().upper() == 'TRUE'
        ]

        # 🔍 คำนวณความคืบหน้า
        done_count = 0
        total = len(required_docs)
        done_set = set()

        for doc_no in required_docs:
            doc_info = df_links[df_links['doc_no'].astype(str).str.strip() == str(doc_no).strip()]
            if doc_info.empty:
                continue
            doc_name = doc_info.iloc[0]['doc_name']

            status_row = df_status[
                (df_status['id'].astype(str) == emp_input) &
                (df_status['doc_name'].astype(str).str.strip() == doc_name.strip())
            ]
            if not status_row.empty and str(status_row.iloc[0]['completed_status']).strip().upper() == 'Y':
                done_count += 1
                done_set.add(doc_no)

        # 🔵 แสดง progress bar
        progress = done_count / total if total > 0 else 0
        st.markdown(f"""
        <div class="summary">
            📈 <strong>ความคืบหน้า: {done_count} / {total} ฟอร์ม</strong>
        </div>
        """, unsafe_allow_html=True)
        st.progress(progress)

        st.subheader("📑 รายการ OJT ที่ต้องดำเนินการ")

        for doc_no in required_docs:
            doc_info = df_links[df_links['doc_no'].astype(str).str.strip() == str(doc_no).strip()]
            if doc_info.empty:
                continue

            doc = doc_info.iloc[0]
            doc_name = doc['doc_name']
            link = doc['link']

            col1, col2 = st.columns([0.75, 0.25])
            with col1:
                st.markdown(f"""
                <div class="card">
                    <div class="doc-title">{doc_no}: {doc_name}</div>
                    <a href="{link}" target="_blank">เปิดแบบฟอร์ม</a>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                checked = doc_no in done_set
                if st.checkbox("ส่งแล้ว", value=checked, key=doc_no):
                    if not checked:
                        result = update_training_status(emp_input, doc_name)
                        if result in ["updated", "appended"]:
                            st.success("📌 บันทึกแล้ว")
                            st.cache_data.clear()
                            st.rerun()
                else:
                    if checked:
                        result = remove_training_status(emp_input, doc_name)
                        if result == "deleted":
                            st.warning("📤 ยกเลิกการส่งแล้ว")
                            st.cache_data.clear()
                            st.rerun()

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: `{e}`")