"""
app.py — AgentTest AI — Main Application
Agentic QA: Requirement → Plan → Manual → Automation → Execute → Report
Run: python app.py
URL: http://localhost:7860
"""
from __future__ import annotations
import asyncio, json, time
from datetime import datetime
from pathlib import Path
import gradio as gr

_orchestrator = None

def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from agents.orchestrator import AgentTestOrchestrator
        _orchestrator = AgentTestOrchestrator()
    return _orchestrator


EXAMPLES = {
    "Bluetooth + Media (IVI)": """Feature: Infotainment Media & Bluetooth
Project: IVI System v5.3 | Domain: Media / Bluetooth

REQ-245963: The system shall wait exactly 3 seconds then automatically skip any unsupported media file format. The skip behaviour shall not crash or freeze the system.

REQ-245964: When a Bluetooth device initiates pairing, a 4-digit numeric PIN shall be displayed on the IVI screen for user confirmation.

REQ-245965: Audio shall route to a paired Bluetooth device within 2 seconds of connection establishment.

REQ-245966: On ignition start, the system shall auto-reconnect to the last successfully paired Bluetooth device within 10 seconds.

REQ-245967: The IVI system shall store a maximum of 8 paired Bluetooth devices in non-volatile memory.""",

    "Navigation GPS": """Feature: Navigation and GPS
Domain: Navigation

REQ-246001: GPS fix shall be acquired within 30 seconds in open sky conditions.
REQ-246002: Route recalculation shall occur within 5 seconds after a missed turn.
REQ-246003: Speed limit display shall update within 1 second of crossing a zone boundary.
REQ-246004: System shall provide turn-by-turn guidance using offline maps when cellular is unavailable.""",

    "Voice Control": """Feature: Voice Command Interface
Domain: VoiceControl

REQ-247001: The wake word "Hey Car" shall activate the voice system within 500 milliseconds.
REQ-247002: Voice command recognition accuracy shall be at least 95% in normal cabin noise (65dB).
REQ-247003: System shall provide audio confirmation within 1 second for every executed command.
REQ-247004: Unsupported commands shall trigger a helpful suggestion response, not silence or an error tone.
REQ-247005: Voice control shall remain fully operational when the touchscreen is disabled or unresponsive.""",
}


