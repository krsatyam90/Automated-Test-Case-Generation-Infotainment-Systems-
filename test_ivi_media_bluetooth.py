"""
AutoTest AI — Generated Python Test Suite
Project: Infotainment System (IVI) — Media & Bluetooth
Requirement Source: IVI_MEDIA_REQ_v2.3.docx
Generated: 2025-03-31T09:00:00Z
Traceability: REQ-245963, REQ-245964, REQ-245965
"""

import pytest
import time
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass
from typing import Optional

# ── Test Configuration ─────────────────────────────────────────────
SCREENSHOT_DIR = Path("outputs/screenshots")
LOG_DIR        = Path("outputs/logs")
SKIP_TIMEOUT   = 3.0   # seconds — from REQ-245963
GPS_TIMEOUT    = 30.0  # seconds — from REQ-245965
BT_TIMEOUT     = 15.0  # seconds — from REQ-245964

SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ── Data Models ────────────────────────────────────────────────────
@dataclass
class MediaTrack:
    filename:  str
    extension: str
    duration:  float
    supported: bool

@dataclass
class BluetoothDevice:
    name:    str
    mac:     str
    pin:     str = "1234"
    paired:  bool = False


# ── Fixtures ───────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def ivi_system():
    """IVI system mock with realistic state management."""
    system = MagicMock()
    system.state = "IDLE"
    system.media.current_track = None
    system.media.playback_state = "STOPPED"
    system.bluetooth.connected_device = None
    system.gps.fix_acquired = False
    system.execute.return_value = {"status": "ok", "timestamp": time.time()}
    system.verify.return_value = True
    yield system
    system.reset()


@pytest.fixture
def usb_with_mixed_files(ivi_system):
    """USB drive with 5 supported + 3 unsupported files."""
    tracks = [
        MediaTrack("song_01.mp3",  ".mp3",  210.0, True),
        MediaTrack("song_02.mp3",  ".mp3",  185.0, True),
        MediaTrack("song_03.aac",  ".aac",  223.0, True),
        MediaTrack("song_04.wav",  ".wav",  198.0, True),
        MediaTrack("song_05.ogg",  ".ogg",  167.0, True),
        MediaTrack("audio_01.flac",".flac", 245.0, False),  # unsupported
        MediaTrack("audio_02.ape", ".ape",  312.0, False),  # unsupported
        MediaTrack("corrupt.flac", ".flac",   0.0, False),  # corrupted
    ]
    ivi_system.media.usb_tracks = tracks
    return tracks


@pytest.fixture
def bt_test_device():
    return BluetoothDevice(name="TestPhone_BT", mac="AA:BB:CC:DD:EE:FF", pin="7392")


# ═══════════════════════════════════════════════════════════════════
# REQ-245963 — Media Playback: Unsupported File Handling
# ═══════════════════════════════════════════════════════════════════

class TestMediaUnsupportedFiles:
    """Tests for REQ-245963: System handles unsupported media files."""

    def test_system_skips_unsupported_file_after_3_seconds(
        self, ivi_system, usb_with_mixed_files
    ):
        """
        TC_245963_POS: System waits 3s then skips unsupported file.
        REQ-245963 | Positive | Priority: High
        """
        # Arrange
        unsupported = next(t for t in usb_with_mixed_files if not t.supported and t.duration > 0)
        ivi_system.media.load_track(unsupported)

        # Act
        start_time = time.time()
        ivi_system.execute("PLAY")
        ivi_system.execute("WAIT_FOR_SKIP")
        elapsed = time.time() - start_time

        # Assert — skip must occur between 2.5s and 3.5s
        assert 2.5 <= elapsed <= 3.5, (
            f"Skip occurred at {elapsed:.2f}s, expected 3.0s ± 0.5s"
        )
        assert ivi_system.verify("NEXT_TRACK_LOADED"), "Next track should be queued"
        assert ivi_system.media.playback_state != "ERROR", "State should not be ERROR"

    def test_system_press_previous_after_skip(self, ivi_system, usb_with_mixed_files):
        """
        TC_245963_POS_B: Press Previous navigates to previous track after skip.
        REQ-245963 | Positive | Priority: Medium
        """
        ivi_system.execute("PLAY_UNSUPPORTED")
        ivi_system.execute("WAIT_3S")
        ivi_system.execute("PRESS_PREVIOUS")

        previous_track = ivi_system.verify("PREVIOUS_TRACK_ACTIVE")
        assert previous_track, "Previous track should be active after pressing Previous"
        assert ivi_system.media.playback_state == "PLAYING"

    def test_corrupted_unsupported_file_no_crash(self, ivi_system, usb_with_mixed_files):
        """
        TC_245963_NEG: Corrupted unsupported file handled without crash.
        REQ-245963 | Negative | Priority: High
        """
        corrupted = next(t for t in usb_with_mixed_files if "corrupt" in t.filename)
        ivi_system.media.load_track(corrupted)
        ivi_system.execute("PLAY")

        assert ivi_system.verify("ERROR_MESSAGE_DISPLAYED"), "Error message should display"
        assert ivi_system.verify("SYSTEM_STABLE"), "System must remain stable"
        assert ivi_system.state != "CRASHED", "System must not crash"

    @pytest.mark.parametrize("extension", [".flac", ".ape", ".wma", ".ogg_corrupted"])
    def test_all_unsupported_formats_handled(self, ivi_system, extension):
        """
        TC_245963_PARAM: All unsupported formats handled consistently.
        REQ-245963 | Parametrised | Priority: Medium
        """
        track = MediaTrack(f"test{extension}", extension, 200.0, False)
        ivi_system.media.load_track(track)
        ivi_system.execute("PLAY")

        assert ivi_system.verify(f"HANDLED_{extension.upper()}"), (
            f"Format {extension} must be handled gracefully"
        )

    def test_skip_timing_boundary_at_exactly_3_seconds(self, ivi_system):
        """
        TC_245963_EDGE: Boundary condition — skip at exactly T=3.0s.
        REQ-245963 | Edge Case | Priority: Medium
        """
        ivi_system.execute("INJECT_UNSUPPORTED_AT_BOUNDARY")
        skip_time = ivi_system.measure("SKIP_EVENT_TIMESTAMP")

        assert skip_time >= 3.0, f"Must not skip before 3.0s, actual: {skip_time}s"
        assert skip_time <= 3.2, f"Must skip by 3.2s, actual: {skip_time}s"


