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
RANGE_NAME = "'Copy of No CGM >2D - Vig, Vin'!A:BZ"


# ----------------------------
# Fetch Google Sheet
# ----------------------------
def fetch_sheet():
    credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise Exception("❌ Missing GOOGLE_CREDENTIALS_JSON environment variable")

    creds_dict = json.loads(credentials_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)

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


# ----------------------------
# MEMBERS LIST
# ----------------------------
@app.get("/members")
def get_members():
    df = fetch_sheet()

    # Member ID → Column B = index 1
    return {"members": df[1].tolist()[1:]}


# ----------------------------
# DASHBOARD ENDPOINT
# ----------------------------
@app.get("/dashboard/{member_id}")
def dashboard(member_id: str):
    df = fetch_sheet()

    # Find row matching MEMBER_ID
    matched_rows = df[df[1] == member_id]
    if matched_rows.empty:
        return {"error": f"Member ID {member_id} not found"}

    r = matched_rows.index[0]

    # Extract metrics using your confirmed column indexes
    metrics = {
        "member_id": df.iloc[r][1],
        "patient_name": df.iloc[r][2],
        "gender": df.iloc[r][3],
        "coach_name": df.iloc[r][4],
        "doctor_name": df.iloc[r][5],

        "days": df.iloc[r][7],
        "meal_log_7d": df.iloc[r][11],
        "gfy_7d": df.iloc[r][12],

        "last_meal_log_date": df.iloc[r][13],
        "days_no_meal": df.iloc[r][14],

        "start_hba1c": df.iloc[r][15],
        "latest_hba1c": df.iloc[r][16],
        "last_1dg": df.iloc[r][17],
        "last_5dg": df.iloc[r][18],
        "last_ea1c": df.iloc[r][19],

        "start_weight": df.iloc[r][21],
        "last_weight": df.iloc[r][22],
        "weight_loss": df.iloc[r][24],
        "last_weight_date": df.iloc[r][25],

        "start_bmi": df.iloc[r][27],
        "last_bmi": df.iloc[r][28],

        "start_sbp": df.iloc[r][30],
        "last_sbp": df.iloc[r][31],
        "start_dbp": df.iloc[r][32],
        "last_dbp": df.iloc[r][33],
        "last_bp_date": df.iloc[r][34],

        "steps_1d": df.iloc[r][36],
        "steps_7d": df.iloc[r][37],
        "last_steps_date": df.iloc[r][38],

        "sleep_1d": df.iloc[r][40],
        "sleep_7d": df.iloc[r][41],
        "last_sleep_date": df.iloc[r][42],

        "start_diabetic_med": df.iloc[r][51],
        "current_diabetic_med": df.iloc[r][52],

        "start_visceral_fat": df.iloc[r][59],
        "latest_visceral_fat": df.iloc[r][60],

        "message_chat": df.iloc[r][61],   # Long paragraph
    }

    return {"metrics": metrics}
