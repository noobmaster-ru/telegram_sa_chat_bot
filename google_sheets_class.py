from gspread import service_account
import re

class GoogleSheetClass():
    def __init__(self, service_account_json: str, table_url: str):
        self.client = service_account(filename=service_account_json)
        self.spreadsheet = self.client.open_by_url(table_url)
    
    def get_nm_id(self, sheet_articles: str) -> int:
        sheet = self.spreadsheet.worksheet(sheet_articles)
        nm_id = sheet.acell('A2').value
        return nm_id
    
    def get_instruction(self, sheet_instruction: str, nm_id: str) -> str:
        sheet = self.spreadsheet.worksheet(sheet_instruction)
        instruction_str = sheet.acell('A1').value

        # форматируем красиво и чтобы телеграм не ругался
        filled_instruction = instruction_str.format(nm_id=nm_id)
        return re.sub(r'([_\[\]()~#+\-=|{}.!])', r'\\\1', filled_instruction)
    