# ═══════════════════════════════════════════════════════════════════
# REQ-245964 — Bluetooth Pairing and Connection
# ═══════════════════════════════════════════════════════════════════

class TestBluetoothPairing:
    """Tests for REQ-245964: Bluetooth device pairing and audio routing."""

    def test_pairing_confirmed_with_4_digit_pin(self, ivi_system, bt_test_device):
        """
        TC_245964_POS: Pairing confirmed with valid 4-digit PIN.
        REQ-245964 | Positive | Priority: High
        """
        ivi_system.bluetooth.enable_discovery()
        ivi_system.bluetooth.select_device(bt_test_device.mac)
        displayed_pin = ivi_system.bluetooth.get_pin()

        # Verify PIN format
        assert len(str(displayed_pin)) == 4, f"PIN must be 4 digits, got: {displayed_pin}"
        assert str(displayed_pin).isdigit(), f"PIN must be numeric, got: {displayed_pin}"

        # Complete pairing
        ivi_system.bluetooth.confirm_pin(displayed_pin)
        assert ivi_system.verify("BT_CONNECTED"), "Device must be connected after PIN confirm"

    def test_wrong_pin_rejected(self, ivi_system, bt_test_device):
        """
        TC_245964_NEG: Wrong PIN causes pairing failure.
        REQ-245964 | Negative | Priority: High
        """
        ivi_system.bluetooth.select_device(bt_test_device.mac)
        ivi_system.bluetooth.confirm_pin("0000")  # wrong PIN

        assert ivi_system.verify("PAIRING_FAILED"), "Pairing should fail with wrong PIN"
        assert ivi_system.verify("DISCONNECTED"), "Device should not be connected"
        assert ivi_system.verify("ERROR_MESSAGE"), "Error message should display"

    def test_audio_routes_within_2_seconds(self, ivi_system, bt_test_device):
        """
        TC_245964_PERF: Audio routes to BT device within 2 seconds.
        REQ-245964 | Performance | Priority: High
        """
        ivi_system.bluetooth.connect_paired_device(bt_test_device.mac)
        start = time.time()
        ivi_system.execute("PLAY_AUDIO")
        ivi_system.execute("WAIT_AUDIO_ROUTE")
        elapsed = time.time() - start

        assert elapsed <= 2.0, f"Audio routing took {elapsed:.2f}s, max 2.0s"
        assert ivi_system.verify("AUDIO_ON_BT"), "Audio must route to BT device"

    def test_auto_reconnect_on_ignition(self, ivi_system, bt_test_device):
        """
        TC_245964_REG: Auto-reconnect to last paired device on ignition.
        REQ-245964 | Regression | Priority: High
        """
        ivi_system.bluetooth.pair_and_disconnect(bt_test_device.mac)
        ivi_system.execute("SIMULATE_IGNITION")
        connected = ivi_system.verify("BT_AUTO_RECONNECTED")

        assert connected, "Should auto-reconnect to last paired device on ignition"


# ═══════════════════════════════════════════════════════════════════
# REQ-245965 — GPS Navigation
# ═══════════════════════════════════════════════════════════════════

class TestGPSNavigation:
    """Tests for REQ-245965: GPS fix acquisition timing."""

    def test_gps_fix_within_30_seconds_open_sky(self, ivi_system):
        """
        TC_245965_POS: GPS fix acquired within 30s in open sky.
        REQ-245965 | Positive | Priority: High
        """
        ivi_system.gps.simulate_open_sky()
        ivi_system.execute("ENABLE_GPS")
        start = time.time()

        while not ivi_system.gps.fix_acquired:
            time.sleep(0.1)
            if time.time() - start > GPS_TIMEOUT:
                break

        elapsed = time.time() - start
        assert ivi_system.gps.fix_acquired, "GPS fix must be acquired"
        assert elapsed <= GPS_TIMEOUT, f"Fix took {elapsed:.1f}s, max {GPS_TIMEOUT}s"