def run_pipeline(req_text: str, progress=gr.Progress()):
    if not req_text.strip():
        return ("⚠️ Please enter requirement text.", "", "", "", "", "", None, None, None, {})

    log_lines = []

    def log(msg: str) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        log_lines.append(f"[{ts}] {msg}")
        return "\n".join(log_lines)

    stages = [
        (0.05, "🔍 Parsing stakeholder requirements..."),
        (0.18, "📋 Creating test plan and coverage matrix..."),
        (0.34, "📝 Generating manual test cases (positive / negative / edge)..."),
        (0.54, "⚙️  Generating automation — Robot · Python · Selenium · JSON (parallel)..."),
        (0.72, "▶️  Executing tests and capturing results / screenshots..."),
        (0.88, "📊 Generating PDF + HTML + Markdown reports..."),
    ]

    for pct, msg in stages:
        progress(pct, desc=msg)
        log(msg)
        time.sleep(0.2)

    try:
        orchestrator = _get_orchestrator()
        state = asyncio.run(orchestrator.run(req_text))
    except Exception as e:
        log(f"⚠️  API not configured — showing demo outputs ({e})")
        state = _demo_state(req_text)

    progress(1.0, desc="✅ Pipeline complete!")

    session_id = state["session_id"]
    manual     = state.get("manual_tests", [])
    robot_code = "\n\n".join(state.get("robot_tests", [DEMO_ROBOT]))
    python_code= "\n\n".join(state.get("python_tests", [DEMO_PYTHON]))
    sel_code   = "\n\n".join(state.get("selenium_tests", [DEMO_SELENIUM]))
    json_coords= json.dumps(state.get("json_coordinates", DEMO_JSON), indent=2)
    exec_sm    = state.get("execution_results", {}).get("summary", {})
    report_path= state.get("report_path", "")

    stats = {
        "session_id":   session_id,
        "requirements": len(state.get("parsed_reqs", [])),
        "manual_tests": len(manual),
        "executed":     exec_sm.get("total", 0),
        "passed":       exec_sm.get("passed", 0),
        "failed":       exec_sm.get("failed", 0),
        "pass_rate":    f"{exec_sm.get('pass_rate', 0)}%",
        "report":       report_path or "outputs/report.pdf",
    }

    final_log = "\n".join(log_lines + [
        "", "=" * 55,
        f"Session      : {session_id}",
        f"Requirements : {len(state.get('parsed_reqs',[]))}",
        f"Manual TCs   : {len(manual)}",
        f"Executed     : {exec_sm.get('total',0)}",
        f"Passed       : {exec_sm.get('passed',0)}",
        f"Failed       : {exec_sm.get('failed',0)}",
        f"Pass Rate    : {exec_sm.get('pass_rate',0)}%",
        f"Report       : {report_path or 'outputs/report.pdf'}",
        "=" * 55,
    ])

    pdf_file  = report_path if report_path and Path(report_path).exists() else None
    html_file = (str(Path(report_path).parent / "test_report.html")
                 if report_path and Path(report_path).parent.exists() else None)
    md_file   = (str(Path(report_path).parent / "test_report.md")
                 if report_path and Path(report_path).parent.exists() else None)

    manual_md = _manual_to_md(manual)

    return (final_log, manual_md, robot_code, python_code,
            sel_code, json_coords,
            pdf_file if pdf_file and Path(pdf_file).exists() else None,
            html_file if html_file and Path(html_file).exists() else None,
            md_file if md_file and Path(md_file).exists() else None,
            stats)


def _manual_to_md(tests: list) -> str:
    if not tests:
        return "# Manual Test Cases\n\nGenerating..."
    lines = [f"# Manual Test Cases — {len(tests)} generated\n"]
    for tc in tests:
        lines += [
            f"## {tc.get('id','TC')} — {tc.get('title','')}",
            f"**Type:** `{tc.get('type','')}` | **Priority:** `{tc.get('priority','')}` "
            f"| **Est:** {tc.get('estimated_time_min',5)} min\n",
            "**Preconditions:**",
        ]
        for p in tc.get("preconditions", []):
            lines.append(f"- {p}")
        lines.append("\n**Test Steps:**")
        for i, s in enumerate(tc.get("steps", []), 1):
            lines.append(f"{i}. {s}")
        lines.append("\n**Expected Results:**")
        for e in tc.get("expected_results", tc.get("expected", [])):
            lines.append(f"✓ {e}")
        lines.append("\n---\n")
    return "\n".join(lines)


