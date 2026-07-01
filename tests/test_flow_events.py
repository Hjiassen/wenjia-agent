from wenjia_agent.runtime.flow_events import (
    get_agent_display_name,
    get_tool_display_name,
    is_tool_result_success,
)


def test_flow_event_display_names():
    assert get_agent_display_name("WenjiaMainAgent") == "主控路由"
    assert get_agent_display_name("FortuneAgent") == "命格分析"
    assert get_tool_display_name("validate_birth_info_tool") == "出生信息完整性检查"
    assert get_tool_display_name("calculate_bazi_tool") == "确定性八字排盘"


def test_tool_result_success_detection():
    assert is_tool_result_success({"ok": True}) is True
    assert is_tool_result_success({"ok": False}) is True
    assert is_tool_result_success('{"ok": true}') is True
    assert is_tool_result_success('{"error": "boom"}') is False
    assert is_tool_result_success("plain text") is True
