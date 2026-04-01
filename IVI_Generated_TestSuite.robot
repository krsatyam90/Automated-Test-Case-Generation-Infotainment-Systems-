*** Settings ***
Documentation    AgentTest AI — Generated IVI Test Suite
...              Requirements: REQ-245963, REQ-245964, REQ-245965
...              Generated: 2025-03-31T09:00:00Z | Session: SESSION_20250331_090000_DEMO
Resource         ${TAF_PATH}/import.resource
Resource         ${TAF_PATH}/project/test/keywords/components/media.resource
Resource         ${TAF_PATH}/project/test/keywords/components/bluetooth.resource
Resource         ${TAF_PATH}/project/test/keywords/components/hmi.resource
Resource         ${TAF_PATH}/project/test/keywords/components/phone.resource
Suite Setup      Initialize IVI System And Verify Ready State
Suite Teardown   Collect All Logs And Shutdown IVI
Test Setup       Reset IVI To Default State
Test Teardown    Run Keywords
...              Capture Screenshot On Failure    AND
...              Log Current System State

*** Variables ***
${IVI_URL}              http://192.168.1.100:8080
${TIMEOUT}              30s
${MEDIA_TIMEOUT}        10s
${BT_TIMEOUT}           15s
${SKIP_WAIT_S}          3
${SCREENSHOT_DIR}       outputs/screenshots
${LOG_DIR}              outputs/logs

*** Test Cases ***

# ═══════════════════════════════════════════════════
# REQ-245963 — Media Playback Unsupported Files
# ═══════════════════════════════════════════════════

TC_245963_POS: Media Playback — Unsupported File Skip After 3s
    [Documentation]    System waits 3s then automatically skips unsupported file
    ...                REQ-245963 | Positive | High Priority
    [Tags]             media    usb    positive    smoke    regression    REQ-245963
    [Setup]            Mount USB With Mixed Files    supported=5    unsupported=3
    prj.test.components.hmi.navigation bar.media.sources : USB
    prj.test.components.media: Launch Source USB
    prj.test.components.media: Open browse in media
    prj.test.components.media: Open Folder from media
    prj.test.components.media: Navigate To Unsupported File    extension=.flac
    prj.test.components.media: Play Song from browser
    ${start_time}=    Get Time    epoch
    Wait Until Keyword Succeeds    5s    500ms    Verify Skip In Progress
    ${elapsed}=    Calculate Elapsed Seconds    ${start_time}
    Should Be True    2.5 <= ${elapsed} <= 3.5
    ...    msg=Skip occurred at ${elapsed}s — expected 3.0s ± 0.5s
    prj.test.components.media: Press Previous after 3s
    Verify Current Track    index=previous
    Verify Playback State    PLAYING
    Capture Screenshot    TC_245963_POS_PASS

TC_245963_NEG: Media Playback — Corrupted File No Crash
    [Documentation]    Corrupted unsupported file handled gracefully without crash
    ...                REQ-245963 | Negative | High Priority
    [Tags]             media    usb    negative    regression    REQ-245963
    prj.test.components.hmi.navigation bar.media.sources : USB
    prj.test.components.media: Launch Source USB
    prj.test.components.media: Open browse in media
    prj.test.components.media: Navigate To Corrupted File
    prj.test.components.media: Attempt Play Corrupted File
    Verify Error Message Displayed    expected=File format not supported
    Verify System State               expected=IDLE
    Verify No System Crash
    Capture Screenshot    TC_245963_NEG_PASS

TC_245963_EDGE: Media Playback — Skip At Exactly 3.0s Boundary
    [Documentation]    Boundary: skip event at T=3.0s exactly
    ...                REQ-245963 | Edge Case | Medium Priority
    [Tags]             media    usb    edge    boundary    REQ-245963
    prj.test.components.media: Play Timed Unsupported File    inject_at_seconds=3.0
    ${skip_time}=    Measure Skip Event Time
    Should Be True    ${skip_time} >= 3.0    msg=Must not skip before 3.0s, actual: ${skip_time}s
    Should Be True    ${skip_time} <= 3.2    msg=Skip must not exceed 3.2s, actual: ${skip_time}s

# ═══════════════════════════════════════════════════
# REQ-245964 — Bluetooth PIN Pairing
# ═══════════════════════════════════════════════════

TC_245964_POS: Bluetooth Pairing — 4-Digit PIN Confirmation
    [Documentation]    BT device pairs successfully with valid 4-digit PIN
    ...                REQ-245964 | Positive | High Priority
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
    [Documentation]    Incorrect PIN causes pairing failure with error message
    ...                REQ-245964 | Negative | High Priority
    [Tags]             bluetooth    pairing    negative    REQ-245964
    prj.test.components.hmi.navigation bar.connectivity : Bluetooth
    prj.test.components.bluetooth: Enable Bluetooth Discovery
    prj.test.components.bluetooth: Select Device For Pairing    ${BT_TEST_DEVICE}
    prj.test.components.phone: Enter Wrong PIN    0000
    Verify Pairing Failed Message    expected=Incorrect PIN
    Verify Connection Status         expected=DISCONNECTED
    Capture Screenshot    TC_245964_NEG_PASS

TC_245964_PERF: Bluetooth Audio — Routes Within 2 Seconds
    [Documentation]    Audio routes to BT device within 2s of connection
    ...                REQ-245965 | Performance | High Priority
    [Tags]             bluetooth    audio    performance    REQ-245965
    prj.test.components.bluetooth: Connect Paired Device    ${BT_TEST_DEVICE_MAC}
    ${start}=    Get Time    epoch
    prj.test.components.media: Play Audio Track
    Wait Until Audio Routes To Device    ${BT_TEST_DEVICE}    timeout=3s
    ${elapsed}=    Calculate Elapsed Seconds    ${start}
    Should Be True    ${elapsed} <= 2.0    msg=Audio routing took ${elapsed}s, max is 2.0s

*** Keywords ***
Initialize IVI System And Verify Ready State
    [Documentation]    Full system boot with readiness verification
    Log    Initializing IVI System...    console=True
    Connect To IVI    host=${IVI_URL}
    Wait Until IVI Ready    timeout=60s
    Verify All Services Running
    Set Screenshot Directory    ${SCREENSHOT_DIR}
    Log    IVI System Ready    console=True

Collect All Logs And Shutdown IVI
    Collect System Logs    destination=${LOG_DIR}
    Generate Test Report
    Disconnect From IVI

Reset IVI To Default State
    Clear Media Queue
    Disable All Active Connections
    Navigate To Home Screen
    Sleep    1s

Capture Screenshot On Failure
    Run Keyword If Test Failed
    ...    Capture Page Screenshot
    ...    ${SCREENSHOT_DIR}/FAIL_${TEST NAME}_${SUITE NAME}.png

Calculate Elapsed Seconds
    [Arguments]    ${start_epoch}
    ${now}=     Get Time    epoch
    ${elapsed}= Evaluate    ${now} - ${start_epoch}
    RETURN    ${elapsed}

Mount USB With Mixed Files
    [Arguments]    ${supported}=5    ${unsupported}=3
    Log    Mounting USB with ${supported} supported + ${unsupported} unsupported files
    Execute IVI Command    mount_usb    supported=${supported}    unsupported=${unsupported}
    Wait Until Element Visible    id=usb-mounted    timeout=5s