def _demo_state(req_text: str) -> dict:
    """Realistic demo when API key not configured."""
    sid = f"SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}_DEMO"
    return {
        "session_id": sid,
        "parsed_reqs": [
            {"id":"REQ-245963","title":"Unsupported File Skip","priority":"High","domain":"Media"},
            {"id":"REQ-245964","title":"Bluetooth PIN Pairing","priority":"High","domain":"Bluetooth"},
            {"id":"REQ-245965","title":"Audio Routing Timing","priority":"High","domain":"Bluetooth"},
        ],
        "test_plan": {"test_plan_id":"TP-DEMO","risk_areas":["Timing","BT pairing"]},
        "manual_tests": [
            {"id":"TC_245963_POS","req_id":"REQ-245963",
             "title":"System skips unsupported file after 3 seconds",
             "type":"positive","priority":"High","estimated_time_min":5,
             "preconditions":["USB with .flac files mounted","System in Media mode"],
             "steps":["Navigate to Media → USB","Open file browser",
                      "Select unsupported .flac file","Press Play",
                      "Wait 3 seconds","Observe skip behaviour"],
             "expected_results":["File skips at T=3.0s ± 0.5s",
                                  "Next supported track begins playing",
                                  "No system freeze or crash"],
             "status":"NOT_RUN"},
            {"id":"TC_245963_NEG","req_id":"REQ-245963",
             "title":"Corrupted unsupported file handled gracefully",
             "type":"negative","priority":"High","estimated_time_min":5,
             "preconditions":["Corrupted .flac file (0 bytes) on USB"],
             "steps":["Select corrupted file","Press Play","Observe system response"],
             "expected_results":["Error message displayed within 2s",
                                  "System remains in IDLE state","No crash or reboot"],
             "status":"NOT_RUN"},
            {"id":"TC_245963_EDGE","req_id":"REQ-245963",
             "title":"Skip at exactly 3.0-second boundary",
             "type":"edge","priority":"Medium","estimated_time_min":8,
             "preconditions":["Precise timing test environment","Signal injection at T=3.0s"],
             "steps":["Play unsupported file with injection at T=9.9s",
                      "Measure skip event timestamp"],
             "expected_results":["Skip at T >= 3.0s","Skip at T <= 3.2s"],
             "status":"NOT_RUN"},
            {"id":"TC_245964_POS","req_id":"REQ-245964",
             "title":"Bluetooth pairing confirmed with 4-digit PIN",
             "type":"positive","priority":"High","estimated_time_min":8,
             "preconditions":["BT device in discoverable mode","IVI BT enabled"],
             "steps":["Enable BT discovery","Select test device from list",
                      "Observe PIN on IVI screen","Verify PIN format","Confirm pairing"],
             "expected_results":["4-digit numeric PIN displayed",
                                  "PIN matches ^[0-9]{4}$","Device status: CONNECTED"],
             "status":"NOT_RUN"},
        ],
        "robot_tests":    [DEMO_ROBOT],
        "python_tests":   [DEMO_PYTHON],
        "selenium_tests": [DEMO_SELENIUM],
        "json_coordinates": DEMO_JSON,
        "execution_results": {
            "summary": {"total":12,"passed":10,"failed":2,"skipped":0,"pass_rate":83.3}
        },
        "report_path": "",
    }


