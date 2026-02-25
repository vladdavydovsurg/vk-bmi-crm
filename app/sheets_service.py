import logging
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

import json

logger = logging.getLogger(__name__)


class SheetsService:
    def __init__(self, service_account_json: str, master_sheet_id: str) -> None:
        self.master_sheet_id = master_sheet_id

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        credentials = Credentials.from_service_account_info(
            json.loads(service_account_json),
            scopes=scopes,
        )

        self.client = gspread.authorize(credentials)
        self.master_spreadsheet = self.client.open_by_key(master_sheet_id)

    # =========================================================
    # MASTER TABLE
    # =========================================================

    async def append_to_master(self, lead_data: dict[str, Any]) -> None:
        logger.info(
            "SheetsService.append_to_master called for lead_id=%s",
            lead_data.get("id"),
        )

        worksheet = self.master_spreadsheet.worksheet("leads")

        row = [
            lead_data.get("id"),
            lead_data.get("created_at"),
            lead_data.get("name"),
            lead_data.get("phone"),
            lead_data.get("telegram_username"),
            lead_data.get("whatsapp"),
            lead_data.get("messenger_max"),
            lead_data.get("email"),
            lead_data.get("weight_kg"),
            lead_data.get("height_cm"),
            lead_data.get("bmi"),
            lead_data.get("lead_type"),
            lead_data.get("manager_name"),
            lead_data.get("manager_status"),
            lead_data.get("comment_from_admin"),
            lead_data.get("tg_link"),
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")

    # =========================================================
    # MANAGER TABLE
    # =========================================================

    async def append_to_manager_sheet(
        self,
        manager_sheet_id: str,
        lead_data: dict[str, Any],
    ) -> None:

        logger.info(
            "SheetsService.append_to_manager_sheet called for lead_id=%s manager_sheet_id=%s",
            lead_data.get("id"),
            manager_sheet_id,
        )

        spreadsheet = self.client.open_by_key(manager_sheet_id)
        worksheet = spreadsheet.worksheet("leads")

        row = [
            lead_data.get("id"),
            lead_data.get("created_at"),
            lead_data.get("name"),
            lead_data.get("phone"),
            lead_data.get("telegram_username"),
            lead_data.get("whatsapp"),
            lead_data.get("messenger_max"),
            lead_data.get("email"),
            lead_data.get("weight_kg"),
            lead_data.get("height_cm"),
            lead_data.get("bmi"),
            lead_data.get("lead_type"),
            lead_data.get("manager_status"),
            lead_data.get("comment_from_admin"),
            lead_data.get("tg_link"),
        ]

        worksheet.append_row(row, value_input_option="USER_ENTERED")

    # =========================================================
    # UPDATE STATUS (UNIVERSAL)
    # =========================================================

    async def update_status_in_sheet(
        self,
        sheet_id: str,
        lead_id: str,
        new_status: str,
    ) -> None:
        """
        Обновляет статус лида в таблице.
        Работает и для master, и для таблиц менеджеров.
        Не зависит от номера колонки — ищет по заголовку.
        """

        spreadsheet = self.client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet("leads")

        try:
            cell = worksheet.find(lead_id)
        except Exception:
            logger.warning("Lead id %s not found in sheet %s", lead_id, sheet_id)
            return

        row_number = cell.row

        headers = worksheet.row_values(1)

        if "manager_status" not in headers:
            logger.warning("manager_status column not found in sheet %s", sheet_id)
            return

        status_col_index = headers.index("manager_status") + 1

        worksheet.update_cell(row_number, status_col_index, new_status)

        logger.info(
            "Updated status for lead_id=%s in sheet=%s to %s",
            lead_id,
            sheet_id,
            new_status,
        )