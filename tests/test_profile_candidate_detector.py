from apps.web.backend.modules.profile_candidate_detector import detect_profile_candidates


def test_detects_explicit_relationships_without_guessing_real_names():
    suggestions = detect_profile_candidates(
        "我妈妈最近不舒服，我对象也比较担心。", "web:one"
    )

    assert [item["suggested_relationship"] for item in suggestions] == ["母亲", "伴侣"]
    assert suggestions[0]["display_name"] == "我的母亲"
    assert suggestions[0]["source_message_id"].startswith("message:")


def test_respects_explicit_opt_out_and_ignores_generic_mentions():
    assert detect_profile_candidates("我妈妈的资料不要记录", "web:one") == []
    assert detect_profile_candidates("有人说父母都很重要", "web:one") == []


def test_suggestion_key_is_stable_for_same_message():
    first = detect_profile_candidates("我的朋友最近换工作", "web:one")
    second = detect_profile_candidates("我的朋友最近换工作", "web:one")

    assert first == second
