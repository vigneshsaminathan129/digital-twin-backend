from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os
import json

app = FastAPI()

# -------------------------------
# CORS
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all (or replace with your frontend URL)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# GOOGLE SHEET CONFIG
# -------------------------------
SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEET_ID = "1MCJP5sfj0AaodAp6o6hmU7dbiXLZTXo85ZmGEB3UP9Q"
RANGE_NAME = "Sheet1!A:BB"   # Covers all columns shown in screenshots


# -------------------------------
# FETCH THE GOOGLE SHEET
# -------------------------------
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

    # Convert to DataFrame
    df = pd.DataFrame(rows)
    df.columns = df.iloc[0]       # Set first row as header
    df = df[1:]                   # Remove header row from data
    df.reset_index(drop=True, inplace=True)

    return df


# -------------------------------
# GET ALL MEMBER IDs
# -------------------------------
@app.get("/members")
def get_members():
    df = fetch_sheet()
    return {"members": df["MEMBER_ID"].tolist()}


# -------------------------------
# ➤ MAIN DASHBOARD ENDPOINT
# -------------------------------
@app.get("/dashboard/{member_id}")
def dashboard(member_id: str):

    df = fetch_sheet()

    row = df[df["MEMBER_ID"] == member_id]

    if row.empty:
        return {"error": f"❌ Member ID {member_id} not found."}

    r = row.iloc[0]  # extract the row

    # Build Clean JSON Output
    output = {

        "basic": {
            "member_id": r["MEMBER_ID"],
            "gender": r["Gender"],
            "coach_name": r["coachName"],
            "doctor_name": r["doctorName"],
            "previous_rounds": r["Previous Rounds"],
            "days": r["DAYS"],
        },

        "chat": {
            "last_chat_sent_date": r["LAST CHAT SENT DATE"],
            "days_no_chat": r["# DAYS NO CHAT"],
        },

        "meal_logs": {
            "meal_log_7d": r["7D MEAL LOG %"],
            "gfy_7d": r["7D GFY %"],
            "last_meal_log_date": r["LAST MEAL LOG DATE"],
            "days_no_meal_log": r["# DAYS NO MEAL LOG"],
        },

        "blood_sugar": {
            "start_hba1c": r["START HbA1c"],
            "last_hba1c": r["LAST HbA1c"],
            "last_1dg": r["LAST 1DG"],
            "last_5dg": r["LAST 5DG"],
            "last_ea1c": r["LAST eA1c"],
            "days_no_cgm": r["# DAYS NO CGM"],
        },

        "weight": {
            "start_weight": r["START WEIGHT"],
            "lowest_weight": r["LOWEST WEIGHT"],
            "last_weight": r["LAST WEIGHT"],
            "weight_loss_lbs": r["WEIGHT LOSS (LBS)"],
            "last_weight_recorded_date": r["LAST WEIGHT RECORDED DATE"],
            "days_no_weight": r["# DAYS NO WEIGHT"],
        },

        "blood_pressure": {
            "last_sbp": r["LAST SBP"],
            "last_dbp": r["LAST DBP"],
            "last_bp_recorded_date": r["LAST BP RECORDED DATE"],
            "days_no_bp": r["# DAYS NO BP"],
        },

        "steps": {
            "steps_1d": r["STEPS_1D"],
            "steps_7d": r["STEPS_7D"],
            "last_steps_recorded_date": r["LAST STEPS RECORDED DATE"],
            "days_no_steps": r["# DAYS NO STEPS"],
        },

        "sleep": {
            "sleep_1d": r["SLEEP_1D"],
            "sleep_7d": r["SLEEP_7D"],
            "last_sleep_recorded_date": r["LAST SLEEP RECORDED DATE"],
            "days_no_sleep": r["# DAYS NO SLEEP"],
        },

        "medicine": {
            "start_diabetic_medicine": r["Start Diabetic Medicine"],
            "current_diabetic_medicine": r["Current Diabetic Medicine"],
        },

        "message_to_send": r["MESSAGES TO BE SENT AS CHAT"],
    }

    return output
