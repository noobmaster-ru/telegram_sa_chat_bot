from gspread import service_account

class GoogleSheetClass():
    def __init__(self, service_account_json: str, table_url: str):
        self.client = service_account(filename=service_account_json)
        self.spreadsheet = self.client.open_by_url(table_url)
    
    def get_article(self, sheet_name: str) -> int:
        main_sheet = self.spreadsheet.worksheet(sheet_name)
        nm_id = main_sheet.acell('A2').value
        return nm_id
