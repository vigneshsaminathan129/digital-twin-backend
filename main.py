from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os
import json

app = FastAPI()

# -------------------------
# CORS (allow frontend)
# -------------------------
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

# -------------------------
# Google Sheet Configuration
# -------------------------
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

SHEET_ID = "1feRkTQ-GhXGtmNwknJZ4QLx3zOmZV_t1"

# Your tab name (IMPORTANT: must match exactly)
RANGE_NAME = "'Copy of No CGM >2D - Vig, Vin'!A:Z"


# -------------------------
# Function: Fetch Google Sheet
# -------------------------
def fetch_sheet():

    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise Exception("❌ Missing GOOGLE_CREDENTIALS_JSON environment variable")

    # Load JSON → dict → credentials
    creds_dict = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)

    # Build Sheets API client
    service = build("sheets", "v4", credentials=credentials)

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range=RANGE_NAME)
        .execute()
    )

    rows = result.get("values", [])
    df = pd.DataFrame(rows)
    return df


# -------------------------
# Endpoint: GET Member IDs
# -------------------------
@app.get("/members")
def get_members():
    df = fetch_sheet()

    if df.empty or len(df.columns) < 2:
        return {"members": []}

    member_ids = df[1].tolist()[1:]   # Column B = Member IDs
    return {"members": member_ids}


# -------------------------
# Build Summary Paragraph
# -------------------------
def build_summary(m):

    return f"""
Your Digital Twin shows moderate engagement, with {m['meal_log']} meal logging and {m['gfy']} GFY. 
Steps: {m['steps']}, Sleep: {m['sleep']} hours. Protein: {m['protein']}%, Fiber: {m['fiber']}%. 

Clinical data:
• Starting HbA1c: {m['start_hba1c']}% → Latest eA1c: {m['latest_ea1c']}%
• Weight: {m['start_weight']} → {m['latest_weight']} lbs
• BMI: {m['start_bmi']} → {m['latest_bmi']}
• Visceral Fat: {m['start_vfat']} → {m['latest_vfat']}
• Blood Pressure: {m['start_bp']} → {m['latest_bp']}

Current medication: {m['medicine']}

Your Twin can heal only what it can see. Improve logging, protein, fiber, steps, and sleep 
to drive deeper metabolic healing and long-term stability.
""".strip()


# -------------------------
# Endpoint: Dashboard Data
# -------------------------
@app.get("/dashboard/{member_id}")
def dashboard(member_id: str):
    df = fetch_sheet()

    # Find member row
    matched_rows = df[df[1] == member_id]

    if matched_rows.empty:
        return {"error": f"Member ID '{member_id}' not found."}

    r = matched_rows.index[0]

    metrics = {
        "meal_log": df.iloc[r][11],
        "gfy": df.iloc[r][12],
        "steps": df.iloc[r][37],
        "sleep": df.iloc[r][41],

        "protein": df.iloc[r][54] if len(df.columns) > 54 else "0",
        "fiber": df.iloc[r][53] if len(df.columns) > 53 else "0",

        "start_hba1c": df.iloc[r][15],
        "latest_ea1c": df.iloc[r][19],

        "start_weight": df.iloc[r][21],
        "latest_weight": df.iloc[r][23],

        "start_bmi": df.iloc[r][27],
        "latest_bmi": df.iloc[r][28],

        "start_vfat": df.iloc[r][59],
        "latest_vfat": df.iloc[r][60],

        "start_bp": f"{df.iloc[r][30]} / {df.iloc[r][32]}",
        "latest_bp": f"{df.iloc[r][31]} / {df.iloc[r][33]}",

        "medicine": df.iloc[r][52] if len(df.columns) > 52 else "",
    }

    summary = build_summary(metrics)

    return {"metrics": metrics, "summary": summary}
