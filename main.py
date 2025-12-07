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
    allow_origins=["*", "https://clinquant-banoffee-a435a5.netlify.app", "https://twinhealthindia.cloud"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Sheet Config
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEET_ID = "1MCJP5sfj0AaodAp6o6hmU7dbiXLZTXo85ZmGEB3UP9Q"
RANGE_NAME = "'Copy of No CGM >2D - Vig, Vin'!A:CB"   # enough columns


# -----------------------------------
# Fetch sheet
# -----------------------------------
def fetch_sheet():
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise Exception("❌ Missing GOOGLE_CREDENTIALS_JSON")

    creds_dict = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)

    service = build("sheets", "v4", credentials=credentials)
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=RANGE_NAME
    ).execute()

    rows = result.get("values", [])
    df = pd.DataFrame(rows)
    return df


# -----------------------------------
# SUMMARY BUILDER (same as V1)
# -----------------------------------
def build_summary(m):
    return f"""
Your Digital Twin shows moderate engagement, with {m['meal_log']} meal logging and {m['gfy']} GFY, {m['steps']} step consistency.
Sleep visibility is {m['sleep']} hours, protein {m['protein']}%, and fiber {m['fiber']}%, which limits your Twin’s ability
to understand recovery patterns and how your meals support blood sugar stability.

Your clinical data shows that your starting HbA1c was {m['start_hba1c']}%, and your latest eA1c is {m['latest_ea1c']}%.
Your weight changed from {m['start_weight']} ➝ {m['latest_weight']} lbs and your BMI improved from {m['start_bmi']} ➝ {m['latest_bmi']}.
Visceral fat changed from {m['start_vfat']} ➝ {m['latest_vfat']}. Your blood pressure changed from {m['start_bp']} ➝ {m['latest_bp']}.

You are currently supported with {m['medicine']}, which provides temporary support while your metabolism continues healing.
Long-term improvement depends on strengthening meal consistency, improving protein and fiber habits, and ensuring full visibility.

To accelerate your progress, continue logging meals, increase protein and fiber daily, maintain strong step consistency,
and track sleep so your Twin can guide you with precision.

Your Digital Twin can only heal what it can see. With consistent engagement, your Twin will guide you toward
deeper metabolic healing and long-term stability.
""".strip()


# -----------------------------------
# Members
# -----------------------------------
@app.get("/members")
def get_members():
    df = fetch_sheet()
    return {"members": df[1].tolist()[1:]}


# -----------------------------------
# Dashboard (V2 mapped → V1 format)
# -----------------------------------
@app.get("/dashboard/{member_id}")
def dashboard(member_id: str):
    df = fetch_sheet()

    matched = df[df[1] == member_id]
    if matched.empty:
        return {"error": f"Member ID {member_id} not found"}

    r = matched.index[0]

    # -----------------------------------
    # COLUMN MAPPING (your confirmed values)
    # -----------------------------------
    metrics = {
        "meal_log": df.iloc[r][11],        # L → 7D MEAL LOG %
        "gfy": df.iloc[r][12],             # M → 7D GFY %
        "steps": df.iloc[r][37],           # AL → STEPS_7D
        "sleep": df.iloc[r][41],           # AP → SLEEP_7D

        "protein": df.iloc[r][54] if len(df.columns) > 54 else "0",   # Taget_protein_1D
        "fiber": df.iloc[r][53] if len(df.columns) > 53 else "0",     # Taget_fibre_1D

        "start_hba1c": df.iloc[r][15],     # P
        "latest_ea1c": df.iloc[r][19],     # T

        "start_weight": df.iloc[r][21],    # V
        "latest_weight": df.iloc[r][22],   # W

        "start_bmi": df.iloc[r][27],       # AB
        "latest_bmi": df.iloc[r][28],      # AC

        "start_vfat": df.iloc[r][59],      # BH
        "latest_vfat": df.iloc[r][60],     # BI

        "start_bp": f"{df.iloc[r][30]} / {df.iloc[r][32]}",   # AE / AG
        "latest_bp": f"{df.iloc[r][31]} / {df.iloc[r][33]}",  # AF / AH

        "medicine": df.iloc[r][52],        # BA → Current Diabetic Medicine
    }

    summary = build_summary(metrics)

    return {"metrics": metrics, "summary": summary}
