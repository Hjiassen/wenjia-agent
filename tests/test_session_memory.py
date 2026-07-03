from agents.memory.session_settings import SessionSettings

from wenjia_agent.runtime import session_memory


def test_build_session_settings_uses_positive_limit(monkeypatch):
    monkeypatch.setattr(session_memory.settings, "session_history_limit", 24)

    built = session_memory.build_session_settings()

    assert isinstance(built, SessionSettings)
    assert built.limit == 24


def test_build_session_settings_can_disable_limit(monkeypatch):
    monkeypatch.setattr(session_memory.settings, "session_history_limit", 0)

    assert session_memory.build_session_settings() is None
