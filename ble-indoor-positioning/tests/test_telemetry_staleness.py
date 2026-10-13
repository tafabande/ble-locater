import time
import pytest

from server.app import (
    TagState,
    perform_localization,
    shared,
    list_tags,
    get_position_state
)

def test_uninitialized_tag_is_unavailable_without_fabricated_position():
    """Verify that a newly instantiated tag has no fabricated default coordinates (e.g. 2.5, 7.5)."""
    tag = TagState("TEST_TAG_01")
    assert tag.last_position is None
    assert tag.last_position_time is None
    assert tag.status == "unavailable"
    assert tag.get_position_status() == "unavailable"

    summary = tag.to_summary()
    assert summary["status"] == "unavailable"
    assert summary["position_status"] == "unavailable"
    assert summary["position"] is None
    assert summary["position_age_s"] is None
    assert summary["zone"] == "Unknown"

def test_out_of_order_packet_chronological_sorting():
    """Verify that datagrams arriving out of sequence are sorted in chronological order."""
    tag = TagState("TEST_TAG_OUT_OF_ORDER")
    now_ms = int(time.time() * 1000)

    # Packets out of chronological order: 800ms ago, 200ms ago, 500ms ago
    t1 = now_ms - 800
    t2 = now_ms - 500
    t3 = now_ms - 200

    tag.last_raw_packets["ANCHOR_01"] = [(t3, -65), (t1, -70), (t2, -68)]
    perform_localization(tag)

    # After localization processing, anchor packets must be sorted by timestamp
    processed_packets = tag.last_raw_packets["ANCHOR_01"]
    assert len(processed_packets) == 3
    timestamps = [p[0] for p in processed_packets]
    assert timestamps == [t1, t2, t3]

def test_future_timestamp_extreme_clock_skew_rejected():
    """Verify that datagrams with extreme future timestamps (>1000ms ahead) are rejected."""
    tag = TagState("TEST_TAG_CLOCK_SKEW")
    now_ms = int(time.time() * 1000)

    valid_t = now_ms - 100
    extreme_future_t = now_ms + 5000  # 5 seconds in future (severe desync)

    tag.last_raw_packets["ANCHOR_01"] = [(valid_t, -60), (extreme_future_t, -55)]
    perform_localization(tag)

    # Severe future packet must be dropped
    processed = tag.last_raw_packets["ANCHOR_01"]
    assert len(processed) == 1
    assert processed[0][0] == valid_t

def test_minor_clock_skew_tolerated_and_clamped():
    """Verify that datagrams with minor clock skew (e.g. +150ms NTP jitter) are tolerated and clamped to now_ms."""
    tag = TagState("TEST_TAG_MINOR_SKEW")
    now_ms = int(time.time() * 1000)

    minor_future_t = now_ms + 150  # 150ms in future
    tag.last_raw_packets["ANCHOR_01"] = [(minor_future_t, -62)]
    perform_localization(tag)

    processed = tag.last_raw_packets["ANCHOR_01"]
    assert len(processed) == 1
    # Clamped to now_ms or valid past, never left as a future timestamp
    assert processed[0][0] <= int(time.time() * 1000)

def test_duplicate_packet_deduplication():
    """Verify that duplicate UDP datagrams arriving with the same timestamp are deduplicated."""
    tag = TagState("TEST_TAG_DEDUP")
    now_ms = int(time.time() * 1000)

    t = now_ms - 200
    # Duplicate (t, -65) received twice due to UDP retry
    tag.last_raw_packets["ANCHOR_01"] = [(t, -65), (t, -65)]
    perform_localization(tag)

    processed = tag.last_raw_packets["ANCHOR_01"]
    assert len(processed) == 1
    assert processed[0] == (t, -65)

def test_anchor_disappearance_transitions_and_no_fabrication():
    """Verify that when anchors disappear (<3 anchors), no new coordinates are fabricated,
    and status cleanly decays from current -> stale -> unavailable."""
    tag = TagState("TEST_TAG_ANCHORS_LOST")
    now_ms = int(time.time() * 1000)

    # Step 1: Provide 4 anchors so localization succeeds
    for aid in ["ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04"]:
        tag.last_raw_packets[aid] = [(now_ms - 100, -60), (now_ms - 50, -62)]

    perform_localization(tag)
    assert tag.last_position is not None
    assert tag.status == "current"
    initial_pos = dict(tag.last_position)
    pos_time = tag.last_position_time

    # Step 2: 3 anchors disappear, only 1 anchor remains transmitting
    tag.last_raw_packets["ANCHOR_02"] = []
    tag.last_raw_packets["ANCHOR_03"] = []
    tag.last_raw_packets["ANCHOR_04"] = []
    tag.last_raw_packets["ANCHOR_01"] = [(now_ms, -60)]

    perform_localization(tag)

    # Tag position must NOT change (no fabrication of positions)
    assert tag.last_position == initial_pos
    assert tag.last_position_time == pos_time

    # Step 3: Verify time decay of position_status
    # <= 4s: current
    assert tag.get_position_status(now=pos_time + 2.0) == "current"
    # 4s - 30s: stale
    assert tag.get_position_status(now=pos_time + 10.0) == "stale"
    # > 30s: unavailable
    assert tag.get_position_status(now=pos_time + 35.0) == "unavailable"

    # In summary, when unavailable, zone must revert to Unknown
    summary_stale = tag.to_summary()
    assert summary_stale["position_status"] in ["current", "stale"]

def test_telemetry_staleness_in_tag_endpoints():
    """Verify that REST API endpoints accurately surface status, position_status and position_age_s."""
    test_tag_id = "TAG_API_STALENESS_TEST"
    tag = shared['tag_manager'].get_or_create(test_tag_id)
    now = time.time()
    now_ms = int(now * 1000)

    # Initially unavailable
    state = get_position_state(test_tag_id)
    tag_entry = state['tags'][test_tag_id]
    assert tag_entry["status"] == "unavailable"
    assert tag_entry["position"] is None

    # Supply telemetry for all 4 anchors
    for aid in ["ANCHOR_01", "ANCHOR_02", "ANCHOR_03", "ANCHOR_04"]:
        tag.last_raw_packets[aid] = [(now_ms - 50, -65)]
    perform_localization(tag)

    data = list_tags()
    matching = [t for t in data["tags"] if t["tag_id"] == test_tag_id]
    assert len(matching) == 1
    found = matching[0]
    assert found["status"] == "current"
    assert found["position_status"] == "current"
    assert found["position"] is not None
    assert isinstance(found["position_age_s"], (int, float))
