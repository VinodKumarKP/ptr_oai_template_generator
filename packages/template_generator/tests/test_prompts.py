import pytest
from oai_template_generator.prompts import _slugify, prompt_project_details

def test_slugify():
    assert _slugify("My Project") == "my_project"
    assert _slugify("My-Project") == "my_project"
    assert _slugify("My_Project") == "my_project"
    assert _slugify("  My Project  ") == "my_project"
    assert _slugify("123MyProject") == "myproject"

def test_prompt_project_details_mcp(mocker):
    # Mock inputs for prompt_project_details
    # Structure of inputs based on prompts.py logic:
    # 1. Project name
    # 2. Author
    # 3. Email
    # 4. Output dir
    # 5. Description
    # 6. List of MCP servers
    # -- Loop for 'weather' --
    # 7. Port
    # 8. Class Name
    # 9. Description
    # 10. Tags
    # 11. Source
    # 12. Add env vars? (n)
    
    mocker.patch("builtins.input", side_effect=[
        "mcp_test",             # 1. Project Name
        "Author Name",          # 2. Author
        "test@capgemini.com",   # 3. Email
        ".",                    # 4. Output dir
        "Description",          # 5. Description
        "weather",              # 6. Server list
        "8080",                 # 7. Port
        "WeatherTools",         # 8. Class Name
        "A weather server",     # 9. Desc
        "weather, api",         # 10. Tags
        "http://source",        # 11. Source
        "n",                    # 12. Env vars
    ])
    
    template, slug, author, email, output_dir, description, items, framework = prompt_project_details(
        template="mcp",
        name=None,
        author=None,
        email=None,
        output_dir=None,
        description=None
    )
    
    assert template == "mcp"
    assert slug == "ptr_mcp_servers_mcp_test"
    assert len(items) == 1
    item = items[0]
    assert item["name"] == "weather_server"
    assert item["class_name"] == "WeatherTools"
    assert item["port"] == "8080"
    assert item["tags"] == ["weather", "api"]

def test_prompt_project_details_agent(mocker):
    # Mock inputs for prompt_project_details
    # 1. Project name
    # 2. Author
    # 3. Email
    # 4. Output dir
    # 5. Description
    # 6. List of Agents
    # 7. Framework Selection (1 - langgraph)
    # -- Loop for 'research' --
    # 8. Port
    # 9. Description
    # 10. Sub-agents (empty -> self)
    # 11. System Prompt
    # 12. Model ID (Select 5 - Custom)
    # 13. Custom Model ID
    # 14. AWS Region
    # 15. Use tools? (y)
    # 16. Tool list
    # 17. Use MCP? (n)
    # 18. Global Memory? (n)
    # 19. Global KB? (n)
    # 20. Agent KB? (n)
    # 21. Guardrails? (n)
    # 22. Tags
    # 23. Add prompts? (n)
    # 24. Env vars? (n)

    mocker.patch("builtins.input", side_effect=[
        "agent_test",           # 1
        "Author Name",          # 2
        "test@capgemini.com",   # 3
        ".",                    # 4
        "Description",          # 5
        "research",             # 6
        "1",                    # 7 (Framework)
        "9000",                 # 8 (Port)
        "A research agent",     # 9
        "",                     # 10 (Sub-agents empty)
        "You are a researcher", # 11 (Instructions)
        "5",                    # 12 (Model - Custom)
        "my-custom-model",      # 13
        "us-west-2",            # 14
        "y",                    # 15 (Tools)
        "search_tool",          # 16
        "n",                    # 17 (MCP)
        "n",                    # 18 (Memory)
        "n",                    # 19 (Global KB)
        "n",                    # 20 (Agent KB)
        "n",                    # 21 (Guardrails)
        "research, ai",         # 22 (Tags)
        "n",                    # 23 (Prompts)
        "n"                     # 24 (Env)
    ])
    
    template, slug, author, email, output_dir, description, items, framework = prompt_project_details(
        template="agent",
        name=None,
        author=None,
        email=None,
        output_dir=None,
        description=None
    )
    
    assert template == "agent"
    assert slug == "ptr_agent_servers_agent_test"
    assert framework == "langgraph"
    assert len(items) == 1
    item = items[0]
    assert item["name"] == "research_agent"
    assert item["model_id"] == "my-custom-model"
    assert item["use_tools"] is True
    assert item["tool_list"] == ["search_tool"]
