"""
Comprehensive Exporters Suite:
- JSON (.json)
- CSV (.csv)
- Excel (.xlsx)
- SQLite Database (.db / .sqlite)
- Pandas DataFrame
"""

import csv
import json
import os
import sqlite3
from typing import Any, Dict, List, Union

from .models import MessageData


def _to_rows(messages: List[Union[MessageData, dict]]) -> List[Dict[str, Any]]:
    rows = []
    for msg in messages:
        d = msg.to_dict() if isinstance(msg, MessageData) else msg
        media = d.get("media") or {}
        row = {
            "id": d.get("id"),
            "chat_id": d.get("chat_id"),
            "chat_title": d.get("chat_title"),
            "date": str(d.get("date")),
            "sender_id": d.get("sender_id"),
            "sender_name": d.get("sender_name"),
            "text": d.get("text", ""),
            "views": d.get("views"),
            "forwards": d.get("forwards"),
            "reply_to_msg_id": d.get("reply_to_msg_id"),
            "has_media": bool(d.get("has_media")),
            "media_type": media.get("media_type"),
            "file_name": media.get("file_name"),
            "file_size_bytes": media.get("file_size"),
        }
        rows.append(row)
    return rows


def export_to_json(messages: List[Union[MessageData, dict]], filepath: str) -> str:
    """Export scraped messages to JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    data = [msg.to_dict() if isinstance(msg, MessageData) else msg for msg in messages]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return os.path.abspath(filepath)


def export_to_csv(messages: List[Union[MessageData, dict]], filepath: str) -> str:
    """Export scraped messages to CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    rows = _to_rows(messages)
    fieldnames = [
        "id",
        "chat_id",
        "chat_title",
        "date",
        "sender_id",
        "sender_name",
        "text",
        "views",
        "forwards",
        "reply_to_msg_id",
        "has_media",
        "media_type",
        "file_name",
        "file_size_bytes",
    ]

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)
    return os.path.abspath(filepath)


def export_to_excel(messages: List[Union[MessageData, dict]], filepath: str) -> str:
    """
    Export scraped messages to an Excel (.xlsx) file.
    Uses openpyxl or pandas if installed, with CSV fallback.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    rows = _to_rows(messages)

    try:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Messages"

        if rows:
            headers = list(rows[0].keys())
            ws.append(headers)
            for r in rows:
                ws.append([r.get(h) for h in headers])
        else:
            ws.append(["id", "chat_id", "text", "date"])

        wb.save(filepath)
        return os.path.abspath(filepath)
    except ImportError:
        # Fallback to pandas
        try:
            import pandas as pd

            df = pd.DataFrame(rows)
            df.to_excel(filepath, index=False)
            return os.path.abspath(filepath)
        except ImportError:
            # Fallback to CSV if no Excel library installed
            csv_path = filepath.replace(".xlsx", ".csv")
            export_to_csv(messages, csv_path)
            return os.path.abspath(csv_path)


def export_to_sqlite(
    messages: List[Union[MessageData, dict]], db_path: str, table_name: str = "scraped_messages"
) -> str:
    """
    Export scraped messages into a local SQLite database table.
    """
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    rows = _to_rows(messages)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY,
            chat_id INTEGER,
            chat_title TEXT,
            date TEXT,
            sender_id INTEGER,
            sender_name TEXT,
            text TEXT,
            views INTEGER,
            forwards INTEGER,
            reply_to_msg_id INTEGER,
            has_media BOOLEAN,
            media_type TEXT,
            file_name TEXT,
            file_size_bytes INTEGER
        )
    """)

    for r in rows:
        c.execute(
            f"""
            INSERT OR REPLACE INTO {table_name} (
                id, chat_id, chat_title, date, sender_id, sender_name,
                text, views, forwards, reply_to_msg_id, has_media,
                media_type, file_name, file_size_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                r["id"],
                r["chat_id"],
                r["chat_title"],
                r["date"],
                r["sender_id"],
                r["sender_name"],
                r["text"],
                r["views"],
                r["forwards"],
                r["reply_to_msg_id"],
                r["has_media"],
                r["media_type"],
                r["file_name"],
                r["file_size_bytes"],
            ),
        )

    conn.commit()
    conn.close()
    return os.path.abspath(db_path)


def to_dataframe(messages: List[Union[MessageData, dict]]) -> Any:
    """
    Convert scraped messages into a Pandas DataFrame.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("Pandas is not installed. Install with `pip install pandas`.")

    rows = _to_rows(messages)
    return pd.DataFrame(rows)
