from dataclasses import dataclass


@dataclass
class CashbackArticle:
    nm_id: int
    title: str
    brand_name: str
    instruction_text: str
    image_url: str
    in_stock: bool
