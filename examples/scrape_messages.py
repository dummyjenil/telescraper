"""Example demonstrating how to scrape messages and export them to JSON/CSV."""

from telescraper import TeleScraper

API_ID = 12345678  # Replace with your Telegram API ID
API_HASH = "your_api_hash"  # Replace with your Telegram API Hash
SESSION = "scraper_session"

# Target channel or group
TARGET = "python"  # Username, ID, or invite link

with TeleScraper(SESSION, API_ID, API_HASH) as scraper:
    print(f"[*] Getting info for {TARGET}...")
    chat = scraper.get_chat_info(TARGET)
    print(f"Chat Title: {chat.title}")
    print(f"Subscribers / Members: {chat.participants_count}")
    print(f"Description: {chat.description}\n")

    # 1. Scrape latest 20 messages
    print("[*] Scraping messages:")
    for msg in scraper.iter_messages(TARGET, limit=20):
        print(f"[{msg.date}] ID {msg.id} | {msg.sender_name or 'Anonymous'}: {msg.text[:50]}")
        if msg.has_media:
            print(f"   -> Media: {msg.media.media_type} ({msg.media.file_name})")

    # 2. Export directly to JSON and CSV
    print("\n[*] Exporting messages...")
    json_file = scraper.export_messages(TARGET, output_file="./exports/messages.json", format="json", limit=50)
    csv_file = scraper.export_messages(TARGET, output_file="./exports/messages.csv", format="csv", limit=50)
    print(f"[✔] Exported JSON: {json_file}")
    print(f"[✔] Exported CSV: {csv_file}")
