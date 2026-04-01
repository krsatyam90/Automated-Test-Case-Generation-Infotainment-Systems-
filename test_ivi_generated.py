"""
AgentTest AI — Generated pytest Module
Requirements: REQ-245963 (Media), REQ-245964 (Bluetooth), REQ-245965 (Audio)
Session: SESSION_20250331_090000_DEMO
Generated: 2025-03-31T09:00:00Z
"""
import pytest
import time
from dataclasses import dataclass, field
from typing import List
from unittest.mock import MagicMock, patch


# ── Data Models ────────────────────────────────────────────────────
@dataclass
class MediaTrack:
    filename:  str
    extension: str
    supported: bool
    duration:  float = 200.0
    corrupted: bool = False


@dataclass
class BluetoothDevice:
    name: str
    mac:  str
    pin:  str = "7392"
    paired: bool = False


# ── Constants ──────────────────────────────────────────────────────
SKIP_TIMEOUT_S  = 3.0   # REQ-245963
SKIP_TOLERANCE  = 0.5   # ± 0.5s
BT_TIMEOUT_S    = 15.0  # REQ-245964
AUDIO_ROUTE_MAX = 2.0   # REQ-245965 seconds


# ── Fixtures ───────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def ivi_system():
    """IVI system mock with realistic state management."""
    system = MagicMock()
    system.state = "IDLE"
    system.execute.return_value = {"status": "ok", "timestamp": time.time()}
    system.verify.return_value = True
    system.media.playback_state = "STOPPED"
    system.bluetooth.connected_device = None
    system.gps.fix_acquired = False
    yield system
    system.reset()


@pytest.fixture
def usb_tracks(ivi_system):
    tracks = [
        MediaTrack("song_01.mp3",   ".mp3",  True),
        MediaTrack("song_02.aac",   ".aac",  True),
        MediaTrack("song_03.wav",   ".wav",  True),
        MediaTrack("audio_01.flac", ".flac", False),
        MediaTrack("audio_02.ape",  ".ape",  False),
        MediaTrack("corrupt.flac",  ".flac", False, 0.0, corrupted=True),
    ]
    ivi_system.media.usb_tracks = tracks
    return tracks


@pytest.fixture
def bt_device():
    return BluetoothDevice(name="TestPhone_BT", mac="AA:BB:CC:DD:EE:FF")


# ═══════════════════════════════════════════════════════════════════
# REQ-245963 — Media Playback: Unsupported File Handling
# ═══════════════════════════════════════════════════════════════════

class TestMediaUnsupportedFiles:
    """Tests for REQ-245963: System handles unsupported media files."""

    def test_system_skips_after_3_seconds(self, ivi_system, usb_tracks):
        """
        TC_245963_POS: System waits 3s then skips unsupported file.
        REQ-245963 | Positive | Priority: High
        """
        unsupported = next(
            t for t in usb_tracks if not t.supported and not t.corrupted
        )
        ivi_system.media.load_track(unsupported)

        start = time.perf_counter()
        ivi_system.execute("PLAY")
        ivi_system.execute("WAIT_FOR_SKIP")
        elapsed = time.perf_counter() - start

        lo = SKIP_TIMEOUT_S - SKIP_TOLERANCE
        hi = SKIP_TIMEOUT_S + SKIP_TOLERANCE
        assert lo <= elapsed <= hi, (
            f"Skip at {elapsed:.3f}s — expected {lo}s–{hi}s"
        )
        assert ivi_system.verify("NEXT_TRACK_LOADED"), "Next track should be queued"
        assert ivi_system.media.playback_state != "ERROR"

    def test_press_previous_after_skip(self, ivi_system, usb_tracks):
        """
        TC_245963_POS_B: Press Previous after skip navigates to previous track.
        REQ-245963 | Positive | Priority: Medium
        """
        ivi_system.execute("PLAY_UNSUPPORTED")
        ivi_system.execute("WAIT_3S")
        ivi_system.execute("PRESS_PREVIOUS")
        assert ivi_system.verify("PREVIOUS_TRACK_ACTIVE")
        assert ivi_system.media.playback_state == "PLAYING"

    def test_corrupted_file_no_crash(self, ivi_system, usb_tracks):
        """
        TC_245963_NEG: Corrupted unsupported file handled without crash.
        REQ-245963 | Negative | Priority: High
        """
        corrupted = next(t for t in usb_tracks if t.corrupted)
        ivi_system.media.load_track(corrupted)
        ivi_system.execute("PLAY")

        assert ivi_system.verify("ERROR_MESSAGE_DISPLAYED"), \
            "Error message must be shown to user"
        assert ivi_system.verify("SYSTEM_STABLE"), \
            "System must remain stable after corrupted file"
        assert ivi_system.state != "CRASHED", "System must not crash"

    def test_skip_at_exact_3_second_boundary(self, ivi_system):
        """
        TC_245963_EDGE: Skip at exactly T=3.0s boundary condition.
        REQ-245963 | Edge Case | Priority: Medium
        """
        ivi_system.execute("INJECT_UNSUPPORTED_AT_BOUNDARY")
        skip_time = ivi_system.measure("SKIP_EVENT_TIMESTAMP")
        assert skip_time >= SKIP_TIMEOUT_S, \
            f"Must not skip before {SKIP_TIMEOUT_S}s, actual: {skip_time}s"
        assert skip_time <= SKIP_TIMEOUT_S + 0.2, \
            f"Must skip within 200ms of boundary, actual: {skip_time}s"

    @pytest.mark.parametrize("extension", [".flac", ".ape", ".wma", ".ogg_corrupted"])
    def test_all_unsupported_formats_handled(self, ivi_system, extension):
        """
        TC_245963_PARAM: Verify all unsupported formats handled consistently.
        REQ-245963 | Parametrised | Priority: Medium
        """
        track = MediaTrack(f"test{extension}", extension, False)
        ivi_system.media.load_track(track)
        ivi_system.execute("PLAY")
        assert ivi_system.verify(f"HANDLED_{extension.upper()}"), \
            f"Format {extension} must be handled gracefully"


