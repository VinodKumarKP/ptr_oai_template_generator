"""Project builder — copies and renders the chosen template."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


TEMPLATES_DIR = Path(__file__).parent / "templates"

# Placeholder token used inside template files
_TOKEN = "{{PROJECT_NAME}}"
_TOKEN_AUTHOR = "{{AUTHOR}}"
_TOKEN_EMAIL = "{{EMAIL}}"
_TOKEN_DESC = "{{DESCRIPTION}}"
_TOKEN_TITLE = "{{PROJECT_TITLE}}"


class ProjectBuilder:
    def __init__(
        self,
        template: str,
        project_name: str,
        author: str,
        email: str,
        description: str,
        output_dir: Path,
        init_git: bool = True,
        create_venv: bool = True,
        items: list[dict] | list[str] = None,
        framework: str = None,
        overwrite: bool = False,
    ):
        self.template = template
        self.project_name = project_name
        self.author = author
        self.email = email
        self.description = description
        self.output_dir = output_dir
        self.init_git = init_git
        self.create_venv = create_venv
        self.items = items or []
        self.framework = framework
        self.overwrite = overwrite

        self.template_dir = TEMPLATES_DIR / template
        self.project_dir = output_dir / project_name

    # ------------------------------------------------------------------
    def build(self):
        self._validate()
        self._copy_template()
        if self.template == "mcp":
            self._setup_mcp_servers()
        elif self.template == "agent":
            self._setup_agents()
            self._update_dependencies()
        self._render_files()
        if self.init_git:
            self._init_git()
        if self.create_venv:
            self._create_venv()
        self._print_success()

    # ------------------------------------------------------------------
    def _validate(self):
        if not self.template_dir.exists():
            print(f"❌  Template '{self.template}' not found at {self.template_dir}")
            sys.exit(1)

        if self.project_dir.exists() and not self.overwrite:
            print(f"❌  Directory '{self.project_dir}' already exists.")
            sys.exit(1)

        if not self.project_name:
            print("❌  Project name cannot be empty.")
            sys.exit(1)

    def _copy_template(self):
        print(f"📁  Creating project at {self.project_dir} …")
        if self.project_dir.exists() and self.overwrite:
            shutil.rmtree(self.project_dir)
            
        shutil.copytree(self.template_dir, self.project_dir)

        # Rename the inner src package directory if it exists
        placeholder_pkg = self.project_dir / "src" / "project_name"
        if placeholder_pkg.exists():
            placeholder_pkg.rename(self.project_dir / "src" / self.project_name)

    def _setup_mcp_servers(self):
        """Setup specific MCP servers if template is mcp."""
        mcp_registry_servers = self.project_dir / "mcp_registry_servers"
        servers_dir = mcp_registry_servers / "servers"
        servers_config_dir = mcp_registry_servers / "servers_config"
        
        # Tools directory for MCP servers (if needed, though typically inside server dir)
        # But instructions say: "ask for class name. Create the class script with few dummy functions."
        # This implies creating a separate file for the class? Or updating the server.py?
        # The prompt says "Create the class script with few dummy functions. Then update ... server.template with class name"
        # It seems the class script is the Tools class file referenced in server.template.
        # Let's create a `utils` directory if it doesn't exist and put the class file there.
        # Or put it inside the server directory itself?
        # The template has `from mcp_registry_servers.utils.{{mcp util file name}} import {{mcp util class name}}` (or similar in original)
        # But wait, our current server.template (from previous steps) has:
        # `from mcp_registry_servers.tools.{tool_file_name} import {tools_class_name}`
        # Wait, the current `server.template` content is:
        # from mcp_registry_servers.tools.{tool_file_name} import {tools_class_name}
        # ... object_list=[{tools_class_name}()]
        
        # So we need to:
        # 1. Create `mcp_registry_servers/tools/{tool_file_name}.py`
        # 2. Put the class `{tools_class_name}` in it with dummy functions.
        # 3. Update server.template and write to server.py.
        
        # We need a place for these tool files. Let's assume `mcp_registry_servers/tools`.
        tools_dir = mcp_registry_servers / "tools"
        tools_dir.mkdir(exist_ok=True)
        (tools_dir / "__init__.py").touch()
        
        # Template files
        template_yaml = servers_config_dir / "template_server.yaml"
        server_template_file = mcp_registry_servers / "server.template"

        # Original servers template directory (to copy __init__.py etc)
        src_servers_template = self.template_dir / "mcp_registry_servers" / "servers"

        for server_config in self.items:
            server_name = server_config["name"] if isinstance(server_config, dict) else server_config
            target_server_dir = servers_dir / server_name
            
            # 1. Create the server directory and copy base files
            shutil.copytree(src_servers_template, target_server_dir, dirs_exist_ok=True)
            
            # Extract class name if provided, else generate
            if isinstance(server_config, dict):
                tools_class_name = server_config.get("class_name")
                if not tools_class_name:
                    # Fallback logic
                    tools_class_name = "".join(word.capitalize() for word in server_name.split("_")) 
                    if tools_class_name.endswith("Server"):
                        tools_class_name = tools_class_name[:-6] + "Tools"
                    else:
                        tools_class_name += "Tools"
            else:
                tools_class_name = "".join(word.capitalize() for word in server_name.split("_")) + "Tools"

            # Tool file name matches server name usually, or we can use snake_case of class
            tool_file_name = server_name
            
            # 2. Create the class script (Tools file)
            tool_file_path = tools_dir / f"{tool_file_name}.py"
            tool_content = f'''"""Tools for {server_name}."""

class {tools_class_name}:
    """
    Tools for {server_name}.
    """
    
    def example_tool(self, query: str) -> str:
        """
        An example tool function.
        
        Args:
            query (str): The query string.
            
        Returns:
            str: The result.
        """
        return f"Processed {{query}} by {server_name}"

    def status_check(self) -> dict:
        """
        Check status.
        
        Returns:
            dict: Status info.
        """
        return {{"status": "ok", "server": "{server_name}"}}
'''
            tool_file_path.write_text(tool_content, encoding="utf-8")

            # 3. Handle server.py from server.template
            target_server_py = target_server_dir / "server.py"
            if server_template_file.exists():
                content = server_template_file.read_text(encoding="utf-8")
                
                # Server class name
                server_class_name = "".join(word.capitalize() for word in server_name.split("_"))
                if not server_class_name.endswith("Server"):
                    server_class_name += "Server"
                
                content = content.replace("{server_name}", server_class_name)
                content = content.replace("{tool_file_name}", tool_file_name)
                content = content.replace("{tools_class_name}", tools_class_name)
                
                target_server_py.write_text(content, encoding="utf-8")

            # 4. Create config yaml dynamically based on user input
            if isinstance(server_config, dict):
                yaml_content = []
                yaml_content.append(f"port: {server_config['port']}")
                yaml_content.append(f"description: |\n  {server_config['description']}")
                
                if server_config["tags"]:
                    yaml_content.append("tags:")
                    for tag in server_config["tags"]:
                        yaml_content.append(f"  - {tag}")
                
                if server_config["source"]:
                    yaml_content.append(f"source: {server_config['source']}")
                    
                if server_config["env"]:
                    yaml_content.append("env:")
                    for k, v in server_config["env"].items():
                        yaml_content.append(f"  {k}: {v}")
                
                new_yaml = servers_config_dir / f"{server_name}.yaml"
                new_yaml.write_text("\n".join(yaml_content) + "\n", encoding="utf-8")
            else:
                # Fallback for simple string input (e.g. from tests)
                if template_yaml.exists():
                    new_yaml = servers_config_dir / f"{server_name}.yaml"
                    shutil.copy2(template_yaml, new_yaml)

        # Remove the template.yaml after creating server-specific configs
        if template_yaml.exists():
            template_yaml.unlink()
            
        # Remove the server.template file from the final project
        if server_template_file.exists():
            server_template_file.unlink()

    def _setup_agents(self):
        """Setup specific Agents if template is agent."""
        agentic_registry_agents = self.project_dir / "agentic_registry_agents"
        agents_dir = agentic_registry_agents / "agents"
        agents_config_dir = agentic_registry_agents / "agents_config"
        
        utils_dir = agentic_registry_agents / "utils"
        utils_dir.mkdir(exist_ok=True)
        (utils_dir / "__init__.py").touch()
        
        server_template_dir = agents_dir / "server_template"
        template_yaml = agents_config_dir / "template.yaml"
        
        framework_info = {
            "langgraph": {"core": "langgraph_core", "pkg": "langgraph_agent", "cls": "LangGraphAgent"},
            "crewai": {"core": "crewai_core", "pkg": "crewai_agent", "cls": "CrewAIAgent"},
            "strands": {"core": "aws_strands_core", "pkg": "aws_strands_agent", "cls": "StrandsAgent"},
            "openai": {"core": "openai_core", "pkg": "openai_agent", "cls": "OpenAIAgent"}
        }
        
        info = framework_info.get(self.framework, framework_info["langgraph"])

        for agent_config in self.items:
            # If items are dicts, extract name
            agent_name = agent_config["name"] if isinstance(agent_config, dict) else agent_config
            target_agent_dir = agents_dir / agent_name
            shutil.copytree(server_template_dir, target_agent_dir, dirs_exist_ok=True)
            
            # Handle templates inside the agent directory
            agent_template_file = target_agent_dir / "agent.template"
            server_template_file = target_agent_dir / "server.template"
            
            agent_class_name = "".join(word.capitalize() for word in agent_name.split("_")) + "Agent"
            
            if agent_template_file.exists():
                content = agent_template_file.read_text(encoding="utf-8")
                content = content.replace("{{core_package_name}}", info["core"])
                content = content.replace("{{agent_package_name}}", info["pkg"])
                content = content.replace("{{agent_class_name}}", info["cls"])
                content = content.replace("{{AgentName}}", agent_class_name)
                (target_agent_dir / "agent.py").write_text(content, encoding="utf-8")
                agent_template_file.unlink()
                
            if server_template_file.exists():
                content = server_template_file.read_text(encoding="utf-8")
                content = content.replace("{{agent_class_file_name}}", agent_name)
                content = content.replace("{{AgentName}}", agent_class_name)
                (target_agent_dir / "server.py").write_text(content, encoding="utf-8")
                server_template_file.unlink()

            # Create agent_name.yaml dynamically based on user input
            if isinstance(agent_config, dict):
                
                # --- Automated Tool Scaffolding ---
                tool_list = agent_config.get("tool_list", [])
                utils_filename = f"{agent_name}_utils.py"
                if tool_list:
                    utils_content = '"""Tools utility functions."""\n\n'
                    for tool in tool_list:
                        utils_content += f'''
def {tool}():
    """Dummy implementation for {tool}."""
    return "Executed {tool}"
'''
                    (utils_dir / utils_filename).write_text(utils_content, encoding="utf-8")

                # --- Helper for generating Knowledge Base sections ---
                def generate_kb_section(kb_list, indent_level=0):
                    lines = []
                    indent = " " * indent_level
                    for kb in kb_list:
                        kb_type = kb.get("type", "chroma")
                        lines.append(f"{indent}- name: {kb['name']}")
                        lines.append(f"{indent}  description: \"{kb['description']}\"")
                        lines.append(f"{indent}  vector_store:")
                        lines.append(f"{indent}    type: {kb_type}")
                        lines.append(f"{indent}    settings:")
                        lines.append(f"{indent}      collection_name: \"{kb['name']}\"")
                        lines.append(f"{indent}      persist_directory: \"./rag_db\"")
                        
                        if kb_type == "postgres":
                            lines.append(f"{indent}      # db_host: your-postgres-host.com")
                            lines.append(f"{indent}      # db_user: user")
                            lines.append(f"{indent}      # db_port: 5432")
                            lines.append(f"{indent}      # db_name: your_db")
                        elif kb_type == "s3":
                            lines.append(f"{indent}      # bucket_name: your-bucket")
                            lines.append(f"{indent}      # region: us-east-1")
                            
                        lines.append(f"{indent}  embedding:")
                        lines.append(f"{indent}    model_id: \"bedrock/amazon.titan-embed-text-v1\"")
                        lines.append(f"{indent}    region_name: \"us-west-2\"")
                        lines.append(f"{indent}  data_sources:")
                        lines.append(f"{indent}    - path: \"docs/sample.pdf\"")
                        lines.append(f"{indent}  text_splitter:")
                        lines.append(f"{indent}    type: \"recursive_character\"")
                        lines.append(f"{indent}    chunk_size: 1000")
                        lines.append(f"{indent}    chunk_overlap: 200")
                        lines.append(f"{indent}  retrieval_settings:")
                        lines.append(f"{indent}    top_k: 5")
                        lines.append(f"{indent}    score_threshold: 0.7")
                    return lines

                # --- YAML Generation ---
                yaml_content = []
                yaml_content.append("active: true")
                yaml_content.append(f"name: {agent_name}")
                yaml_content.append(f"description: |\n  {agent_config['description']}")
                yaml_content.append(f"type: {self.framework or 'langgraph'}")
                yaml_content.append("cloud_provider: aws")
                yaml_content.append(f"port: {agent_config['port']}")
                yaml_content.append("")
                
                # Check for sub-agents (multi-agent setup)
                sub_agents = agent_config.get("sub_agents", [])
                mcp_servers = agent_config.get("mcp_servers", [])
                global_kb = agent_config.get("global_kb", [])
                memory_config = agent_config.get("memory_config", {})
                use_guardrails = agent_config.get("use_guardrails", False)
                
                if len(sub_agents) > 1:
                    # Multi-agent/Supervisor setup
                    yaml_content.append(f"instructions: |\n  {agent_config['instructions']}")
                    yaml_content.append("")
                    
                    if global_kb:
                        yaml_content.append("# Global Knowledge Base")
                        yaml_content.append("knowledge_base:")
                        yaml_content.extend(generate_kb_section(global_kb, indent_level=2))
                        yaml_content.append("")
                    
                    yaml_content.append("# Multi-agent configuration")
                    yaml_content.append("agent_list:")
                    for sub in sub_agents:
                        # sub is a dict {name, context, knowledge_base}
                        sub_name = sub["name"]
                        sub_ctx = sub["context"]
                        sub_kb = sub.get("knowledge_base", [])
                        
                        yaml_content.append(f"  - {sub_name}:")
                        yaml_content.append(f"      system_prompt: Prompt for {sub_name}")
                        
                        # Add tools for sub-agent
                        if tool_list:
                            yaml_content.append("      tools:")
                            for t in tool_list:
                                yaml_content.append(f"        - {t}")
                        else:
                            yaml_content.append("      tools: []")
                            
                        if mcp_servers:
                            yaml_content.append("      mcps:")
                            for ms in mcp_servers:
                                yaml_content.append(f"        - {ms}")
                        else:
                            yaml_content.append("      mcps: []")
                        
                        if sub_ctx:
                            yaml_content.append("      context:")
                            for c in sub_ctx:
                                yaml_content.append(f"        - {c}")
                        else:
                            yaml_content.append("      # context: [other_agent_name]")
                            
                        if sub_kb:
                            yaml_content.append("      knowledge_base:")
                            yaml_content.extend(generate_kb_section(sub_kb, indent_level=8))

                    yaml_content.append("")
                else:
                    # Single agent setup
                    yaml_content.append(f"instructions: |\n  {agent_config['instructions']}")
                    yaml_content.append("")
                    
                    if global_kb:
                        # For single agent, global KB works same way or can be agent level.
                        # Assuming structure puts 'knowledge_base' at top for global
                        yaml_content.append("# Global Knowledge Base")
                        yaml_content.append("knowledge_base:")
                        yaml_content.extend(generate_kb_section(global_kb, indent_level=2))
                        yaml_content.append("")

                    # Single agent also has agent_list
                    yaml_content.append("# Agent configuration")
                    yaml_content.append("agent_list:")
                    for sub in sub_agents:
                         # sub is a dict {name, context, knowledge_base}
                         sub_name = sub["name"]
                         sub_ctx = sub["context"]
                         sub_kb = sub.get("knowledge_base", [])
                         yaml_content.append(f"  - {sub_name}:")
                         yaml_content.append(f"      system_prompt: {agent_config['instructions'].splitlines()[0] if agent_config['instructions'] else 'Default Prompt'}")
                         
                         if tool_list:
                            yaml_content.append("      tools:")
                            for t in tool_list:
                                yaml_content.append(f"        - {t}")
                         else:
                            yaml_content.append("      tools: []")

                         if mcp_servers:
                            yaml_content.append("      mcps:")
                            for ms in mcp_servers:
                                yaml_content.append(f"        - {ms}")
                         else:
                            yaml_content.append("      mcps: []")
                         
                         if sub_ctx:
                            yaml_content.append("      context:")
                            for c in sub_ctx:
                                yaml_content.append(f"        - {c}")
                         else:
                            yaml_content.append("      # context: [other_agent_name]")
                            
                         if sub_kb:
                            yaml_content.append("      knowledge_base:")
                            yaml_content.extend(generate_kb_section(sub_kb, indent_level=8))
                            
                    yaml_content.append("")

                yaml_content.append("# Model configuration")
                yaml_content.append("model:")
                yaml_content.append(f"  model_id: {agent_config['model_id']}")
                yaml_content.append(f"  region_name: {agent_config['region']}")
                yaml_content.append("")

                if tool_list:
                    yaml_content.append("# For tools configuration")
                    yaml_content.append("tools:")
                    # Define one entry pointing to the file that contains all the tools
                    utils_name_no_ext = os.path.splitext(utils_filename)[0]
                    yaml_content.append(f"  {utils_name_no_ext}:")
                    yaml_content.append(f"    module: {utils_name_no_ext}")
                    yaml_content.append(f"    base_path: ./utils")
                    yaml_content.append("")
                else:
                    yaml_content.append("# tools: {}")
                    yaml_content.append("")

                if mcp_servers:
                    yaml_content.append("# For MCP type agents")
                    yaml_content.append("mcps:")
                    for srv in mcp_servers:
                        yaml_content.append(f"  {srv}:")
                        yaml_content.append("    command: python")
                        yaml_content.append("    args: []")
                        yaml_content.append(f"    description: MCP server {srv}")
                        yaml_content.append(f"    title: {srv.replace('_', ' ').title()}")
                        yaml_content.append("    env: {}")
                    yaml_content.append("")
                else:
                    yaml_content.append("# mcps: {}")
                    yaml_content.append("")
                
                # Memory Configuration (Global)
                if memory_config:
                    mem_type = memory_config.get("type", "chroma")
                    mem_coll = memory_config.get("collection_name", "chat_memory")
                    
                    yaml_content.append("# Memory configuration")
                    yaml_content.append("memory:")
                    yaml_content.append("  vector_store:")
                    yaml_content.append(f"    type: {mem_type}")
                    yaml_content.append("    settings:")
                    yaml_content.append(f"      collection_name: \"{mem_coll}\"")
                    yaml_content.append("      persist_directory: \"./memory_db\"")
                    
                    if mem_type == "postgres":
                        yaml_content.append(f"      # db_host: your-postgres-host.com")
                        yaml_content.append(f"      # db_user: user")
                        yaml_content.append(f"      # db_port: 5432")
                        yaml_content.append(f"      # db_name: your_db")
                    elif mem_type == "s3":
                        yaml_content.append(f"      # bucket_name: your-bucket")
                        yaml_content.append(f"      # region: us-east-1")
                        
                    yaml_content.append("  embedding:")
                    yaml_content.append("    model_id: \"bedrock/amazon.titan-embed-text-v1\"")
                    yaml_content.append("    region_name: \"us-west-2\"")
                    yaml_content.append("  settings:")
                    yaml_content.append("    max_recent_turns: 3")
                    yaml_content.append("    max_relevant_turns: 3")
                    yaml_content.append("    similarity_threshold: 0.6")
                    yaml_content.append("")
                
                if use_guardrails:
                    yaml_content.append("# Guardrails configuration")
                    yaml_content.append("# NOTE: These are sample validators. Update the configuration as per your requirement.")
                    yaml_content.append("# For more validators and documentation, check guardrails.ai")
                    yaml_content.append("guardrails:")
                    yaml_content.append("  enable_agent_validation: false")
                    yaml_content.append("  custom_validators_dir: \"custom_guardrails\"")
                    yaml_content.append("  validators:")
                    yaml_content.append("    - name: competitor_check")
                    yaml_content.append("      full_name: guardrails/competitor_check")
                    yaml_content.append("      parameters:")
                    yaml_content.append("        competitors: [ \"Apple\", \"Samsung\" ]")
                    yaml_content.append("      on_fail: \"fix\"")
                    yaml_content.append("")
                    yaml_content.append("    - name: RestrictToTopic")
                    yaml_content.append("      full_name: tryolabs/restricttotopic")
                    yaml_content.append("      parameters:")
                    yaml_content.append("        valid_topics: [ \"sports\" ]")
                    yaml_content.append("")
                    yaml_content.append("    - name: DetectPII")
                    yaml_content.append("      full_name: guardrails/detect_pii")
                    yaml_content.append("      parameters:")
                    yaml_content.append("        pii_entities: [\"EMAIL_ADDRESS\", \"PHONE_NUMBER\"]")
                    yaml_content.append("")
                    yaml_content.append("    - name: profanity_free")
                    yaml_content.append("      full_name: guardrails/profanity_free")
                    yaml_content.append("")
                    yaml_content.append("  input:")
                    yaml_content.append("    validators:")
                    yaml_content.append("      - ref: competitor_check")
                    yaml_content.append("  output:")
                    yaml_content.append("    validators:")
                    yaml_content.append("      - ref: competitor_check")
                    yaml_content.append("      - ref: RestrictToTopic")
                    yaml_content.append("")

                # System prompt handling logic
                if len(sub_agents) > 1:
                    yaml_content.append("system_prompt: |\n  " + agent_config['instructions'].replace('\n', '\n  '))
                    yaml_content.append("")
                
                if agent_config['tags']:
                    yaml_content.append("tags:")
                    for tag in agent_config['tags']:
                        yaml_content.append(f"  - {tag}")
                
                if agent_config['env']:
                    yaml_content.append("env:")
                    for k, v in agent_config['env'].items():
                        yaml_content.append(f"  {k}: {v}")
                
                if agent_config['prompts']:
                    yaml_content.append("prompts:")
                    for p in agent_config['prompts']:
                        yaml_content.append(f"  - \"{p}\"")
                
                yaml_content.append("")
                yaml_content.append("crew_config:")
                yaml_content.append("  pattern: single")

                new_yaml = agents_config_dir / f"{agent_name}.yaml"
                new_yaml.write_text("\n".join(yaml_content) + "\n", encoding="utf-8")
            else:
                # Fallback for simple string input (e.g. from tests or simple args)
                if template_yaml.exists():
                    new_yaml = agents_config_dir / f"{agent_name}.yaml"
                    shutil.copy2(template_yaml, new_yaml)

        # Remove the template directory from the final project
        if server_template_dir.exists():
            shutil.rmtree(server_template_dir)
            
        # Remove the template.yaml after creating agent-specific configs
        if template_yaml.exists():
            template_yaml.unlink()

    def _update_dependencies(self):
        """Uncomment framework-specific dependencies in pyproject.toml and requirements.txt."""
        if not self.framework:
            return

        framework_map = {
            "langgraph": "oai-langgraph-core",
            "crewai": "oai-crewai-core",
            "strands": "oai-aws-strands-core",
            "openai": "oai-openai-core"
        }
        
        dep_name = framework_map.get(self.framework)
        if not dep_name:
            return

        # Update pyproject.toml
        pyproject_path = self.project_dir / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text(encoding="utf-8")
            pattern = rf'#\s*"{dep_name}",'
            if dep_name == "oai-langgraph-core":
                content = re.sub(r'#\s*"oai-langraph-core",', f'"{dep_name}",', content)
            
            content = re.sub(pattern, f'"{dep_name}",', content)
            pyproject_path.write_text(content, encoding="utf-8")

        # Update requirements.txt
        req_path = self.project_dir / "requirements.txt"
        if req_path.exists():
            content = req_path.read_text(encoding="utf-8")
            pattern = rf'#\s*({dep_name}\s*@\s*git\+https://github.com/Capgemini-Innersource/ptr_oai_agent_development_kit)'
            content = re.sub(pattern, r'\1', content)
            req_path.write_text(content, encoding="utf-8")

    def _render_files(self):
        """Walk every file and replace placeholder tokens."""
        title = self.project_name.replace("_", " ").replace("-", " ").title()

        replacements = {
            _TOKEN: self.project_name,
            _TOKEN_AUTHOR: self.author,
            _TOKEN_EMAIL: self.email,
            _TOKEN_DESC: self.description,
            _TOKEN_TITLE: title,
        }

        for path in self.project_dir.rglob("*"):
            if path.is_file():
                try:
                    text = path.read_text(encoding="utf-8")
                    for token, value in replacements.items():
                        text = text.replace(token, value)
                    path.write_text(text, encoding="utf-8")
                except UnicodeDecodeError:
                    pass  # skip binary files

    def _init_git(self):
        print("🔧  Initialising git repository …")
        try:
            subprocess.run(
                ["git", "init", "-q"],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "add", "."],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-q", "-m", "chore: initial project scaffold"],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("  ⚠  git not available — skipping.")

    def _create_venv(self):
        print("🐍  Creating virtual environment (.venv) …")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", ".venv"],
                cwd=self.project_dir,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            print("  ⚠  Could not create venv — skipping.")

    def _print_success(self):
        venv_activate = (
            "source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows"
        )
        print(f"\n✅  Project '{self.project_name}' created successfully!\n")
        print("  Next steps:\n")
        try:
            rel = self.project_dir.relative_to(Path.cwd())
        except ValueError:
            rel = self.project_dir
        print(f"    cd {rel}")
        print(f"    {venv_activate}")
        print("    pip install -e .[dev]")
        
        if self.template == "mcp":
            print("\n  🛠  MCP Setup Instructions:")
            print("    1. Update 'pyproject.toml' and 'requirements.txt' with any additional dependencies.")
            print("    2. Add necessary utility files in 'mcp_registry_servers/utils/'.")
            print("    3. Test your MCP server using the MCP Inspector or by running:")
            print("       python -m mcp_registry_servers.server")
        elif self.template == "agent":
            print("\n  🤖 Agent Setup Instructions:")
            print(f"    1. Framework selected: {self.framework}")
            print("    2. Update 'pyproject.toml' and 'requirements.txt' with any additional dependencies.")
            print("    3. Update the agent configuration in 'agentic_registry_agents/agents_config/<agent_name>.yaml'.")
            print("    4. Implement your agent logic in 'agentic_registry_agents/agents/<agent_name>/agent.py'.")
            print("    5. Run your agent server:")
            print("       python -m agentic_registry_agents.server")
        print()
