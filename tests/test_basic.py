import os
import tempfile
from datetime import datetime

from telescraper import (
    ChatData,
    MediaInfo,
    MemberData,
    MessageData,
    QRLogin,
    SecretChat,
    StringSession,
    SyncSession,
    TakeoutSession,
    TeleScraper,
    export_to_csv,
    export_to_json,
)


def test_string_session():
    # Test blank string session
    s = StringSession()
    assert s.dc_id == 2
    assert s.port == 443
    assert s.save() == ""

    # Test create dummy session with key
    from telescraper.crypto import AuthKey

    dummy_key = AuthKey(data=b"0" * 256)
    s.set_auth_key(dummy_key)
    exported = s.save()
    assert len(exported) > 100
    assert exported.startswith("1")

    # Load from exported string
    s2 = StringSession(exported)
    assert s2.dc_id == 2
    assert s2.server_address == "149.154.167.50"
    assert s2.auth_key.key == dummy_key.key
    print("[✔] StringSession encode/decode test passed!")


def test_models_and_exports():
    with tempfile.TemporaryDirectory() as tmpdir:
        media = MediaInfo(media_type="photo", file_name="img.jpg", file_size=2048)
        msg = MessageData(
            id=42,
            chat_id=-10012345,
            chat_title="My Channel",
            date=datetime.now(),
            text="Test message for telescraper",
            has_media=True,
            media=media,
        )

        json_out = os.path.join(tmpdir, "out.json")
        csv_out = os.path.join(tmpdir, "out.csv")

        export_to_json([msg], json_out)
        export_to_csv([msg], csv_out)

        assert os.path.exists(json_out)
        assert os.path.exists(csv_out)
        print("[✔] Exporters test passed!")


def test_client_init():
    # StringSession init
    client = TeleScraper(session=StringSession(), api_id=12345, api_hash="abcdef")
    assert isinstance(client.session, StringSession)

    # SQLite session init
    client2 = TeleScraper(session="test_sqlite", api_id=12345, api_hash="abcdef")
    assert isinstance(client2.session, SyncSession)
    print("[✔] TeleScraper Client initialization test passed!")


if __name__ == "__main__":
    test_string_session()
    test_models_and_exports()
    test_client_init()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
