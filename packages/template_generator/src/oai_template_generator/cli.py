"""Python Project Template Builder CLI."""

import argparse
import sys
from pathlib import Path

from oai_template_generator.builder import ProjectBuilder
from oai_template_generator.prompts import prompt_project_details, confirm


def main():
    parser = argparse.ArgumentParser(
        prog="pytemplate",
        description="🚀 Python Project Template Builder — scaffold agent or MCP projects instantly.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- new command ---
    new_parser = subparsers.add_parser("new", help="Create a new project from a template")
    new_parser.add_argument(
        "template",
        choices=["agent", "mcp"],
        nargs="?",
        help="Template type: 'agent' or 'mcp'",
    )
    new_parser.add_argument("name", nargs="?", help="Project name")
    new_parser.add_argument(
        "--output-dir",
        "-o",
        default=".",
        help="Directory to create the project in (default: current directory)",
    )
    new_parser.add_argument(
        "--author", "-a", default="", help="Author name"
    )
    new_parser.add_argument(
        "--email", "-e", default="", help="Author email"
    )
    new_parser.add_argument(
        "--description", "-d", default="", help="Project description"
    )
    new_parser.add_argument(
        "--no-git", action="store_true", help="Skip git initialization"
    )
    new_parser.add_argument(
        "--no-venv", action="store_true", help="Skip virtual environment creation"
    )

    # --- list command ---
    subparsers.add_parser("list", help="List available templates")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "list":
        _list_templates()
        return

    if args.command == "new":
        _handle_new(args)


def _list_templates():
    print("\n📦 Available Templates\n")
    print("  agent  — Autonomous AI agent with tool use, memory, and configurable LLM backend")
    print("  mcp    — Model Context Protocol server with resources, prompts, and tools\n")


def _handle_new(args):
    # Interactive prompts for missing values
    template, name, author, email, output_dir_str, description, items, framework = prompt_project_details(
        template=args.template,
        name=args.name,
        author=args.author,
        email=args.email,
        output_dir=args.output_dir,
        description=args.description,
    )

    output_dir = Path(output_dir_str).resolve()
    project_dir = output_dir / name
    
    overwrite = False
    if project_dir.exists():
        if confirm(f"⚠  Directory '{project_dir}' already exists. Overwrite?", default=False):
            overwrite = True
        else:
            print("Aborted.")
            sys.exit(0)

    builder = ProjectBuilder(
        template=template,
        project_name=name,
        author=author,
        email=email,
        description=description,
        output_dir=output_dir,
        init_git=not args.no_git,
        create_venv=not args.no_venv,
        items=items,
        framework=framework,
        overwrite=overwrite,
    )

    builder.build()

if __name__ == "__main__":
    main()