# ── Demo code outputs ─────────────────────────────────────────────
DEMO_ROBOT = '''*** Settings ***
Documentation    AgentTest AI — Generated Robot Framework Suite
...              REQ-245963, REQ-245964, REQ-245965
Resource         ${TAF_PATH}/import.resource
Resource         ${TAF_PATH}/project/test/keywords/components/media.resource
Resource         ${TAF_PATH}/project/test/keywords/components/bluetooth.resource
Resource         ${TAF_PATH}/project/test/keywords/components/hmi.resource
Suite Setup      Initialize IVI System And Verify Ready State
Suite Teardown   Collect All Logs And Shutdown IVI
Test Teardown    Capture Screenshot On Failure

*** Variables ***
${IVI_URL}          http://192.168.1.100:8080
${TIMEOUT}          30s
${MEDIA_TIMEOUT}    10s
${SKIP_WAIT_S}      3
${BT_TIMEOUT}       15s

*** Test Cases ***
TC_245963_POS: Media Playback — Unsupported File Skip After 3s
    [Documentation]    System waits 3s then skips unsupported file | REQ-245963
    [Tags]             media    usb    positive    smoke    REQ-245963
    [Setup]            Mount USB With Mixed Files    supported=5    unsupported=3
    prj.test.components.hmi.navigation bar.media.sources : USB
    prj.test.components.media: Launch Source USB
    prj.test.components.media: Open browse in media
    prj.test.components.media: Open Folder from media
    prj.test.components.media: Navigate To Unsupported File    extension=.flac
    prj.test.components.media: Play Song from browser
    ${start}=    Get Time    epoch
    Wait Until Keyword Succeeds    5s    500ms    Verify Skip In Progress
    ${elapsed}=    Calculate Elapsed Seconds    ${start}
    Should Be True    2.5 <= ${elapsed} <= 3.5
    ...    msg=Skip at ${elapsed}s — expected 3.0s ± 0.5s
    prj.test.components.media: Press Previous after 3s
    Verify Playback State    PLAYING
    Capture Screenshot    TC_245963_POS_PASS

TC_245963_NEG: Media Playback — Corrupted File No Crash
    [Documentation]    Corrupted unsupported file handled without crash | REQ-245963
    [Tags]             media    usb    negative    REQ-245963
    prj.test.components.media: Navigate To Corrupted File
    prj.test.components.media: Attempt Play Corrupted File
    Verify Error Message Displayed    expected=File format not supported
    Verify System State               expected=IDLE
    Verify No System Crash
    Capture Screenshot    TC_245963_NEG_PASS

TC_245963_EDGE: Media Playback — Skip At Exactly 3.0s Boundary
    [Documentation]    Boundary condition — skip event at T=3.0s | REQ-245963
    [Tags]             media    usb    edge    boundary    REQ-245963
    prj.test.components.media: Play Timed Unsupported File    inject_at_seconds=3.0
    ${skip_time}=    Measure Skip Event Time
    Should Be True    ${skip_time} >= 3.0    msg=Must not skip before 3.0s
    Should Be True    ${skip_time} <= 3.2    msg=Skip must not exceed 3.2s

TC_245964_POS: Bluetooth Pairing — 4-Digit PIN Confirmation
    [Documentation]    Device pairs with valid 4-digit PIN | REQ-245964
    [Tags]             bluetooth    pairing    positive    smoke    REQ-245964
    prj.test.components.hmi.navigation bar.connectivity : Bluetooth
    prj.test.components.bluetooth: Enable Bluetooth Discovery
    prj.test.components.bluetooth: Wait For Device In List    ${BT_TEST_DEVICE}    timeout=${BT_TIMEOUT}
    prj.test.components.bluetooth: Select Device For Pairing    ${BT_TEST_DEVICE}
    ${pin}=    prj.test.components.bluetooth: Get Displayed PIN
    Should Match Regexp    ${pin}    ^[0-9]{4}$    msg=PIN must be 4 numeric digits, got: ${pin}
    prj.test.components.phone: Confirm Pairing PIN    ${pin}
    prj.test.components.bluetooth: Verify Connection Status    CONNECTED
    Capture Screenshot    TC_245964_POS_PASS

TC_245964_NEG: Bluetooth Pairing — Wrong PIN Rejected
    [Documentation]    Incorrect PIN causes pairing failure | REQ-245964
    [Tags]             bluetooth    pairing    negative    REQ-245964
    prj.test.components.bluetooth: Select Device For Pairing    ${BT_TEST_DEVICE}
    prj.test.components.phone: Enter Wrong PIN    0000
    Verify Pairing Failed Message    expected=Incorrect PIN
    Verify Connection Status         expected=DISCONNECTED

*** Keywords ***
Initialize IVI System And Verify Ready State
    Log    Initializing IVI System...    console=True
    Connect To IVI    host=${IVI_URL}
    Wait Until IVI Ready    timeout=60s
    Set Screenshot Directory    outputs/screenshots

Collect All Logs And Shutdown IVI
    Collect System Logs    destination=outputs/logs
    Disconnect From IVI

Capture Screenshot On Failure
    Run Keyword If Test Failed
    ...    Capture Page Screenshot
    ...    outputs/screenshots/FAIL_${TEST NAME}_${SUITE NAME}.png

Calculate Elapsed Seconds
    [Arguments]    ${start_epoch}
    ${now}=    Get Time    epoch
    ${elapsed}=    Evaluate    ${now} - ${start_epoch}
    RETURN    ${elapsed}'''

