from wenjia_agent.agents import (
    fortune_agent,
    main_agent,
    mystic_tools_agent,
    naming_agent,
    profile_agent,
    relationship_agent,
)
from wenjia_agent.prompts import load_prompt


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


def test_all_reply_prompts_avoid_markdown_tables():
    prompt_files = [
        "main_agent.md",
        "profile_agent.md",
        "fortune_analysis.md",
        "relationship_agent.md",
        "naming_agent.md",
        "mystic_tools_agent.md",
    ]

    for prompt_file in prompt_files:
        assert "不要使用 Markdown 表格" in load_prompt(prompt_file)


def test_prompts_enforce_birth_info_gate():
    gated_prompt_files = [
        "main_agent.md",
        "profile_agent.md",
        "fortune_analysis.md",
        "relationship_agent.md",
        "naming_agent.md",
        "mystic_tools_agent.md",
    ]

    for prompt_file in gated_prompt_files:
        prompt = load_prompt(prompt_file)
        assert "validate_birth_info_tool" in prompt
        assert "完整出生信息" in prompt


def test_prompts_reference_luck_cycle_tool():
    for prompt_file in ("fortune_analysis.md", "mystic_tools_agent.md"):
        prompt = load_prompt(prompt_file)
        assert "build_luck_cycle_context_tool" in prompt


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


def test_agents_can_query_long_term_memory():
    for agent in (main_agent, profile_agent, fortune_agent, relationship_agent, naming_agent):
        tool_names = {tool.name for tool in agent.tools}
        assert "list_long_term_memories_tool" in tool_names
