from types import SimpleNamespace

import pytest

from app.runtime import profile_store
from app.runtime.run_context import WenjiaRunContext


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
    return url


def _bazi_and_context():
    from app.tools.bazi_tools import build_bazi_context_data

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

    profiles = profile_store.list_profiles("web:s1")
    assert len(profiles) == 1
    assert profiles[0]["name"] == "测试"
    assert set(profiles[0]["five_elements"]) == {"木", "火", "土", "金", "水"}


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
    from app.tools.bazi_tools import _save_profile

    result = _save_profile(
        WenjiaRunContext(session_id="web:tool"), "母亲", _birth_args()
    )

    assert result["ok"] is True
    assert result["data"]["saved"] is True
    assert result["data"]["profile"]["relationship_type"] == "母亲"
    assert len(profile_store.list_profiles("web:tool")) == 1


def test_save_profile_helper_degrades_without_session(temp_db):
    from app.tools.bazi_tools import _save_profile

    result = _save_profile(WenjiaRunContext(session_id=None), "本人", _birth_args())

    assert result["ok"] is True
    assert result["data"]["saved"] is False
    assert profile_store.list_profiles("web:tool") == []


def test_autosave_subject_persists_on_successful_chart(temp_db):
    from app.tools.bazi_tools import _autosave_subject, build_bazi_context_data

    built = build_bazi_context_data(**_birth_args())
    ctx = SimpleNamespace(context=WenjiaRunContext(session_id="web:auto"))

    _autosave_subject(ctx, built)  # type: ignore[arg-type]

    profiles = profile_store.list_profiles("web:auto")
    assert len(profiles) == 1
    assert profiles[0]["relationship_type"] == "本人"


def test_autosave_subject_skips_cached_results(temp_db):
    from app.tools.bazi_tools import _autosave_subject, build_bazi_context_data

    built = build_bazi_context_data(**_birth_args())
    cached = {**built, "from_cache": True}
    ctx = SimpleNamespace(context=WenjiaRunContext(session_id="web:auto"))

    _autosave_subject(ctx, cached)  # type: ignore[arg-type]

    assert profile_store.list_profiles("web:auto") == []