DEMO_PYTHON = '''"""
AgentTest AI — Generated pytest Module
Requirements: REQ-245963, REQ-245964, REQ-245965
"""
import pytest
import time
from unittest.mock import MagicMock
from dataclasses import dataclass


@dataclass
class MediaTrack:
    filename: str
    extension: str
    supported: bool
    duration: float = 200.0


@pytest.fixture(scope="module")
def ivi_system():
    """IVI system mock with realistic state management."""
    system = MagicMock()
    system.state = "IDLE"
    system.execute.return_value = {"status": "ok"}
    system.verify.return_value = True
    system.media.playback_state = "STOPPED"
    yield system
    system.reset()


@pytest.fixture
def usb_tracks(ivi_system):
    tracks = [
        MediaTrack("song_01.mp3",   ".mp3",  True),
        MediaTrack("song_02.aac",   ".aac",  True),
        MediaTrack("audio_01.flac", ".flac", False),
        MediaTrack("corrupt.flac",  ".flac", False, 0.0),
    ]
    ivi_system.media.usb_tracks = tracks
    return tracks


class TestMediaUnsupportedFiles:
    """REQ-245963 — Unsupported file handling."""

    def test_skips_after_3_seconds(self, ivi_system, usb_tracks):
        """TC_245963_POS: System skips unsupported file at T=3.0s ± 0.5s."""
        bad = next(t for t in usb_tracks if not t.supported and t.duration > 0)
        ivi_system.media.load_track(bad)
        start = time.perf_counter()
        ivi_system.execute("PLAY")
        ivi_system.execute("WAIT_FOR_SKIP")
        elapsed = time.perf_counter() - start
        assert 2.5 <= elapsed <= 3.5, f"Skip at {elapsed:.2f}s, expected 3.0s ± 0.5s"
        assert ivi_system.verify("NEXT_TRACK_LOADED"), "Next track should be queued"
        assert ivi_system.media.playback_state != "ERROR"

    def test_previous_after_skip(self, ivi_system, usb_tracks):
        """TC_245963_POS_B: Previous navigates back after auto-skip."""
        ivi_system.execute("PLAY_UNSUPPORTED")
        ivi_system.execute("WAIT_3S")
        ivi_system.execute("PRESS_PREVIOUS")
        assert ivi_system.verify("PREVIOUS_TRACK_ACTIVE")
        assert ivi_system.media.playback_state == "PLAYING"

    def test_corrupted_file_no_crash(self, ivi_system, usb_tracks):
        """TC_245963_NEG: Corrupted file handled without crash."""
        corrupt = next(t for t in usb_tracks if "corrupt" in t.filename)
        ivi_system.media.load_track(corrupt)
        ivi_system.execute("PLAY")
        assert ivi_system.verify("ERROR_MESSAGE_DISPLAYED")
        assert ivi_system.verify("SYSTEM_STABLE")
        assert ivi_system.state != "CRASHED"

    def test_skip_at_3_second_boundary(self, ivi_system):
        """TC_245963_EDGE: Boundary condition — skip at exactly T=3.0s."""
        ivi_system.execute("INJECT_UNSUPPORTED_AT_BOUNDARY")
        skip_time = ivi_system.measure("SKIP_EVENT_TIMESTAMP")
        assert skip_time >= 3.0, f"Must not skip before 3.0s, actual: {skip_time}s"
        assert skip_time <= 3.2, f"Must skip by 3.2s, actual: {skip_time}s"

    @pytest.mark.parametrize("ext", [".flac", ".ape", ".wma"])
    def test_all_unsupported_formats(self, ivi_system, ext):
        """TC_245963_PARAM: All unsupported formats handled."""
        track = MediaTrack(f"test{ext}", ext, False)
        ivi_system.media.load_track(track)
        ivi_system.execute("PLAY")
        assert ivi_system.verify(f"HANDLED_{ext.upper()}")


class TestBluetoothPairing:
    """REQ-245964 — Bluetooth PIN pairing."""

    def test_pairing_with_4_digit_pin(self, ivi_system):
        """TC_245964_POS: 4-digit numeric PIN displayed and confirmed."""
        ivi_system.bluetooth.enable_discovery()
        ivi_system.bluetooth.select_device("TestPhone_BT")
        pin = ivi_system.bluetooth.get_pin()
        assert len(str(pin)) == 4, f"PIN must be 4 digits, got: {pin}"
        assert str(pin).isdigit(), f"PIN must be numeric, got: {pin}"
        ivi_system.bluetooth.confirm_pin(pin)
        assert ivi_system.verify("BT_CONNECTED")

    def test_wrong_pin_rejected(self, ivi_system):
        """TC_245964_NEG: Wrong PIN causes pairing failure."""
        ivi_system.bluetooth.select_device("TestPhone_BT")
        ivi_system.bluetooth.confirm_pin("0000")
        assert ivi_system.verify("PAIRING_FAILED")
        assert ivi_system.verify("DISCONNECTED")

    def test_audio_routes_within_2_seconds(self, ivi_system):
        """TC_245965_PERF: Audio routes to BT device within 2 seconds."""
        ivi_system.bluetooth.connect_paired_device("AA:BB:CC:DD:EE:FF")
        start = time.perf_counter()
        ivi_system.execute("PLAY_AUDIO")
        ivi_system.execute("WAIT_AUDIO_ROUTE")
        elapsed = time.perf_counter() - start
        assert elapsed <= 2.0, f"Audio routing took {elapsed:.2f}s, max 2.0s"
        assert ivi_system.verify("AUDIO_ON_BT")'''

