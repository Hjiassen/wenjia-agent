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


def test_memory_upsert_and_list(temp_memory_db):
    first = memory_store.upsert_memory(
        "user:1",
        kind="note",
        key="preference:style",
        title="偏好",
        content="喜欢克制、直接的分析。",
        source_session_id="web:s1",
    )
    second = memory_store.upsert_memory(
        "user:1",
        kind="note",
        key="preference:style",
        title="偏好",
        content="喜欢先给结论。",
        source_session_id="web:s2",
    )

    assert first["id"] == second["id"]
    memories = memory_store.list_memories("user:1")
    assert len(memories) == 1
    assert memories[0]["content"] == "喜欢先给结论。"


def test_profile_memories_are_rejected(temp_memory_db):
    with pytest.raises(ValueError, match="profile memories are no longer supported"):
        memory_store.upsert_memory(
            "user:1",
            kind="profile",
            key="profile:本人:测试",
            title="本人：测试",
            content="出生1995-05-12；四柱甲子",
        )


def test_query_ranked_memories_prefer_relevant_old_items(temp_memory_db):
    memory_store.upsert_memory(
        "user:1",
        kind="note",
        key="preference:recent",
        title="近期偏好",
        content="喜欢回答先给结论。",
    )
    memory_store.upsert_memory(
        "user:1",
        kind="note",
        key="context:career",
        title="持续目标",
        content="近期关注职业方向。",
    )

    memories = memory_store.list_memories("user:1", query="我妈妈的命格怎么看")

    assert {item["kind"] for item in memories} == {"note"}


def test_delete_memory_is_scoped_to_user(temp_memory_db):
    saved = memory_store.upsert_memory(
        "user:1",
        kind="note",
        key="preference:style",
        title="偏好",
        content="喜欢简洁回答。",
    )

    assert memory_store.delete_memory("user:2", saved["id"]) is False
    assert memory_store.list_memories("user:1")

    assert memory_store.delete_memory("user:1", saved["id"]) is True
    assert memory_store.list_memories("user:1") == []
