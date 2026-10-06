"""
Demonstration of all advanced Pure Synchronous TeleScraper features:
- QR Code Login
- StringSession
- Takeout Session (Mass Data Scraping)
- Message Sending, Editing, Forwarding, Pinning, Deleting, Reactions, Drafts
- File and Media Uploading (Small & Large 2GB Files)
- Secret Chats
"""

from telescraper import StringSession, TeleScraper

API_ID = 12345678
API_HASH = "your_api_hash"

# Option 1: SQLite session or Option 2: StringSession
session = StringSession()  # Or "my_session.session"

with TeleScraper(session, API_ID, API_HASH) as scraper:
    # -------------------------------------------------------------
    # 1. QR Code Login (Scan with Telegram mobile app)
    # -------------------------------------------------------------
    # qr = scraper.qr_login(print_qr=True)
    # user = qr.wait()

    # -------------------------------------------------------------
    # 2. StringSession Export
    # -------------------------------------------------------------
    # session_string = scraper.session.save()
    # print("Your saved StringSession:", session_string)

    # -------------------------------------------------------------
    # 3. Takeout Session (High speed export with reduced flood limits)
    # -------------------------------------------------------------
    # with scraper.takeout(message_channels=True, files=True) as takeout:
    #     for msg in takeout.iter_messages("target_channel", limit=1000):
    #         print(msg.id, msg.text)

    # -------------------------------------------------------------
    # 4. Message Operations: Send, Edit, Pin, Reaction, Draft, Delete
    # -------------------------------------------------------------
    # msg = scraper.send_message("me", "Hello from pure sync TeleScraper!")
    # scraper.edit_message("me", msg.id, "Edited message text")
    # scraper.send_reaction("me", msg.id, "🔥")
    # scraper.pin_message("me", msg.id)
    # scraper.save_draft("me", "This is an unsent draft message")
    # scraper.delete_messages("me", [msg.id])

    # -------------------------------------------------------------
    # 5. File Uploading & Media
    # -------------------------------------------------------------
    # scraper.send_file("me", "photo.jpg", caption="Sent via pure sync uploader")
    # scraper.download_profile_photo("username", output_dir="./avatars")

    # -------------------------------------------------------------
    # 6. End-to-End Encrypted Secret Chat
    # -------------------------------------------------------------
    # secret_chat = scraper.create_secret_chat("target_username")
    pass
