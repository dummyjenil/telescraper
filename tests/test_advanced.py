import os
import struct
import tempfile
from datetime import datetime

from telescraper import (
    ChatData,
    ConnectionHttp,
    ConnectionTcpAbridged,
    ConnectionTcpFull,
    ConnectionTcpIntermediate,
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpObfuscated,
    ConnectionTcpRandomizedIntermediate,
    MediaInfo,
    MemberData,
    MessageData,
    ScrapeCheckpoint,
    StringSession,
    SyncSession,
    TeleScraper,
    export_to_csv,
    export_to_excel,
    export_to_json,
    export_to_sqlite,
    extract_data,
    inspect_media_metadata,
    resize_image_sync,
)


def test_transports_instantiation():
    # Test that all transport classes instantiate cleanly with socket parameters
    ip = "149.154.167.50"
    port = 443

    c_full = ConnectionTcpFull(ip, port)
    assert c_full.ip == ip
    assert c_full.port == port

    c_abridged = ConnectionTcpAbridged(ip, port)
    assert c_abridged.ip == ip

    c_inter = ConnectionTcpIntermediate(ip, port)
    assert c_inter.ip == ip

    c_rand = ConnectionTcpRandomizedIntermediate(ip, port)
    assert c_rand.ip == ip

    c_obfs = ConnectionTcpObfuscated(ip, port)
    assert c_obfs.ip == ip

    c_mtproxy = ConnectionTcpMTProxyIntermediate(ip, port, secret="00112233445566778899aabbccddeeff")
    assert c_mtproxy.ip == ip

    c_http = ConnectionHttp(ip, 80)
    assert c_http.ip == ip
    print("[✔] All 7 Transports instantiated cleanly!")


def test_regex_extractor():
    sample_text = """
    Contact us at admin@telegram.org or support@example.com for assistance!
    Call customer support at +1 (555) 234-5678 or +91 9876543210.
    Visit our site https://t.me/durov or https://core.telegram.org/api.
    Check our channel @telegram_news.
    Donations:
    BTC: bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq
    ETH: 0x71C7656EC7ab88b098defB751B7401B5f6d8976F
    TON: EQBvW8m52BQGdXEk6qnWqPT761qO4D0R2zG4N1a0bC2d3e4f
    TRON: TJwN4wFk9N5kX1qR3mZ8vL2yP6sT4aB7cD
    """

    res = extract_data(sample_text)
    assert "admin@telegram.org" in res["emails"]
    assert "support@example.com" in res["emails"]
    assert any("555" in p for p in res["phones"])
    assert "https://t.me/durov" in res["urls"]
    assert "telegram_news" in res["mentions"]
    assert "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq" in res["wallets"]["bitcoin"]
    assert "0x71C7656EC7ab88b098defB751B7401B5f6d8976F" in res["wallets"]["ethereum"]
    assert "EQBvW8m52BQGdXEk6qnWqPT761qO4D0R2zG4N1a0bC2d3e4f" in res["wallets"]["ton"]
    assert "TJwN4wFk9N5kX1qR3mZ8vL2yP6sT4aB7cD" in res["wallets"]["tron"]
    print("[✔] Regex Extractor test passed!")


def test_checkpoint_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        cp_path = os.path.join(tmpdir, "checkpoint.json")
        cp = ScrapeCheckpoint(cp_path)

        assert cp.get_offset("my_channel") == 0
        cp.update("my_channel", 1234)
        assert cp.get_offset("my_channel") == 1234

        # Reload from disk
        cp2 = ScrapeCheckpoint(cp_path)
        assert cp2.get_offset("my_channel") == 1234
        print("[✔] Checkpoint Manager test passed!")


def test_all_exporters():
    with tempfile.TemporaryDirectory() as tmpdir:
        msg = MessageData(
            id=100,
            chat_id=-100999,
            chat_title="Crypto Channel",
            date=datetime.now(),
            text="Bitcoin update today!",
            sender_id=123,
            sender_name="Alice",
            has_media=False,
        )

        json_file = os.path.join(tmpdir, "test.json")
        csv_file = os.path.join(tmpdir, "test.csv")
        excel_file = os.path.join(tmpdir, "test.xlsx")
        sqlite_file = os.path.join(tmpdir, "test.db")

        export_to_json([msg], json_file)
        export_to_csv([msg], csv_file)
        export_to_excel([msg], excel_file)
        export_to_sqlite([msg], sqlite_file)

        assert os.path.exists(json_file)
        assert os.path.exists(csv_file)
        assert os.path.exists(sqlite_file)
        # Excel creates .xlsx or fallback .csv
        assert os.path.exists(excel_file) or os.path.exists(excel_file.replace(".xlsx", ".csv"))
        print("[✔] Advanced Exporters (JSON, CSV, SQLite, Excel) test passed!")


def test_media_utils():
    import io

    from PIL import Image

    img = Image.new("RGB", (10, 10), color="red")
    b = io.BytesIO()
    img.save(b, format="JPEG")
    dummy_bytes = b.getvalue()
    buf, dims = resize_image_sync(dummy_bytes)
    assert buf is not None

    # Test metadata inspector
    meta = inspect_media_metadata("non_existent_file.mp4")
    assert meta["duration"] is None
    print("[✔] Media processing utilities test passed!")


def test_client_transports_configuration():
    # Verify client can be initialized with different transport classes
    client_obfs = TeleScraper(session="obfs_session", api_id=12345, api_hash="hash", connection=ConnectionTcpObfuscated)
    assert client_obfs.connection_class == ConnectionTcpObfuscated

    client_mtp = TeleScraper(
        session="mtp_session",
        api_id=12345,
        api_hash="hash",
        connection=ConnectionTcpMTProxyIntermediate,
        connection_kwargs={"secret": "00112233445566778899aabbccddeeff"},
    )
    assert client_mtp.connection_class == ConnectionTcpMTProxyIntermediate
    print("[✔] TeleScraper Transports configuration test passed!")


if __name__ == "__main__":
    test_transports_instantiation()
    test_regex_extractor()
    test_checkpoint_manager()
    test_all_exporters()
    test_media_utils()
    test_client_transports_configuration()
    print("\n🎉 ALL ADVANCED TESTS PASSED PERFECTLY!")