DEMO_SELENIUM = '''"""
AgentTest AI — Selenium WebDriver Scripts
IVI HMI Automation | Selenium 4 + Page Object Model
"""
import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

IVI_URL = "http://192.168.1.100:8080"


@pytest.fixture(scope="module")
def driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(5)
    drv.get(IVI_URL)
    yield drv
    drv.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.failed and "driver" in item.funcargs:
        drv = item.funcargs["driver"]
        drv.save_screenshot(
            f"outputs/screenshots/FAIL_{item.name}_{int(time.time())}.png"
        )


class IVIMediaPage:
    """Page Object: Media screen."""
    def __init__(self, driver):
        self.driver = driver
        self.wait   = WebDriverWait(driver, 30)

    def navigate_to_usb(self):
        btn = self.wait.until(EC.element_to_be_clickable((By.ID, "nav-media")))
        btn.click()
        usb = self.wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "[data-source='usb']")))
        usb.click()

    def open_browser(self):
        self.wait.until(EC.element_to_be_clickable((By.ID, "browse-btn"))).click()

    def select_file_by_extension(self, ext: str):
        item = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//div[@class='track-item'][contains(@data-ext,\'{ext}\')]")))
        item.click()

    def press_play(self):
        self.wait.until(EC.element_to_be_clickable((By.ID, "play-btn"))).click()

    def get_playback_state(self) -> str:
        el = self.wait.until(EC.presence_of_element_located((By.ID, "playback-state")))
        return el.get_attribute("data-state")


class IVIBluetoothPage:
    """Page Object: Bluetooth screen."""
    def __init__(self, driver):
        self.driver = driver
        self.wait   = WebDriverWait(driver, 30)

    def navigate_to_bluetooth(self):
        self.wait.until(EC.element_to_be_clickable((By.ID, "nav-bt"))).click()

    def enable_discovery(self):
        toggle = self.wait.until(EC.element_to_be_clickable((By.ID, "bt-discovery-toggle")))
        toggle.click()
        self.wait.until(EC.visibility_of_element_located((By.ID, "bt-scanning")))

    def select_device(self, device_name: str):
        device = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//div[@class='bt-device-item'][contains(text(),\'{device_name}\')]")))
        device.click()

    def get_pin(self) -> str:
        pin_el = self.wait.until(EC.visibility_of_element_located((By.ID, "pairing-pin")))
        return pin_el.text.strip()


def test_media_unsupported_file_skip(driver):
    """TC_245963_POS: Unsupported file skips at T=3.0s ± 0.5s."""
    page = IVIMediaPage(driver)
    page.navigate_to_usb()
    page.open_browser()
    page.select_file_by_extension(".flac")
    page.press_play()

    start = time.perf_counter()
    wait  = WebDriverWait(driver, 5)
    skip_indicator = wait.until(
        EC.visibility_of_element_located((By.ID, "skip-indicator")))
    elapsed = time.perf_counter() - start

    assert elapsed <= 3.5, f"Skip too slow: {elapsed:.2f}s (max 3.5s)"
    assert elapsed >= 2.5, f"Skip too fast: {elapsed:.2f}s (min 2.5s)"
    assert skip_indicator.is_displayed()


def test_bluetooth_pin_format(driver):
    """TC_245964_POS: Displayed PIN is 4 numeric digits."""
    page = IVIBluetoothPage(driver)
    page.navigate_to_bluetooth()
    page.enable_discovery()
    page.select_device("TestPhone_BT")
    pin = page.get_pin()
    assert len(pin) == 4,      f"PIN length {len(pin)}, expected 4"
    assert pin.isdigit(),       f"PIN '{pin}' contains non-numeric characters"'''

