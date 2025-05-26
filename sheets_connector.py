import json
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from datetime import datetime

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gsheet_client():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/14a9Yct53RD5IQB6bQC10b-ngYLQiqhoFwD6iyvGZZdg/edit?gid=2038251767#gid=2038251767"

@st.cache_data(ttl=300)
def get_training_matrix():
    sheet = get_gsheet_client().open_by_url(SPREADSHEET_URL)
    data = sheet.worksheet("training_matrix").get_all_records()
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_form_links():
    sheet = get_gsheet_client().open_by_url(SPREADSHEET_URL)
    data = sheet.worksheet("form_links").get_all_records()
    return pd.DataFrame(data)

@st.cache_data(ttl=60)  # สั้นกว่าหน่อยเพราะข้อมูลนี้อัปเดตบ่อย
def get_training_status():
    sheet = get_gsheet_client().open_by_url(SPREADSHEET_URL)
    ws = sheet.worksheet("training_status")
    records = ws.get_all_records()

    if not records:
        return pd.DataFrame(columns=["id", "doc_name", "completed_status", "timestamp"])

    df = pd.DataFrame(records)
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def update_training_status(emp_id, doc_name):
    try:
        sheet = get_gsheet_client().open_by_url(SPREADSHEET_URL)
        ws = sheet.worksheet("training_status")
        records = ws.get_all_records()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for idx, row in enumerate(records):
            if str(row.get("id")).strip() == str(emp_id) and str(row.get("doc_name")).strip() == str(doc_name):
                ws.update_cell(idx + 2, 3, "Y")
                ws.update_cell(idx + 2, 4, timestamp)  # timestamp ที่คอลัมน์ 4
                return "updated"

        ws.append_row([str(emp_id), str(doc_name), "Y", timestamp])
        return "appended"

    except Exception as e:
        return f"error: {e}"

def remove_training_status(emp_id, doc_name):
    try:
        sheet = get_gsheet_client().open_by_url(SPREADSHEET_URL)
        ws = sheet.worksheet("training_status")
        records = ws.get_all_records()

        for idx, row in enumerate(records):
            if str(row.get("id")).strip() == str(emp_id) and str(row.get("doc_name")).strip() == str(doc_name):
                ws.delete_rows(idx + 2)  # +2 เพราะ header บรรทัดแรก, index เริ่มที่ 0
                return "deleted"
        return "not_found"
    except Exception as e:
        return f"error: {e}"
