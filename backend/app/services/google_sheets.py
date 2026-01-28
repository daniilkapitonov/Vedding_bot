import logging
from datetime import datetime
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from ..config import settings

logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1E1ihpG_QVQieYq07T73-7nkkil3Ne6bp-dsuraqXhx0"
SHEET_NAME = "Guest TG"

HEADERS = [
    "telegram_id",
    "tg_username",
    "full_name",
    "phone",
    "gender",
    "side",
    "attendance_status",
    "is_relative",
    "is_best_friend",
    "has_plus_one_requested",
    "plus_one_partner_username",
    "children",
    "allergies",
    "food",
    "alcohol",
    "updated_at",
    "created_at",
]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _get_service():
    path = settings.GOOGLE_SA_JSON_PATH
    if not path:
        raise RuntimeError("GOOGLE_SA_JSON_PATH not set")
    creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

def _sheet_id(service) -> int:
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == SHEET_NAME:
            return int(props.get("sheetId"))
    raise RuntimeError("Sheet 'Guest TG' not found")

def ensure_formatting(service) -> None:
    try:
        sheet_id = _sheet_id(service)
    except Exception as e:
        logger.warning("sheets: cannot get sheet id: %s", e)
        return

    # Ensure header row
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1:Q1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    ).execute()

    requests: list[dict[str, Any]] = []
    # Freeze header row
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    })
    # Header formatting
    requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.95, "green": 0.92, "blue": 0.88},
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"bold": True},
                    "wrapStrategy": "WRAP",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,wrapStrategy)",
        }
    })
    # Column widths
    widths = [110, 140, 200, 140, 100, 100, 140, 120, 130, 150, 220, 220, 180, 140, 220, 160, 160]
    for idx, w in enumerate(widths):
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": idx, "endIndex": idx + 1},
                "properties": {"pixelSize": w},
                "fields": "pixelSize",
            }
        })
    # Alternating colors
    requests.append({
        "addBanding": {
            "bandedRange": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0},
                "rowProperties": {
                    "firstBandColor": {"red": 0.98, "green": 0.96, "blue": 0.94},
                    "secondBandColor": {"red": 0.99, "green": 0.98, "blue": 0.96},
                },
            }
        }
    })
    # Filters
    requests.append({
        "setBasicFilter": {
            "filter": {"range": {"sheetId": sheet_id}}
        }
    })

    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests},
    ).execute()

def _read_rows(service) -> list[list[str]]:
    res = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A2:Q",
    ).execute()
    return res.get("values", []) or []

def upsert_row(service, row: list[str]) -> None:
    # row[0] is telegram_id
    rows = _read_rows(service)
    target_row_idx = None
    for i, r in enumerate(rows, start=2):
        if r and str(r[0]) == str(row[0]):
            target_row_idx = i
            break
    if target_row_idx is None:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:Q",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
    else:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A{target_row_idx}:Q{target_row_idx}",
            valueInputOption="RAW",
            body={"values": [row]},
        ).execute()

def to_row(data: dict) -> list[str]:
    def _b(v):
        return "true" if bool(v) else "false"
    return [
        str(data.get("telegram_id") or ""),
        data.get("tg_username") or "",
        data.get("full_name") or "",
        data.get("phone") or "",
        data.get("gender") or "",
        data.get("side") or "",
        data.get("attendance_status") or "",
        _b(data.get("is_relative")),
        _b(data.get("is_best_friend")),
        _b(data.get("has_plus_one_requested")),
        data.get("plus_one_partner_username") or "",
        data.get("children") or "",
        data.get("allergies") or "",
        data.get("food") or "",
        data.get("alcohol") or "",
        data.get("updated_at") or datetime.utcnow().isoformat(),
        data.get("created_at") or datetime.utcnow().isoformat(),
    ]
