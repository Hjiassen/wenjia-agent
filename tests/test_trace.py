import json

from wenjia_agent.runtime.config import settings
from wenjia_agent.runtime.trace import start_trace


def test_trace_recorder_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "trace_enabled", True)
    monkeypatch.setattr(settings, "trace_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_fallback_model", "fallback-model")

    trace = start_trace("session-1", "hello\nworld", source="test")
    trace.emit("custom", value={"ok": True})
    trace.finish("success", fallback_used=False)

    assert trace.path is not None
    lines = trace.path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]

    assert [event["event"] for event in events] == ["run_start", "custom", "run_end"]
    assert events[0]["session_id"] == "session-1"
    assert events[0]["source"] == "test"
    assert events[0]["message_preview"] == "hello world"
    assert events[0]["fallback_model"] == "fallback-model"
    assert events[1]["value"] == {"ok": True}
    assert events[2]["status"] == "success"


def test_trace_recorder_respects_disabled_setting(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "trace_enabled", False)
    monkeypatch.setattr(settings, "trace_dir", str(tmp_path))

    trace = start_trace("session-1", "hello", source="test")
    trace.emit("custom")
    trace.finish("success")

    assert trace.path is None
    assert not list(tmp_path.iterdir())
