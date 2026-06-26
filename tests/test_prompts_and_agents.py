from app.agents import (
    fortune_agent,
    main_agent,
    mystic_tools_agent,
    naming_agent,
    profile_agent,
    relationship_agent,
)
from app.prompts import load_prompt


def test_prompt_templates_load_and_are_active():
    prompt_files = [
        "main_agent.md",
        "profile_agent.md",
        "fortune_analysis.md",
        "relationship_agent.md",
        "naming_agent.md",
        "mystic_tools_agent.md",
    ]

    for prompt_file in prompt_files:
        prompt = load_prompt(prompt_file)
        assert "owner: wenjia-agent" in prompt
        assert "status: draft" not in prompt
        assert "MVP 暂未启用" not in prompt


def test_main_agent_has_specialist_handoffs():
    handoff_names = {agent.name for agent in main_agent.handoffs}

    assert handoff_names == {
        "ProfileAgent",
        "FortuneAgent",
        "RelationshipAgent",
        "NamingAgent",
        "MysticToolsAgent",
    }


def test_specialist_agents_are_configured():
    assert profile_agent.tools
    assert mystic_tools_agent.tools
    assert fortune_agent.output_type.__name__ == "FortuneReport"
    assert relationship_agent.output_type.__name__ == "RelationshipReport"
    assert naming_agent.output_type.__name__ == "NamingReport"
