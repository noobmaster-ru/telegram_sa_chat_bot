import re


def escape_markdown_v2(text: str) -> str:
    return re.sub(r"([_\[\]()~#+>\-=|{}.!])", r"\\\1", text)
