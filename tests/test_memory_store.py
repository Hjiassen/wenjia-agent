import pytest

from wenjia_agent.runtime import memory_store


@pytest.fixture()
def temp_memory_db(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path / 'memory.db'}", future=True)
    monkeypatch.setattr(memory_store, "_engine", engine)
    monkeypatch.setattr(memory_store, "_Session", sessionmaker(bind=engine, future=True))
    monkeypatch.setattr(memory_store, "_initialized", False)
    return engine


def _bazi_and_context():
    from wenjia_agent.tools.bazi_tools import build_bazi_context_data

    built = build_bazi_context_data(
        name="测试",
        gender="男",
        birth_year=1995,
        birth_month=5,
        birth_day=12,
        birth_hour=9,
        birth_minute=30,
        province="北京市",
        city="北京市",
    )
    assert built["ok"] is True
    data = built["data"]
    return data["bazi"], data["context"]


def test_memory_upsert_and_list(temp_memory_db):
    first = memory_store.upsert_memory(
        "client:1",
        kind="note",
        key="preference:style",
        title="偏好",
        content="喜欢克制、直接的分析。",
        source_session_id="web:s1",
    )
    second = memory_store.upsert_memory(
        "client:1",
        kind="note",
        key="preference:style",
        title="偏好",
        content="喜欢先给结论。",
        source_session_id="web:s2",
    )

    assert first["id"] == second["id"]
    memories = memory_store.list_memories("client:1")
    assert len(memories) == 1
    assert memories[0]["content"] == "喜欢先给结论。"


def test_remember_profile_formats_context(temp_memory_db):
    bazi, context = _bazi_and_context()

    saved = memory_store.remember_profile(
        "client:1",
        "本人",
        bazi,
        context,
        source_session_id="web:s1",
    )
    formatted = memory_store.format_memory_context("client:1")

    assert saved is not None
    assert saved["kind"] == "profile"
    assert "本人：测试" in formatted
    assert "四柱" in formatted
    assert "用户本轮更正" in formatted
