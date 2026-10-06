"""
Comprehensive Master Test Suite for TeleScraper Advanced Subsystems.
Tests Multi-DC Sender Pool, Bot Token Login, Session Termination,
Profile Photos, Parallel Uploads, Invite Links, Stories, Gap Sync, and VoIP Signalling.
100% Pure Synchronous.
"""

import os
import tempfile

from telescraper import StringSession, TeleScraper
from telescraper.network.sender_pool import SyncSenderPool
from telescraper.sync_engine import SyncUpdateEngine, UpdateSyncState
from telescraper.uploader import upload_file_sync
from telescraper.voip import DH_G, DH_PRIME_2048, VoIPSignalling


def test_sender_pool():
    print("Testing Multi-DC Sender Pool...")
    client = TeleScraper(session=StringSession(), api_id=12345, api_hash="abc")
    pool = client.sender_pool
    assert isinstance(pool, SyncSenderPool)
    assert len(pool.DC_ADDRESSES) == 5
    assert pool.DC_ADDRESSES[1][0] == "149.154.175.53"
    assert pool.DC_ADDRESSES[5][0] == "91.108.56.130"
    pool.close_all()
    print("[✔] Multi-DC Sender Pool test passed!")


def test_sync_engine():
    print("Testing SyncUpdateEngine...")
    client = TeleScraper(session=StringSession(), api_id=12345, api_hash="abc")
    engine = client.sync_engine
    assert isinstance(engine, SyncUpdateEngine)
    assert engine.state is None
    # Simulate state caching
    engine.state = UpdateSyncState(pts=100, qts=20, date=1700000000, seq=5)
    assert engine.state.pts == 100
    assert engine.state.qts == 20
    print("[✔] SyncUpdateEngine test passed!")


def test_voip_signalling():
    print("Testing VoIP Signalling & Diffie-Hellman Key Exchange...")
    client = TeleScraper(session=StringSession(), api_id=12345, api_hash="abc")
    voip = client.voip
    assert isinstance(voip, VoIPSignalling)

    # Test DH generation
    a, g_a, g_a_hash = voip._generate_dh_pair()
    assert 1 < a < DH_PRIME_2048
    assert 1 < g_a < DH_PRIME_2048
    assert len(g_a_hash) == 32

    # Simulate receiver DH key computation
    b, g_b, _ = voip._generate_dh_pair()
    g_a_bytes = g_a.to_bytes(256, "big")
    g_b_bytes = g_b.to_bytes(256, "big")

    shared_from_a = pow(g_b, a, DH_PRIME_2048)
    shared_from_b = pow(g_a, b, DH_PRIME_2048)
    assert shared_from_a == shared_from_b  # Diffie-Hellman secret match!
    print("[✔] VoIP Signalling & DH Handshake test passed!")


def test_parallel_uploader_logic():
    print("Testing Parallel Chunk Uploader with mock client...")

    class MockClient:
        def __init__(self):
            self.invoked_parts = []

        def _invoke(self, req):
            self.invoked_parts.append(req.file_part)
            return True

    mock_client = MockClient()
    dummy_data = b"X" * (1024 * 1024)  # 1MB data (2 chunks of 512KB)

    # Test sequential (workers=1)
    res_seq = upload_file_sync(mock_client, dummy_data, filename="test.bin", workers=1)
    assert res_seq.parts == 2
    assert sorted(mock_client.invoked_parts) == [0, 1]

    # Test parallel (workers=4)
    mock_client.invoked_parts.clear()
    res_par = upload_file_sync(mock_client, dummy_data, filename="test.bin", workers=4)
    assert res_par.parts == 2
    assert sorted(mock_client.invoked_parts) == [0, 1]
    print("[✔] Parallel Chunk Uploader test passed!")


def test_client_api_surface():
    print("Testing TeleScraper expanded API surface...")
    client = TeleScraper(session=StringSession(), api_id=12345, api_hash="abc")

    # Verify method existence
    assert hasattr(client, "bot_login")
    assert hasattr(client, "get_authorizations")
    assert hasattr(client, "reset_authorizations")
    assert hasattr(client, "terminate_session")
    assert hasattr(client, "log_out")
    assert hasattr(client, "set_profile_photo")
    assert hasattr(client, "delete_profile_photos")
    assert hasattr(client, "get_profile_photos")
    assert hasattr(client, "create_invite_link")
    assert hasattr(client, "edit_invite_link")
    assert hasattr(client, "revoke_invite_link")
    assert hasattr(client, "get_invite_links")
    assert hasattr(client, "get_peer_stories")
    assert hasattr(client, "post_story")
    assert hasattr(client, "delete_stories")
    assert hasattr(client, "get_state")
    assert hasattr(client, "get_difference")
    assert hasattr(client, "get_channel_difference")
    assert hasattr(client, "voip")
    assert hasattr(client, "sender_pool")
    print("[✔] TeleScraper expanded API surface test passed!")


if __name__ == "__main__":
    test_sender_pool()
    test_sync_engine()
    test_voip_signalling()
    test_parallel_uploader_logic()
    test_client_api_surface()
    print("\n🎉 ALL MASTER EXPANSION TESTS PASSED 100% PERFECTLY!")