DEMO_JSON = {
    "metadata": {
        "generated_by": "AgentTest AI v2.1",
        "resolution": "1280x720",
        "touch_unit": "pixels",
        "screenshot_convention": "FAIL_{TC_ID}_{STEP}_{TIMESTAMP}.png",
        "log_convention": "{TC_ID}_{DATE}.log",
    },
    "ui_elements": {
        "nav_media":     {"x": 120, "y": 680, "width": 80,  "height": 40, "action": "TAP"},
        "nav_bluetooth": {"x": 220, "y": 680, "width": 80,  "height": 40, "action": "TAP"},
        "usb_source":    {"x": 200, "y": 150, "width": 160, "height": 60, "action": "TAP"},
        "browse_btn":    {"x": 640, "y": 150, "width": 120, "height": 50, "action": "TAP"},
        "play_btn":      {"x": 640, "y": 500, "width": 80,  "height": 80, "action": "TAP"},
        "previous_btn":  {"x": 480, "y": 500, "width": 80,  "height": 80, "action": "TAP"},
        "bt_discovery":  {"x": 1100,"y": 120, "width": 80,  "height": 40, "action": "TAP"},
        "pin_display":   {"x": 640, "y": 380, "width": 200, "height": 50, "action": "CAPTURE_TEXT"},
    },
    "test_sequences": {
        "TC_245963_POS": {
            "steps": [
                {"step": 1, "action": "TAP", "element": "nav_media",
                 "coordinates": {"x": 120, "y": 680},
                 "expected_state": "MEDIA_SCREEN_VISIBLE",
                 "screenshot": "TC_245963_POS_step01.png"},
                {"step": 2, "action": "TAP", "element": "usb_source",
                 "coordinates": {"x": 200, "y": 150},
                 "expected_state": "USB_SOURCE_ACTIVE",
                 "screenshot": "TC_245963_POS_step02.png"},
                {"step": 5, "action": "TAP", "element": "play_btn",
                 "coordinates": {"x": 640, "y": 500},
                 "expected_state": "PLAYBACK_STARTED",
                 "screenshot": "TC_245963_POS_step05.png"},
                {"step": 6, "action": "WAIT", "duration_ms": 3000,
                 "assertion": "elapsed BETWEEN 2500ms AND 3500ms",
                 "expected_state": "SKIP_IN_PROGRESS",
                 "screenshot": "TC_245963_POS_step06.png"},
            ],
            "assertions": [
                {"field": "skip_timing", "operator": "BETWEEN", "min": 2.5, "max": 3.5, "unit": "s"},
                {"field": "system_state", "operator": "EQUALS", "expected": "PLAYING"},
            ],
        },
    },
}


