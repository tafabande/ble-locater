import pytest
import asyncio
from server.app import (
    serve_index,
    get_control_status,
    handle_control_action, ControlAction,
    get_schematic, save_schematic, SchematicPayload,
    get_training_status, reload_models, cancel_training_run,
    add_raw_packet, add_raw_packets_batch, PacketData,
    direct_online_learn, DirectLearningInput,
    get_position_state, list_tags, update_tag_label, TagLabelUpdate,
    get_alerts, clear_alerts, get_position_history,
    search_assets, list_assets, get_asset, create_asset, AssetCreate, update_asset, AssetUpdate, delete_asset,
    get_nearby_assets, get_contextual_map, get_confidence_heatmap,
    configure_anchor, ConfigUpdate
)

@pytest.mark.anyio
async def test_async_endpoints():
    res = await serve_index()
    assert res is not None

    status = await get_control_status()
    assert "services" in status
    assert "telemetry" in status

    act_on = await handle_control_action(ControlAction(action="start_sim"))
    assert act_on["status"] == "ok"

    act_off = await handle_control_action(ControlAction(action="stop_sim"))
    assert act_off["status"] == "ok"

    schematic = await get_schematic()
    assert "anchors" in schematic

    save_res = await save_schematic(SchematicPayload(**schematic))
    assert save_res["status"] == "ok"

    train_status = await get_training_status()
    assert "available_models" in train_status
    assert "last_successful_run" in train_status
    assert "last_result" in train_status

    cancel_res = await cancel_training_run()
    assert cancel_res["status"] == "ok"

    reload_res = await reload_models()
    assert reload_res["status"] == "ok"

def test_sync_observation_and_learning_endpoints():
    from server.app import shared, OnlineDistanceLearner
    pkt = PacketData(timestamp=1700000000000, anchor="ANCHOR_01", mac="TAG_TEST_01", rssi=-65)
    obs_res = add_raw_packet(pkt)
    assert obs_res["status"] == "success"

    batch_res = add_raw_packets_batch([pkt])
    assert batch_res["status"] == "success"

    learn_res = direct_online_learn(DirectLearningInput(anchor_id="ANCHOR_01", rssi=-60.0, true_distance=2.0))
    assert learn_res["status"] == "learned"

    # Reset shared online learner to prevent polluting other unit tests
    shared['online_learner'] = OnlineDistanceLearner()

def test_sync_state_and_tag_endpoints():
    add_raw_packet(PacketData(timestamp=1700000000000, anchor="ANCHOR_01", mac="TAG_TEST_01", rssi=-65))

    state_all = get_position_state()
    assert "tags" in state_all

    state_single = get_position_state(tag_id="TAG_TEST_01")
    assert "tags" in state_single

    tags_list = list_tags()
    assert "tags" in tags_list

    lbl_res = update_tag_label(TagLabelUpdate(tag_id="TAG_TEST_01", label="Test Tag"))
    assert lbl_res["status"] == "success"

def test_sync_alerts_and_history_endpoints():
    alerts_all = get_alerts()
    assert "alerts" in alerts_all

    alerts_tag = get_alerts(tag_id="TAG_TEST_01")
    assert "alerts" in alerts_tag

    clr_res = clear_alerts()
    assert clr_res["status"] == "success"

    hist = get_position_history()
    assert "history" in hist

def test_sync_search_and_map_endpoints():
    search_res = search_assets(q="test")
    assert "results" in search_res

    nearby_res = get_nearby_assets(room="Room A (Executive Suite 1)")
    assert "nearby" in nearby_res

    context_map = get_contextual_map(room="Room A (Executive Suite 1)")
    assert context_map is not None

def test_sync_asset_crud_endpoints():
    test_id = "unit_test_asset_01"
    try:
        delete_asset(test_id)
    except Exception:
        pass
    create_dto = AssetCreate(
        id=test_id,
        name="Unit Test Equipment",
        type="equipment",
        department="Operations",
        floor=1,
        room="Room A",
        ble_mac="TAG_TEST_01",
        status="active",
        notes="Created by automated endpoint test"
    )
    c_res = create_asset(create_dto)
    assert c_res["status"] == "success"

    a_list = list_assets()
    assert "assets" in a_list

    a_single = get_asset(test_id)
    assert a_single["name"] == "Unit Test Equipment"

    upd_res = update_asset(test_id, AssetUpdate(notes="Updated notes"))
    assert upd_res["status"] == "success"

    del_res = delete_asset(test_id)
    assert del_res["status"] == "success"

def test_sync_heatmap_and_config_endpoints():
    heatmap = get_confidence_heatmap(step=1.0)
    assert heatmap is not None

    cfg_res = configure_anchor(ConfigUpdate(anchor_id="ANCHOR_01", x=0.5, y=5.5))
    assert cfg_res["status"] == "success"
