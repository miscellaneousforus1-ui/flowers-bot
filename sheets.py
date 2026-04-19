import os
import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

FLOWERS_TAB = "Цветы"
SALES_TAB   = "Продажи"

# Позиции столбцов (1-based) — лист «Цветы»
F_ID             = 1
F_NAME           = 2
F_VARIETY        = 3
F_ROOT           = 4
F_PURCHASE_PRICE = 5
F_PURCHASE_DATE  = 6
F_PLANTING_DATE  = 7
F_STATUS         = 8

FIELD_COL = {
    "name":           F_NAME,
    "variety":        F_VARIETY,
    "root":           F_ROOT,
    "purchase_price": F_PURCHASE_PRICE,
    "purchase_date":  F_PURCHASE_DATE,
    "planting_date":  F_PLANTING_DATE,
    "status":         F_STATUS,
}


class SheetsManager:
    def __init__(self):
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if creds_json:
            info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(
                "credentials.json", scopes=SCOPES
            )

        self.client = gspread.authorize(creds)
        spreadsheet_id = os.environ["SPREADSHEET_ID"]
        self.ss = self.client.open_by_key(spreadsheet_id)
        self._ensure_sheets()

    # ── Инициализация листов ─────────────────────────────────────────────────
    def _ensure_sheets(self):
        existing = [ws.title for ws in self.ss.worksheets()]

        if FLOWERS_TAB not in existing:
            ws = self.ss.add_worksheet(FLOWERS_TAB, rows=1000, cols=8)
            ws.append_row([
                "ID", "Название", "Сорт", "Корневая система",
                "Цена покупки", "Дата покупки", "Дата посадки", "Статус",
            ])

        if SALES_TAB not in existing:
            ws = self.ss.add_worksheet(SALES_TAB, rows=1000, cols=6)
            ws.append_row([
                "ID", "ID цветка", "Название цветка",
                "Тип продажи", "Цена", "Дата",
            ])

    # ── Вспомогательные ──────────────────────────────────────────────────────
    def _flowers_ws(self):
        return self.ss.worksheet(FLOWERS_TAB)

    def _sales_ws(self):
        return self.ss.worksheet(SALES_TAB)

    def _next_id(self, ws) -> str:
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return "1"
        ids = []
        for row in rows[1:]:
            if row and row[0]:
                try:
                    ids.append(int(row[0]))
                except ValueError:
                    pass
        return str(max(ids) + 1) if ids else "1"

    def _row_to_flower(self, row: list) -> dict:
        while len(row) < 8:
            row.append("")
        return {
            "id":             row[F_ID - 1],
            "name":           row[F_NAME - 1],
            "variety":        row[F_VARIETY - 1],
            "root":           row[F_ROOT - 1],
            "purchase_price": row[F_PURCHASE_PRICE - 1],
            "purchase_date":  row[F_PURCHASE_DATE - 1],
            "planting_date":  row[F_PLANTING_DATE - 1],
            "status":         row[F_STATUS - 1],
        }

    # ── Цветы: создание ──────────────────────────────────────────────────────
    def add_flower(self, data: dict) -> str:
        ws = self._flowers_ws()
        flower_id = self._next_id(ws)
        ws.append_row([
            flower_id,
            data["name"],
            data["variety"],
            data["root"],
            data["purchase_price"],
            data["purchase_date"],
            data["planting_date"],
            "живой",
        ])
        return flower_id

    # ── Цветы: поиск ─────────────────────────────────────────────────────────
    def find_flowers(self, query: str, status_filter: list = None) -> list:
        ws = self._flowers_ws()
        rows = ws.get_all_values()
        q = query.lower()
        results = []
        for row in rows[1:]:
            if not row or not row[0]:
                continue
            f = self._row_to_flower(row)
            name_match = q in f["name"].lower() or q in f["variety"].lower()
            if not name_match:
                continue
            if status_filter and f["status"] not in status_filter:
                continue
            results.append(f)
        return results

    def get_flower_by_id(self, flower_id: str) -> dict | None:
        ws = self._flowers_ws()
        for row in ws.get_all_values()[1:]:
            if row and row[0] == str(flower_id):
                return self._row_to_flower(row)
        return None

    def get_all_flowers(self, status_filter: list = None) -> list:
        ws = self._flowers_ws()
        results = []
        for row in ws.get_all_values()[1:]:
            if not row or not row[0]:
                continue
            f = self._row_to_flower(row)
            if status_filter and f["status"] not in status_filter:
                continue
            results.append(f)
        return results

    # ── Цветы: обновление ────────────────────────────────────────────────────
    def update_flower_field(self, flower_id: str, field: str, value):
        col = FIELD_COL.get(field)
        if not col:
            return
        ws = self._flowers_ws()
        for i, row in enumerate(ws.get_all_values(), start=1):
            if row and row[0] == str(flower_id):
                ws.update_cell(i, col, value)
                return

    # ── Цветы: удаление ──────────────────────────────────────────────────────
    def delete_flower(self, flower_id: str):
        ws = self._flowers_ws()
        for i, row in enumerate(ws.get_all_values(), start=1):
            if row and row[0] == str(flower_id):
                ws.delete_rows(i)
                return

    # ── Продажи ──────────────────────────────────────────────────────────────
    def add_sale(
        self,
        flower_id: str,
        flower_name: str,
        sale_type: str,
        price: float,
        date: str,
    ) -> str:
        ws = self._sales_ws()
        sale_id = self._next_id(ws)
        ws.append_row([sale_id, flower_id, flower_name, sale_type, price, date])
        return sale_id

    def get_flower_sales(self, flower_id: str) -> list:
        ws = self._sales_ws()
        sales = []
        for row in ws.get_all_values()[1:]:
            if row and len(row) >= 6 and row[1] == str(flower_id):
                sales.append({
                    "id":          row[0],
                    "flower_id":   row[1],
                    "flower_name": row[2],
                    "type":        row[3],
                    "price":       row[4],
                    "date":        row[5],
                })
        return sales
