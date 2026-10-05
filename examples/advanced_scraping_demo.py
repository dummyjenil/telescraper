"""
Demonstration of all 6 Advanced Pure Synchronous Scraping Features:
1. Server-Side MTProto Filters (photos, videos, documents, voice, urls)
2. Resumable Checkpointed Scraping (checkpoint='progress.json')
3. Multi-Threaded Parallel File Downloader (4x faster chunks)
4. Advanced Exporters (Excel, SQLite, DataFrame, JSON, CSV)
5. Linked Discussion Comments Scraping
6. Regex Data Extractor (Emails, Phones, URLs, Crypto Wallets: BTC, ETH, TON, SOL, USDT)
"""

from telescraper import TeleScraper, ScrapeCheckpoint

API_ID = 12345678
API_HASH = "your_api_hash"
SESSION = "advanced_scraper_session"

with TeleScraper(SESSION, API_ID, API_HASH) as scraper:
    CHANNEL = "target_channel_username"

    # -------------------------------------------------------------------------
    # Feature 1: ⚡ Server-Side MTProto Filters (10x Faster Media Scraping)
    # -------------------------------------------------------------------------
    print("[1] Scraping ONLY photos directly from Telegram server...")
    for msg in scraper.iter_messages(CHANNEL, filter_type="photos", limit=20):
        print(f"Photo Message ID: {msg.id} | Date: {msg.date}")

    # -------------------------------------------------------------------------
    # Feature 2: 🔁 Resumable Scraping (Checkpoint State Manager)
    # -------------------------------------------------------------------------
    print("\n[2] Scraping with checkpoint tracking (auto-resumes if stopped)...")
    for msg in scraper.iter_messages(CHANNEL, checkpoint="channel_progress.json", limit=50):
        print(f"Scraped & Saved progress for Msg ID: {msg.id}")

    # -------------------------------------------------------------------------
    # Feature 3: 🧵 Multi-Threaded Parallel File Downloader (Fast 4x Download)
    # -------------------------------------------------------------------------
    print("\n[3] Downloading large media file using 4 parallel worker threads...")
    # messages = scraper.get_messages(CHANNEL, limit=5)
    # for msg in messages:
    #     if msg.has_media:
    #         saved_path = scraper.download_parallel(msg, output_dir="./downloads", num_threads=4)
    #         print(f"Parallel Download complete: {saved_path}")

    # -------------------------------------------------------------------------
    # Feature 4: 📊 Advanced Exporters (Excel, SQLite, Pandas DataFrame)
    # -------------------------------------------------------------------------
    print("\n[4] Exporting scraped channel data to Excel and SQLite...")
    excel_path = scraper.export_to_excel(CHANNEL, "output.xlsx", limit=100)
    sqlite_path = scraper.export_to_sqlite(CHANNEL, "scraped_data.db", limit=100)
    print(f"Exported Excel: {excel_path}")
    print(f"Exported SQLite: {sqlite_path}")

    # Or directly get a Pandas DataFrame for data science:
    # df = scraper.to_dataframe(CHANNEL, limit=100)
    # print(df.head())

    # -------------------------------------------------------------------------
    # Feature 5: 👥 Linked Discussion / Comments Scraper
    # -------------------------------------------------------------------------
    print("\n[5] Scraping comments from a channel post's discussion group...")
    # for comment in scraper.iter_comments(CHANNEL, post_id=123, limit=50):
    #     print(f"Comment from {comment.sender_name}: {comment.text}")

    # -------------------------------------------------------------------------
    # Feature 6: 🧠 Regex Data Extractor (Emails, Phones, Crypto Wallets)
    # -------------------------------------------------------------------------
    print("\n[6] Extracting structured data and crypto wallets from messages...")
    extracted = scraper.extract_from_messages(CHANNEL, limit=100)
    print("Found Emails:", extracted["emails"])
    print("Found Phones:", extracted["phones"])
    print("Found Crypto Wallets:", extracted["wallets"])