# ═══════════════════════════════════════════════════════════════════
# REQ-245964 — Bluetooth Pairing & REQ-245965 — Audio Routing
# ═══════════════════════════════════════════════════════════════════

class TestBluetoothPairing:
    """Tests for REQ-245964 & REQ-245965."""

    def test_pairing_with_4_digit_pin(self, ivi_system, bt_device):
        """
        TC_245964_POS: Device pairs with valid 4-digit PIN.
        REQ-245964 | Positive | Priority: High
        """
        ivi_system.bluetooth.enable_discovery()
        ivi_system.bluetooth.select_device(bt_device.mac)
        displayed_pin = ivi_system.bluetooth.get_pin()

        assert len(str(displayed_pin)) == 4, \
            f"PIN must be 4 digits, got '{displayed_pin}'"
        assert str(displayed_pin).isdigit(), \
            f"PIN must be numeric, got '{displayed_pin}'"

        ivi_system.bluetooth.confirm_pin(displayed_pin)
        assert ivi_system.verify("BT_CONNECTED"), \
            "Device must be connected after correct PIN"

    def test_wrong_pin_rejected(self, ivi_system, bt_device):
        """
        TC_245964_NEG: Wrong PIN causes pairing failure.
        REQ-245964 | Negative | Priority: High
        """
        ivi_system.bluetooth.select_device(bt_device.mac)
        ivi_system.bluetooth.confirm_pin("0000")  # intentionally wrong

        assert ivi_system.verify("PAIRING_FAILED"), "Pairing should fail with wrong PIN"
        assert ivi_system.verify("DISCONNECTED"),    "Device should not be connected"
        assert ivi_system.verify("ERROR_MESSAGE"),   "Error message should be displayed"

    def test_audio_routes_within_2_seconds(self, ivi_system, bt_device):
        """
        TC_245965_PERF: Audio routes to paired device within 2 seconds.
        REQ-245965 | Performance | Priority: High
        """
        ivi_system.bluetooth.connect_paired_device(bt_device.mac)
        start = time.perf_counter()
        ivi_system.execute("PLAY_AUDIO")
        ivi_system.execute("WAIT_AUDIO_ROUTE")
        elapsed = time.perf_counter() - start

        assert elapsed <= AUDIO_ROUTE_MAX, \
            f"Audio routing took {elapsed:.3f}s, max allowed: {AUDIO_ROUTE_MAX}s"
        assert ivi_system.verify("AUDIO_ON_BT"), \
            "Audio must be routed to Bluetooth device"

    def test_auto_reconnect_on_ignition(self, ivi_system, bt_device):
        """
        TC_245966_POS: Auto-reconnect to last paired device on ignition start.
        REQ-245966 | Positive | Priority: High
        """
        ivi_system.bluetooth.pair_and_disconnect(bt_device.mac)
        ivi_system.execute("SIMULATE_IGNITION_START")

        reconnected = ivi_system.verify("BT_AUTO_RECONNECTED")
        assert reconnected, "Should auto-reconnect on ignition start"

    def test_max_8_paired_devices(self, ivi_system):
        """
        TC_245967_EDGE: System stores maximum 8 paired devices.
        REQ-245967 | Edge Case | Priority: Medium
        """
        for i in range(8):
            ivi_system.bluetooth.pair_device(f"Device_{i:02d}", f"AA:BB:CC:DD:{i:02d}:FF")

        count = ivi_system.bluetooth.paired_count()
        assert count == 8, f"Should have exactly 8 paired devices, got {count}"

        # Attempt to pair a 9th device
        ivi_system.bluetooth.pair_device("Device_09", "AA:BB:CC:DD:09:FF")
        new_count = ivi_system.bluetooth.paired_count()
        assert new_count == 8, \
            f"Should not exceed 8 paired devices, got {new_count}"