# ── Gradio UI ─────────────────────────────────────────────────────
with gr.Blocks(
    title="AgentTest AI — Agentic QA System",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    css=".agent-log{font-family:'SF Mono',Consolas,monospace!important;font-size:12px!important}",
) as demo:

    gr.HTML("""
    <div style="text-align:center;padding:1.5rem 0 .5rem">
      <h1 style="font-size:1.9rem;font-weight:700;margin-bottom:.3rem">
        🤖 AgentTest AI
      </h1>
      <p style="color:#64748b;font-size:1rem;max-width:640px;margin:0 auto">
        Agentic QA — from stakeholder requirement to full test report in one click.
        Generates manual tests, Robot Framework, pytest, Selenium, JSON coordinates,
        executes them, and produces PDF + HTML + Markdown reports automatically.
      </p>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Settings")
            domain_dd = gr.Dropdown(
                choices=["Infotainment (IVI)","ADAS","Body Control","Powertrain","Generic"],
                value="Infotainment (IVI)", label="Automotive Domain",
            )
            test_levels = gr.CheckboxGroup(
                choices=["Manual","Unit","Integration","System","Regression"],
                value=["Manual","Unit","System"], label="Test Levels to Generate",
            )
            run_exec  = gr.Checkbox(value=True, label="Execute tests after generation")
            gen_report= gr.Checkbox(value=True, label="Generate PDF + HTML + MD report")
            gr.Markdown("### 📂 Load Example")
            example_dd = gr.Dropdown(
                choices=list(EXAMPLES.keys()), label="Example Requirement",
            )
            load_btn = gr.Button("Load Example →", variant="secondary", size="sm")

        with gr.Column(scale=2):
            gr.Markdown("### 📋 Stakeholder Requirements")
            req_input = gr.Textbox(
                lines=15,
                placeholder=(
                    "Paste your stakeholder requirement here...\n\n"
                    "Example:\n"
                    "Feature: Bluetooth Audio\n"
                    "REQ-001: Device must appear in available list within 10 seconds\n"
                    "REQ-002: Audio must route to BT device within 2 seconds\n"
                    "REQ-003: System shall auto-reconnect on ignition start\n"
                ),
                label="",
            )
            run_btn = gr.Button(
                "🚀 Run Full Agentic Pipeline",
                variant="primary", size="lg",
            )

    gr.Markdown("---")

    with gr.Row():
        stats_out = gr.JSON(label="📊 Pipeline Results")
        agent_log = gr.Textbox(
            label="🖥️ Agent Activity Log",
            lines=10, elem_classes=["agent-log"],
        )

    with gr.Tabs():
        with gr.Tab("📝 Manual Test Cases"):
            manual_out = gr.Markdown()
        with gr.Tab("🤖 Robot Framework"):
            robot_out  = gr.Code(language="robotframework",
                                  label="Generated .robot file")
        with gr.Tab("🐍 Python pytest"):
            python_out = gr.Code(language="python",
                                  label="Generated pytest module")
        with gr.Tab("🌐 Selenium"):
            selenium_out = gr.Code(language="python",
                                    label="Generated Selenium script")
        with gr.Tab("📌 JSON Coordinates"):
            json_out = gr.Code(language="json",
                                label="UI Action Map + Coordinates")

    gr.Markdown("### 📥 Download Reports")
    with gr.Row():
        pdf_dl  = gr.File(label="PDF Report")
        html_dl = gr.File(label="HTML Report")
        md_dl   = gr.File(label="Markdown Report")

    load_btn.click(
        fn=lambda x: EXAMPLES.get(x, ""),
        inputs=example_dd, outputs=req_input,
    )
    run_btn.click(
        fn=run_pipeline,
        inputs=[req_input],
        outputs=[agent_log, manual_out, robot_out, python_out,
                 selenium_out, json_out, pdf_dl, html_dl, md_dl, stats_out],
    )

    gr.HTML("""
    <p style="text-align:center;color:#94a3b8;font-size:11px;padding:1.5rem 0">
      AgentTest AI · GPT-4o · LangGraph · Gradio 4 · Robot Framework 7 · Selenium 4 · pytest 8
    </p>
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
