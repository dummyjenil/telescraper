# TeleScraper: Complete Technical Documentation & API Reference

**TeleScraper** is a high-performance, 100% pure-synchronous Python client and scraping engine for Telegram MTProto 2.0. It is engineered from first principles with **zero asyncio event loops**, standard blocking sockets, and multi-threaded scaling.

---

## 📑 Table of Contents

1. [Architectural Overview](#1-architectural-overview)
2. [Installation & Requirements](#2-installation--requirements)
3. [Client Initialization & Sessions](#3-client-initialization--sessions)
4. [Authentication Methods](#4-authentication-methods)
5. [Anti-Censorship & Transports](#5-anti-censorship--transports)
6. [Scraping & Server-Side Filtering](#6-scraping--server-side-filtering)
7. [Resumable Checkpoints](#7-resumable-checkpoints)
8. [Data Extractors (Regex & Wallets)](#8-data-extractors-regex--wallets)
9. [Multi-Format Exporters](#9-multi-format-exporters)
10. [Media Downloader & 4x Parallel Engine](#10-media-downloader--4x-parallel-engine)
11. [Chunked File Uploader (Up to 2GB)](#11-chunked-file-uploader-up-to-2gb)
12. [Group, Channel & Permissions Administration](#12-group-channel--permissions-administration)
13. [Telegram Stories Engine](#13-telegram-stories-engine)
14. [State Synchronization & Gap Recovery](#14-state-synchronization--gap-recovery)
15. [VoIP Voice & Video Call Signalling](#15-voip-voice--video-call-signalling)
16. [End-to-End Secret Chats](#16-end-to-end-secret-chats)
17. [Full API Reference](#17-full-api-reference)

---

## 1. Architectural Overview

Unlike asynchronous frameworks (like Telethon or Pyrogram) which require `async def`, `await`, and manage complex `asyncio` event loops, TeleScraper operates on a **Pure Synchronous Paradigm**:
* **Network Layer**: Pure blocking `socket.socket` with customizable timeouts.
* **Cryptography**: Multi-tiered MTProto 2.0 AES-IGE (with native OpenSSL ctypes acceleration and pure Python `pyaes` fallback) and a built-in DER PKCS#1 RSA parser without third-party RSA pip dependencies.
* **Concurrency**: Multi-threaded parallelism via Python's native `concurrent.futures.ThreadPoolExecutor` and OS threads (`threading.Thread`).

---

## 2. Installation & Requirements

### System Requirements
* Python 3.8+
* Mandatory Dependency: `pyaes==1.6.1`
* Optional Dependencies: `pillow` (for automatic image resizing), `hachoir` (for media metadata extraction), `pandas` & `openpyxl` (for direct DataFrame and Excel exports).

### Installation
```bash
# Clone the repository
git clone https://github.com/your-org/telescraper.git
cd telescraper

# Install using uv or pip
uv pip install -e .
# or
pip install -e .
```

---

## 3. Client Initialization & Sessions

### SQLite Disk Session (`SyncSession`)
Persists data center information, authorization keys, and user credentials into an SQLite `.session` file:
```python
from telescraper import TeleScraper

client = TeleScraper(
    session="my_account",  # Creates my_account.session
    api_id=123456,
    api_hash="0123456789abcdef0123456789abcdef"
)
```

### In-Memory Base64 StringSession (`StringSession`)
Zero-disk, ephemeral session management fully compatible with Telethon version 1 string sessions:
```python
from telescraper import TeleScraper, StringSession

# Load from existing string
session = StringSession("1AZA...==")
client = TeleScraper(session=session, api_id=123456, api_hash="abcdef")

# Save session to string
session_str = client.session.save()
print("Saved session:", session_str)
```

---

## 4. Authentication Methods

### Interactive Phone & OTP Code
```python
client.start(phone="+1234567890")
# Handles SMS/Telegram OTP and 2FA cloud password automatically.
```

### Desktop QR Code Login
```python
qr = client.qr_login(print_qr=True)
# Displays terminal ASCII QR code and polls until approved on mobile.
success = qr.wait(timeout=120)
```

### Bot Token Login
```python
client.start(bot_token="123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ")
# or direct call
client.bot_login("123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ")
```

### Session & Device Management
```python
# List active authorized devices
devices = client.get_authorizations()
for d in devices:
    print(d.device_model, d.platform, d.ip)

# Terminate all other sessions except current
client.reset_authorizations()

# Terminate specific session by authorization hash
client.terminate_session(hash=123456789)

# Logout and revoke authorization key
client.log_out()
```

### High-Volume Data Takeout Session
```python
with client.takeout(contacts=True, message_users=True, message_chats=True) as takeout:
    for msg in takeout.iter_messages("channel_name", limit=5000):
        print(msg.id, msg.text)
```

---

## 5. Anti-Censorship & Transports

TeleScraper provides 7 synchronous TCP and HTTP transports to bypass censorship and Deep Packet Inspection (DPI):

```python
from telescraper.network.connection import (
    ConnectionTcpIntermediate,
    ConnectionTcpRandomizedIntermediate,
    ConnectionTcpObfuscated,
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpFull,
    ConnectionTcpAbridged,
    ConnectionHttp,
)

# 1. Standard Intermediate
client = TeleScraper(connection=ConnectionTcpIntermediate, ...)

# 2. Randomized Intermediate (Censorship evasion with random padding)
client = TeleScraper(connection=ConnectionTcpRandomizedIntermediate, ...)

# 3. Obfuscated2 (64-byte handshake + bidirectional AES-128-CTR stream cipher)
client = TeleScraper(connection=ConnectionTcpObfuscated, ...)

# 4. MTProxy (Supports standard 32-hex, 'dd' prefix, and Fake-TLS 'ee' secrets)
client = TeleScraper(
    connection=ConnectionTcpMTProxyIntermediate,
    proxy=("proxy.example.com", 443, "dd000102030405060708090a0b0c0d0e0f"),
    ...
)

# 5. HTTP Transport Fallback (Port 80/443 POST tunneling)
client = TeleScraper(connection=ConnectionHttp, ...)
```

---

## 6. Scraping & Server-Side Filtering

### 10x Fast Media Scraping (Server-Side MTProto Filters)
Instead of downloading thousands of text messages and checking if they contain media, TeleScraper queries Telegram servers directly for specific media types:

```python
# Server-side filters: 'photos', 'videos', 'documents', 'audio', 'voice', 'urls', 'round_videos', 'gifs', 'pinned'
for photo_msg in client.iter_messages("crypto_vip", filter_type="photos", limit=500):
    print(f"Photo Msg ID: {photo_msg.id} - Date: {photo_msg.date}")

for doc_msg in client.iter_messages("ebooks_hub", filter_type="documents", limit=100):
    print(f"Document: {doc_msg.media.file_name} ({doc_msg.media.file_size} bytes)")
```

### Linked Discussion & Comments Scraping
Scrapes comments under posts from linked discussion groups:
```python
for comment in client.iter_comments("tech_news", post_id=1420, limit=50):
    print(f"[{comment.sender_name}]: {comment.text}")
```

### Members & Participants Scraping
```python
for member in client.iter_members("python_developers", limit=1000):
    print(f"{member.first_name} (@{member.username}) - Role: {member.status}")
```

---

## 7. Resumable Checkpoints

Never lose scraping progress when network fails or jobs get interrupted:
```python
from telescraper import ScrapeCheckpoint

# Resumes from last saved message ID automatically
for msg in client.iter_messages("large_channel", checkpoint="progress.json"):
    # Process message
    pass
```

---

## 8. Data Extractors (Regex & Wallets)

Built-in automated regex extraction for sensitive and structured data:
```python
text = """
Contact support at help@company.org or +1-800-555-0199.
Send payment to Bitcoin: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
or USDT (TRC20): TXjB9W4VnJq42hZt2nLp1pE1d4B5c6D7E8
or TON: EQCD39VS5jcptHL8vMjEXrzGaRcCVYto7HUn4bpAOg8xqB2N
"""

# Extract from raw text
data = client.extract_data(text)
print("Emails:", data["emails"])
print("Wallets:", data["wallets"])

# Or extract across an entire channel
aggregated = client.extract_from_messages("crypto_signals_channel", limit=200)
print("Discovered Bitcoin Wallets:", aggregated["wallets"]["bitcoin"])
print("Discovered Solana Wallets:", aggregated["wallets"]["solana"])
```

---

## 9. Multi-Format Exporters

Export scraped channel datasets directly into various formats in one line:
```python
# 1. Excel Spreadsheet (.xlsx)
client.export_to_excel("channel_name", "output.xlsx", limit=1000)

# 2. SQLite Database (.db)
client.export_to_sqlite("channel_name", "database.db", table_name="scraped_posts", limit=1000)

# 3. Pandas DataFrame (For Data Science & AI workflows)
df = client.to_dataframe("channel_name", limit=500)
print(df.head())

# 4. JSON & CSV
client.export_to_json("channel_name", "messages.json", limit=1000)
client.export_to_csv("channel_name", "messages.csv", limit=1000)
```

---

## 10. Media Downloader & 4x Parallel Engine

### Multi-Threaded Parallel File Downloader
Downloads files 4x faster using concurrent chunk workers (`ThreadPoolExecutor`):
```python
messages = client.get_messages("movies_channel", limit=10)
for msg in messages:
    if msg.has_media:
        saved_path = client.download_parallel(
            msg,
            output_dir="./downloads",
            num_threads=4,
            progress_callback=lambda rec, total: print(f"{rec}/{total} bytes", end='\r')
        )
        print("Downloaded to:", saved_path)
```

### Bulk Channel Media Downloader
```python
client.download_all_media(
    target="wallpapers_channel",
    output_dir="./wallpapers",
    limit=100,
    media_types=["photo"]
)
```

### Profile Avatar Downloader & Manager
```python
# Download avatar
avatar_path = client.download_profile_photo("username", output_dir="./avatars")

# Upload and set new profile photo
client.set_profile_photo("new_avatar.jpg", workers=4)

# Get profile photos history
photos = client.get_profile_photos("me", limit=5)

# Delete profile photos
client.delete_profile_photos([photos[0].id])
```

---

## 11. Chunked File Uploader (Up to 2GB)

Supports small files, large 2GB media, and multi-threaded parallel chunk uploads:
```python
# Multi-threaded fast upload with progress bar
def progress(uploaded, total):
    print(f"Uploaded: {uploaded}/{total} bytes ({(uploaded/total)*100:.1f}%)", end='\r')

client.send_file(
    target="my_channel",
    file="large_archive.zip",
    caption="Here is the backup archive.",
    workers=4,
    progress_callback=progress
)
```

---

## 12. Group, Channel & Permissions Administration

### Moderation & Permissions
```python
# Ban / Restrict participant
client.edit_permissions(
    chat="my_group",
    user="bad_user",
    send_messages=False,
    send_media=False,
    send_stickers=False
)

# Kick participant (temporary ban + unban)
client.kick_participant("my_group", "spammer")

# Inspect Admin Audit Log
events = client.get_admin_log("my_group", limit=50)
for ev in events:
    print(ev.date, ev.action)
```

### Channels, Groups & Invite Links
```python
# Create channel or group
channel = client.create_channel("New Announcements", about="Official updates")
group = client.create_group("Community Group", users=["@user1", "@user2"])

# Create custom invite link
link = client.create_invite_link(
    chat="my_group",
    title="VIP Promo Link",
    usage_limit=50,
    expire_date=1780000000
)
print("Invite link:", link.link)

# Revoke invite link
client.revoke_invite_link("my_group", link=link.link)

# List all invite links
invites = client.get_invite_links("my_group")
```

---

## 13. Telegram Stories Engine

```python
# Get active stories of a peer
peer_stories = client.get_peer_stories("durov")

# Post a story
story = client.post_story(
    target="me",
    file_path="story_photo.jpg",
    caption="Enjoying the day!",
    period=86400  # 24 hours
)

# Delete stories
client.delete_stories("me", story_ids=[story.id])
```

---

## 14. State Synchronization & Gap Recovery

Synchronize account message sequence states and recover missed updates:
```python
# Get current PTS/QTS state
state = client.get_state()
print(f"Current PTS: {state.pts}, QTS: {state.qts}, Date: {state.date}")

# Recover missed updates difference
diff = client.get_difference(pts=state.pts - 50, date=state.date - 3600)

# Recover missed channel updates
channel_diff = client.get_channel_difference("my_channel", pts=120)
```

---

## 15. VoIP Voice & Video Call Signalling

Pure synchronous MTProto voice and video call signalling with Diffie-Hellman cryptographic key fingerprint exchange:
```python
# 1. Request outgoing call
call_res = client.voip.request_call("username", video=False)

# 2. Accept incoming call
accept_res, fingerprint = client.voip.accept_call(
    call_id=12345,
    access_hash=67890,
    g_a=sender_g_a_bytes
)
print("Shared DH Key Fingerprint:", fingerprint)

# 3. Discard / Hang up call
client.voip.discard_call(call_id=12345, access_hash=67890)

# 4. Fetch VoIP STUN/TURN configurations
config = client.voip.get_call_config()
```

---

## 16. End-to-End Secret Chats

Create End-to-End Encrypted (E2EE) secret chats:
```python
secret_chat = client.create_secret_chat("target_user")
print(f"Secret chat created with ID: {secret_chat.chat_id}")
```

---

## 17. Full API Reference

| Method / Property | Description |
| :--- | :--- |
| `client.connect()` | Connects to Telegram DC and performs initial handshake |
| `client.disconnect()` | Closes TCP connection and pooled DC senders |
| `client.is_user_authorized()` | Checks if current session is logged in |
| `client.start(...)` | Interactive phone/code or bot token login |
| `client.bot_login(bot_token)` | Authenticates as a Telegram bot |
| `client.qr_login(print_qr=True)` | Generates QR code and polls for desktop login |
| `client.takeout(...)` | Creates a high-volume data takeout session context |
| `client.iter_messages(...)` | Yields strongly-typed `MessageData` with filters and checkpoints |
| `client.get_messages(...)` | Returns list of `MessageData` |
| `client.iter_comments(...)` | Yields comments from linked channel discussion groups |
| `client.iter_members(...)` | Yields group/channel participant dataclasses |
| `client.get_chat_info(...)` | Fetches `ChatData` metadata and subscriber counts |
| `client.extract_data(text)` | Regex extracts emails, phones, URLs, and crypto wallets |
| `client.extract_from_messages(...)` | Aggregates all extracted entities from a channel |
| `client.export_to_json(...)` | Exports messages to JSON |
| `client.export_to_csv(...)` | Exports messages to CSV |
| `client.export_to_excel(...)` | Exports messages to Excel (.xlsx) |
| `client.export_to_sqlite(...)` | Exports messages to SQLite (.db) |
| `client.to_dataframe(...)` | Converts messages to Pandas DataFrame |
| `client.download_media(...)` | Downloads message media chunk-by-chunk |
| `client.download_parallel(...)` | 4x faster media downloads using multi-threaded chunk workers |
| `client.download_all_media(...)` | Bulk channel downloader with progress bars |
| `client.upload_file(...)` | Uploads files up to 2GB with optional thread workers |
| `client.send_file(...)` | Uploads and dispatches media to chats |
| `client.send_message(...)` | Dispatches text messages |
| `client.edit_message(...)` | Edits previously sent messages |
| `client.delete_messages(...)` | Deletes messages with revoke support |
| `client.set_profile_photo(...)` | Uploads and sets user profile avatar |
| `client.delete_profile_photos(...)` | Deletes profile pictures from history |
| `client.create_invite_link(...)` | Creates custom chat invite links |
| `client.get_peer_stories(...)` | Scrapes user and channel stories |
| `client.post_story(...)` | Dispatches photo/video stories |
| `client.get_state()` | Fetches current update state (pts, qts, date, seq) |
| `client.get_difference(...)` | Recovers missed update gaps |
| `client.voip` | Accesses the VoIP & Video call signalling manager |
| `client.sender_pool` | Accesses persistent foreign DC sender connections |
