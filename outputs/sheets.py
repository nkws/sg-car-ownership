"""Google Sheets export for SG Car Ownership pipeline.

Pushes summary data to a Google Spreadsheet with tabs for:
1. Overview (FSI score, alerts)
2. COE Trends
3. Income Segmentation
4. Town Profiles
5. Hire Purchase
6. Signal Log

Requires a Google Cloud service account credentials JSON file.
Set the path via GOOGLE_CREDS_FILE env var or place credentials.json in project root.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import pandas as pd
from datetime import datetime
from database import get_conn, init_db
from config import GOOGLE_SHEETS, SIGNAL_FILE


def get_sheets_client():
    """Authenticate and return gspread client."""
    import gspread
    from google.oauth2.service_account import Credentials

    creds_file = GOOGLE_SHEETS["credentials_file"]
    if not Path(creds_file).exists():
        print(f"Credentials file not found: {creds_file}")
        print("Set GOOGLE_CREDS_FILE env var or place credentials.json in project root.")
        print("\nTo set up Google Sheets integration:")
        print("1. Go to console.cloud.google.com")
        print("2. Create a service account")
        print("3. Enable Google Sheets API")
        print("4. Download JSON key and save as credentials.json")
        print("5. Share your target spreadsheet with the service account email")
        return None, None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    client = gspread.authorize(creds)

    # Open or create spreadsheet
    sheet_name = GOOGLE_SHEETS["spreadsheet_name"]
    try:
        spreadsheet = client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(sheet_name)
        print(f"Created new spreadsheet: {sheet_name}")

    return client, spreadsheet


def _ensure_worksheet(spreadsheet, title, rows=1000, cols=20):
    """Get or create a worksheet by title."""
    try:
        return spreadsheet.worksheet(title)
    except Exception:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


def _df_to_sheet(worksheet, df):
    """Write a DataFrame to a worksheet (clears existing content)."""
    worksheet.clear()
    if df.empty:
        return
    header = df.columns.tolist()
    values = [header] + df.values.tolist()
    worksheet.update(range_name="A1", values=values)


def export_to_sheets():
    """Export all summary data to Google Sheets."""
    client, spreadsheet = get_sheets_client()
    if not spreadsheet:
        return False

    init_db()
    print("Exporting to Google Sheets...")

    # 1. Overview tab
    ws = _ensure_worksheet(spreadsheet, "Overview")
    signal = {}
    if SIGNAL_FILE.exists():
        with open(SIGNAL_FILE) as f:
            signal = json.load(f)

    overview_data = [
        ["SG Car Ownership — Financial Stress Dashboard"],
        ["Last Updated", signal.get("timestamp", "N/A")[:19]],
        [],
        ["FSI Score", signal.get("fsi_score", "N/A")],
        ["FSI Trend", signal.get("fsi_trend", "N/A")],
        [],
        ["Components"],
    ]
    for comp, val in signal.get("fsi_components", {}).items():
        overview_data.append([comp, val])
    overview_data.append([])
    overview_data.append(["Alerts"])
    for alert in signal.get("alerts", []):
        overview_data.append([alert])
    overview_data.append([])
    overview_data.append(["Car Costs"])
    for cat, data in signal.get("car_costs", {}).items():
        overview_data.append([cat, f"${data['monthly_total']:,.0f}/mo",
                              f"Vehicle: ${data['vehicle_cost']:,.0f}"])

    ws.clear()
    ws.update(range_name="A1", values=overview_data)

    # 2. COE Trends
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT month, vehicle_class, AVG(premium) as avg_premium,
                   AVG(quota) as avg_quota, AVG(bids_received) as avg_bids
            FROM coe_results
            WHERE month >= '2020-01'
            GROUP BY month, vehicle_class
            ORDER BY month
        """).fetchall()
    coe_df = pd.DataFrame([dict(r) for r in rows])
    ws = _ensure_worksheet(spreadsheet, "COE Trends")
    _df_to_sheet(ws, coe_df)
    print(f"  COE Trends: {len(coe_df)} rows")

    # 3. Income Segmentation
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM household_income").fetchall()
    income_df = pd.DataFrame([dict(r) for r in rows])
    ws = _ensure_worksheet(spreadsheet, "Income Segmentation")
    _df_to_sheet(ws, income_df)
    print(f"  Income: {len(income_df)} rows")

    # 4. Town Profiles
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM town_profile ORDER BY fsi_score DESC").fetchall()
    town_df = pd.DataFrame([dict(r) for r in rows])
    ws = _ensure_worksheet(spreadsheet, "Town Profiles")
    _df_to_sheet(ws, town_df)
    print(f"  Towns: {len(town_df)} rows")

    # 5. Hire Purchase
    with get_conn() as conn:
        try:
            rows = conn.execute("SELECT * FROM mas_hire_purchase ORDER BY year, quarter").fetchall()
            hp_df = pd.DataFrame([dict(r) for r in rows])
        except Exception:
            hp_df = pd.DataFrame()
    ws = _ensure_worksheet(spreadsheet, "Hire Purchase")
    _df_to_sheet(ws, hp_df)
    print(f"  HP: {len(hp_df)} rows")

    # 6. Signal Log
    ws = _ensure_worksheet(spreadsheet, "Signal Log")
    signal_row = [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        signal.get("fsi_score", ""),
        signal.get("fsi_trend", ""),
        json.dumps(signal.get("fsi_components", {})),
        " | ".join(signal.get("alerts", [])),
    ]
    # Append to existing log
    existing = ws.get_all_values()
    if not existing:
        ws.update(range_name="A1", values=[["Timestamp", "FSI", "Trend", "Components", "Alerts"]])
        existing = [["header"]]
    ws.append_row(signal_row)
    print(f"  Signal log: appended 1 row")

    print("Google Sheets export complete!")
    return True


if __name__ == "__main__":
    export_to_sheets()
