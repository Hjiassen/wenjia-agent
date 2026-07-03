from types import SimpleNamespace

import pytest

from wenjia_agent.runtime import profile_store
from wenjia_agent.runtime import memory_store
from wenjia_agent.runtime.run_context import WenjiaRunContext


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Point the profile store at a throwaway sqlite file per test."""

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    url = f"sqlite:///{tmp_path / 'profiles.db'}"
    engine = create_engine(url, future=True)
    monkeypatch.setattr(profile_store, "_engine", engine)
    monkeypatch.setattr(profile_store, "_Session", sessionmaker(bind=engine, future=True))
    monkeypatch.setattr(profile_store, "_initialized", False)
    monkeypatch.setattr(memory_store, "_engine", engine)
    monkeypatch.setattr(memory_store, "_Session", sessionmaker(bind=engine, future=True))
    monkeypatch.setattr(memory_store, "_initialized", False)
    return url


def _bazi_and_context():
    from wenjia_agent.tools.bazi_tools import build_bazi_context_data

    built = build_bazi_context_data(
        name="测试",
        gender="未知",
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


def test_save_and_list_round_trip(temp_db):
    bazi, context = _bazi_and_context()

    saved = profile_store.save_profile("web:s1", "本人", bazi, context)
    assert saved["id"] >= 1
    assert saved["relationship_type"] == "本人"
    assert saved["name"] == "测试"
    assert saved["pillars"]["day"]
    assert saved["birth"] == {
        "year": 1995,
        "month": 5,
        "day": 12,
        "hour": 9,
        "minute": 30,
        "calendar_type": "solar",
        "is_leap_month": False,
        "province": "北京市",
        "city": "北京市",
        "longitude": "116.4074",
    }

    profiles = profile_store.list_profiles("web:s1")
    assert len(profiles) == 1
    assert profiles[0]["name"] == "测试"
    assert profiles[0]["birth"]["year"] == 1995
    assert profiles[0]["birth"]["province"] == "北京市"
    assert set(profiles[0]["five_elements"]) == {"木", "火", "土", "金", "水"}


def test_save_profile_mirrors_to_long_term_memory(temp_db):
    bazi, context = _bazi_and_context()

    profile_store.save_profile("web:s1", "本人", bazi, context, user_id="client:1")

    memories = memory_store.list_memories("client:1")
    assert len(memories) == 1
    assert memories[0]["kind"] == "profile"
    assert "本人：测试" in memories[0]["content"]


def test_upsert_does_not_duplicate_same_person(temp_db):
    bazi, context = _bazi_and_context()

    first = profile_store.save_profile("web:s1", "本人", bazi, context)
    second = profile_store.save_profile("web:s1", "本人", bazi, context)

    assert first["id"] == second["id"]
    assert len(profile_store.list_profiles("web:s1")) == 1


def test_profiles_are_scoped_by_session(temp_db):
    bazi, context = _bazi_and_context()

    profile_store.save_profile("web:s1", "本人", bazi, context)
    profile_store.save_profile("web:s2", "父亲", bazi, context)

    assert len(profile_store.list_profiles("web:s1")) == 1
    assert profile_store.list_profiles("web:s2")[0]["relationship_type"] == "父亲"


def test_manual_profile_create_and_edit(temp_db):
    created = profile_store.upsert_manual_profile(
        "web:s1",
        {
            "name": "手动人物",
            "relationship_type": "朋友",
            "gender": "未知",
            "birth_year": 1990,
            "birth_month": 1,
            "birth_day": 2,
            "birth_hour": 3,
            "birth_minute": 4,
            "calendar_type": "solar",
            "is_leap_month": False,
            "province": "北京市",
            "city": "北京市",
        },
    )

    assert created["name"] == "手动人物"
    assert created["birth"]["year"] == 1990

    updated = profile_store.upsert_manual_profile(
        "web:s1",
        {
            "name": "手动人物2",
            "relationship_type": "本人",
            "gender": "男",
            "birth_year": 1990,
            "birth_month": 1,
            "birth_day": 2,
            "birth_hour": 3,
            "birth_minute": 4,
            "calendar_type": "solar",
            "is_leap_month": False,
            "province": "北京市",
            "city": "北京市",
        },
        profile_id=created["id"],
    )

    assert updated["id"] == created["id"]
    assert updated["name"] == "手动人物2"
    assert updated["relationship_type"] == "本人"
    assert len(profile_store.list_profiles("web:s1")) == 1


def test_manual_profile_mirrors_to_long_term_memory(temp_db):
    created = profile_store.upsert_manual_profile(
        "web:s1",
        {
            "name": "手动人物",
            "relationship_type": "朋友",
            "gender": "未知",
            "birth_year": 1990,
            "birth_month": 1,
            "birth_day": 2,
            "birth_hour": 3,
            "birth_minute": 4,
            "calendar_type": "solar",
            "is_leap_month": False,
            "province": "北京市",
            "city": "北京市",
        },
        user_id="client:1",
    )

    memories = memory_store.list_memories("client:1", query="朋友手动人物")
    assert len(memories) == 1
    assert "朋友：手动人物" in memories[0]["content"]

    profile_store.upsert_manual_profile(
        "web:s1",
        {
            "name": "手动人物2",
            "relationship_type": "本人",
            "gender": "男",
            "birth_year": 1990,
            "birth_month": 1,
            "birth_day": 2,
            "birth_hour": 3,
            "birth_minute": 4,
            "calendar_type": "solar",
            "is_leap_month": False,
            "province": "北京市",
            "city": "北京市",
        },
        profile_id=created["id"],
        user_id="client:1",
    )

    memories = memory_store.list_memories("client:1")
    assert len(memories) == 1
    assert memories[0]["key"] == "profile:本人:手动人物2"


def _birth_args():
    return dict(
        name="测试",
        gender="未知",
        birth_year=1995,
        birth_month=5,
        birth_day=12,
        birth_hour=9,
        birth_minute=30,
        province="北京市",
        city="北京市",
    )


def test_save_profile_helper_persists_with_session(temp_db):
    from wenjia_agent.tools.bazi_tools import _save_profile

    result = _save_profile(
        WenjiaRunContext(session_id="web:tool"), "母亲", _birth_args()
    )

    assert result["ok"] is True
    assert result["data"]["saved"] is True
    assert result["data"]["profile"]["relationship_type"] == "母亲"
    assert len(profile_store.list_profiles("web:tool")) == 1


def test_save_profile_helper_degrades_without_session(temp_db):
    from wenjia_agent.tools.bazi_tools import _save_profile

    result = _save_profile(WenjiaRunContext(session_id=None), "本人", _birth_args())

    assert result["ok"] is True
    assert result["data"]["saved"] is False
    assert profile_store.list_profiles("web:tool") == []


def test_autosave_subject_persists_on_successful_chart(temp_db):
    from wenjia_agent.tools.bazi_tools import _autosave_subject, build_bazi_context_data

    built = build_bazi_context_data(**_birth_args())
    ctx = SimpleNamespace(context=WenjiaRunContext(session_id="web:auto"))

    _autosave_subject(ctx, built)  # type: ignore[arg-type]

    profiles = profile_store.list_profiles("web:auto")
    assert len(profiles) == 1
    assert profiles[0]["relationship_type"] == "本人"
    assert profiles[0]["birth"]["year"] == 1995
    assert profiles[0]["birth"]["month"] == 5
    assert profiles[0]["birth"]["day"] == 12
    assert profiles[0]["birth"]["hour"] == 9
    assert profiles[0]["birth"]["minute"] == 30
    assert profiles[0]["birth"]["province"] == "北京市"
    assert profiles[0]["birth"]["city"] == "北京市"


def test_autosave_subject_skips_cached_results(temp_db):
    from wenjia_agent.tools.bazi_tools import _autosave_subject, build_bazi_context_data

    built = build_bazi_context_data(**_birth_args())
    cached = {**built, "from_cache": True}
    ctx = SimpleNamespace(context=WenjiaRunContext(session_id="web:auto"))

    _autosave_subject(ctx, cached)  # type: ignore[arg-type]

    assert profile_store.list_profiles("web:auto") == []
