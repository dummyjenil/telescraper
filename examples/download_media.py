"""Example demonstrating how to download photos, videos, or documents from a channel."""

from telescraper import TeleScraper

API_ID = 12345678              # Replace with your Telegram API ID
API_HASH = "your_api_hash"     # Replace with your Telegram API Hash
SESSION = "downloader_session"

TARGET = "target_channel_username"
DOWNLOAD_FOLDER = "./downloads"

with TeleScraper(SESSION, API_ID, API_HASH) as scraper:
    print(f"[*] Starting media download from {TARGET}...")

    # Method 1: Bulk download all media with progress
    downloaded_files = scraper.download_all_media(
        target=TARGET,
        output_dir=DOWNLOAD_FOLDER,
        limit=50,  # Scan through the last 50 messages
        media_types=["photo", "video", "document"],  # or specify ['photo'] only
        show_progress=True
    )
    print(f"\n[✔] Total files downloaded: {len(downloaded_files)}")

    # Method 2: Download individually per message
    # for msg in scraper.iter_messages(TARGET, limit=10):
    #     if msg.has_media:
    #         saved_path = msg.download(output_dir="./custom_folder")
    #         print(f"Downloaded: {saved_path}")
