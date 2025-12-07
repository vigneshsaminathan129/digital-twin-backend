from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os
import json

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://clinquant-banoffee-a435a5.netlify.app",
        "https://twinhealthindia.cloud",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Sheet Config
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEET_ID = "1MCJP5sfj0AaodAp6o6hmU7dbiXLZTXo85ZmGEB3UP9Q"
RANGE_NAME = "'Copy of No CGM >2D - Vig, Vin'!A:BI"


def fetch_sheet():
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise Exception("❌ Missing GOOGLE_CREDENTIALS_JSON environment variable")

    creds_dict = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)

    service = build("sheets", "v4", credentials=credentials)
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=RANGE_NAME
    ).execute()

    rows = result.get("values", [])
    df = pd.DataFrame(rows)

    df.columns = df.iloc[0]       # First row as header
    df = df[1:]                   # Remove header row

    return df


@app.get("/members")
def get_members():
    df = fetch_sheet()
    return {"members": df["MEMBER_ID"].tolist()}


def build_summary(m):
    return f"""
Your engagement is strong. Meal logging is {m['meal_log']}%, and GFY is {m['gfy']}%.
Steps recorded: {m['steps']}, Sleep visibility: {m['sleep']} hours.

Your starting HbA1c was {m['start_hba1c']}%, now latest A1c is {m['latest_hba1c']}%.

Weight: {m['start_weight']} → {m['last_weight']} lbs  
BMI: {m['start_bmi']} → {m['last_bmi']}  
Visceral fat: {m['start_vfat']} → {m['latest_vfat']}

BP changed from {m['start_bp']} → {m['last_bp']}.

Medicines: {m['medicine']}

To continue improving:
- Log meals daily
- Increase protein & fiber
- Maintain consistent steps & sleep

Your Twin can heal only what it can see.
""".strip()


@app.get("/dashboard/{member_id}")
def dashboard(member_id: str):
    df = fetch_sheet()

    row = df[df["MEMBER_ID"] == member_id]
    if row.empty:
        return {"error": "Member ID not found"}

    r = row.iloc[0]

    metrics = {
        "meal_log": r["7D MEAL LOG %"],
        "gfy": r["7D GFY %"],
        "steps": r["STEPS_7D"],
        "sleep": r["SLEEP_7D"],

        "start_hba1c": r["START HbA1c"],
        "latest_hba1c": r["LAST HbA1c"],

        "start_weight": r["START WEIGHT"],
        "last_weight": r["LAST WEIGHT"],

        "start_bmi": r["START BMI"],
        "last_bmi": r["LAST BMI"],

        "start_vfat": r["start_visceralFat"],
        "latest_vfat": r["latest_visceralFat"],

        "start_bp": f"{r['START 5D-SBP']} / {r['START 5D-DBP']}",
        "last_bp": f"{r['LAST SBP']} / {r['LAST DBP']}",

        "medicine": r["Current Diabetic Medicine"],
        "message_chat": r["MESSAGES TO BE SENT AS CHAT"]
    }

    summary = build_summary(metrics)

    return {"metrics": metrics, "summary": summary}
