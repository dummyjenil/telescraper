# 🚀 TeleScraper

> **100% Pure Synchronous Telegram MTProto Client & Scraping Engine for Python.**  
> *Zero Asyncio. Zero Telethon Dependency. High Performance. Pure Blocking Sockets & Threading.*

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MTProto](https://img.shields.io/badge/MTProto-2.0-orange.svg)](https://core.telegram.org/mtproto)
[![Asyncio-Free](https://img.shields.io/badge/Asyncio-0%25-red.svg)](#)

---

## ✨ Why TeleScraper?

Asynchronous libraries like Telethon and Pyrogram are built around `asyncio` event loops. While powerful for 24x7 bot hosting, `async`/`await` introduces significant complexities when integrating into data engineering pipelines, Celery tasks, standard multi-threaded workers, desktop applications (Tkinter/Qt), or Jupyter Notebooks.

**TeleScraper** is engineered from scratch for high-performance scraping and automation with a **100% pure synchronous execution model**.

### 🌟 Key Features
* ⚡ **10x Faster Media Scraping**: Direct server-side MTProto filters (`photos`, `videos`, `documents`, `audio`, `voice`, `urls`, `gifs`, `pinned`).
* 🧵 **4x Multi-Threaded Parallel Downloads & Uploads**: Thread-pooled chunk workers (`ThreadPoolExecutor`) without event loop bottlenecks.
* 🔁 **Resumable Scraping Checkpoints**: Automatically tracks progress (`progress.json`) and resumes interrupted scrapes.
* 📊 **Multi-Format Exporters**: Direct one-line exports to **Excel (.xlsx)**, **SQLite (.db)**, **Pandas DataFrame**, JSON, and CSV.
* 🧠 **Regex Entity Extractor**: Auto-extracts Emails, Phone numbers, URLs, Mentions, and Crypto Wallets (**Bitcoin, Ethereum, TON, Solana, TRON/USDT**).
* 👥 **Discussion Comments Scraper**: Scrapes channel post comments directly from linked discussion groups.
* 🛡️ **7 Anti-Censorship Transports**: Full, Abridged, Intermediate, Randomized Intermediate, Obfuscated2, MTProxy (`dd` & Fake-TLS secrets), and HTTP tunnel.
* 🔐 **Standalone Cryptography**: Native MTProto 2.0 AES-IGE with OpenSSL ctypes acceleration and pure Python DER PKCS#1 RSA (Zero external RSA package dependencies).
* 💾 **100% Telethon-Compatible Sessions**: SQLite `.session` files and Base64 `StringSession` (version 1).
* 🔑 **All Auth Modes**: Interactive Phone/SMS/OTP, QR Code Desktop Login, Bot Tokens, and High-Volume Data Takeout sessions.
* 📞 **VoIP & Stories**: Call signalling with Diffie-Hellman key exchange and Telegram Stories scraper/poster.

---

## 📦 Installation

```bash
# Clone and install locally
git clone https://github.com/your-org/telescraper.git
cd telescraper
pip install -e .
```

---

## ⚡ Quick Start

### 1. Basic Scraping & Text Extraction
```python
from telescraper import TeleScraper

# Initialize client
client = TeleScraper("my_session", api_id=123456, api_hash="abcdef0123456789")
client.start(phone="+1234567890")

# Scrape messages sequentially
for msg in client.iter_messages("python_community", limit=100):
    print(f"[{msg.date}] {msg.sender_name}: {msg.text}")
```

### 2. Fast Media Scraping with Server-Side Filters
```python
# Fetches only photo messages directly from Telegram servers (10x faster)
for photo_msg in client.iter_messages("wallpapers", filter_type="photos", limit=50):
    photo_msg.download(output_dir="./wallpapers")
```

### 3. Parallel 4x Media Downloader
```python
messages = client.get_messages("movies_channel", limit=5)
for msg in messages:
    if msg.has_media:
        client.download_parallel(msg, output_dir="./downloads", num_threads=4)
```

### 4. Direct Exports to Excel, SQLite & Pandas
```python
# Direct to Excel
client.export_to_excel("crypto_channel", "crypto_posts.xlsx", limit=1000)

# Direct to SQLite Database
client.export_to_sqlite("crypto_channel", "crypto.db", table_name="messages", limit=1000)

# Direct to Pandas DataFrame
df = client.to_dataframe("crypto_channel", limit=500)
print(df.head())
```

### 5. Automated Crypto Wallet & Entity Extraction
```python
# Extract all crypto wallets and contact info across a channel
entities = client.extract_from_messages("crypto_signals", limit=200)
print("Bitcoin Wallets:", entities["wallets"]["bitcoin"])
print("TON Wallets:", entities["wallets"]["ton"])
print("Emails:", entities["emails"])
```

---

## 📚 Documentation & Comparisons

* 📖 **[Complete Technical Documentation & API Reference](DOCUMENTATION.md)**
* 📊 **[Telethon vs TeleScraper Master Comparison Matrix](COMPARISON_TABLE.md)**

---

## 🧪 Testing

Run all test suites locally:
```bash
uv run python tests/test_basic.py
uv run python tests/test_advanced.py
uv run python tests/test_master_suite.py
```

---

## 📄 License
MIT License.
