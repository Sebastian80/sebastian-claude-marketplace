#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0", "rich>=13.0"]
# ///
"""
Skill Debugging Tool for Claude Code

Validates skill YAML frontmatter and tests trigger recognition.
Based on known Claude Code limitations (GitHub #9817).

Usage:
    uv run debug-skill.py validate <skill_path>     # Validate a single skill
    uv run debug-skill.py validate-all <plugin_dir> # Validate all skills in plugin
    uv run debug-skill.py test-trigger <skill_path> <query>  # Test if query triggers skill
    uv run debug-skill.py simulate <plugin_dir>     # Simulate skill discovery
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
except ImportError:
    print("Installing dependencies...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pyyaml", "rich"], check=True)
    import yaml
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

console = Console()


class SkillValidator:
    """Validates Claude Code skill YAML frontmatter."""

    # Known problematic patterns (checked against raw YAML frontmatter)
    YAML_ISSUES = [
        (r'description:\s*>\s*\n', 'YAML folded block scalar (>) - causes silent failure'),
        (r'description:\s*\|\s*\n', 'YAML literal block scalar (|) - risky, may fail'),
        (r'description:\s*\n\s+[^\s]', 'YAML implicit multiline - causes silent failure'),
    ]

    # Character limits
    MAX_DESCRIPTION_LENGTH = 1024
    MAX_NAME_LENGTH = 64
    RECOMMENDED_DESC_LENGTH = 500

    def __init__(self, skill_path: Path):
        self.skill_path = skill_path
        self.content = skill_path.read_text()
        self.frontmatter = self._extract_frontmatter()
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def _extract_frontmatter(self) -> Optional[dict]:
        """Extract and parse YAML frontmatter."""
        if not self.content.startswith('---'):
            return None

        parts = self.content.split('---', 2)
        if len(parts) < 3:
            return None

        try:
            return yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parse error: {e}")
            return None

    def validate(self) -> bool:
        """Run all validation checks."""
        self._check_frontmatter_exists()
        self._check_yaml_patterns()
        self._check_name_field()
        self._check_description_field()
        self._check_description_quality()
        return len(self.errors) == 0

    def _check_frontmatter_exists(self):
        """Verify frontmatter is present and parseable."""
        if self.frontmatter is None:
            self.errors.append("No valid YAML frontmatter found")

    def _check_yaml_patterns(self):
        """Check for problematic YAML patterns in raw content."""
        fm_section = self.content.split('---')[1] if '---' in self.content else ''

        for pattern, message in self.YAML_ISSUES:
            if re.search(pattern, fm_section, re.MULTILINE):
                self.errors.append(f"Problematic YAML: {message}")

    def _check_name_field(self):
        """Validate the name field."""
        if not self.frontmatter:
            return

        name = self.frontmatter.get('name', '')

        if not name:
            self.errors.append("Missing 'name' field")
            return

        if len(name) > self.MAX_NAME_LENGTH:
            self.errors.append(f"Name too long: {len(name)} chars (max {self.MAX_NAME_LENGTH})")

        if not re.match(r'^[a-z0-9-]+$', name):
            self.warnings.append(f"Name should be lowercase letters, numbers, hyphens only: '{name}'")

    def _check_description_field(self):
        """Validate the description field."""
        if not self.frontmatter:
            return

        desc = self.frontmatter.get('description', '')

        if not desc:
            self.errors.append("Missing 'description' field")
            return

        if not isinstance(desc, str):
            self.errors.append(f"Description is not a string: {type(desc)}")
            return

        if len(desc) > self.MAX_DESCRIPTION_LENGTH:
            self.errors.append(f"Description too long: {len(desc)} chars (max {self.MAX_DESCRIPTION_LENGTH})")
        elif len(desc) > self.RECOMMENDED_DESC_LENGTH:
            self.warnings.append(f"Description is long: {len(desc)} chars (recommended <{self.RECOMMENDED_DESC_LENGTH})")

        # Check if it's likely truncated (from YAML block scalar issue)
        if desc.strip() in ('>', '|', ''):
            self.errors.append("Description appears truncated - likely YAML block scalar issue")

    def _check_description_quality(self):
        """Check description quality for trigger recognition."""
        if not self.frontmatter:
            return

        desc = self.frontmatter.get('description', '')
        if not desc or not isinstance(desc, str):
            return

        # Check for recommended patterns
        if not re.search(r'use when|when to use|triggers?|keywords?', desc, re.IGNORECASE):
            self.warnings.append("Description should include 'Use when...' or trigger conditions")

        if desc[0].islower():
            self.info.append("Consider starting description with capital letter")

    def get_trigger_keywords(self) -> list[str]:
        """Extract potential trigger keywords from description."""
        if not self.frontmatter:
            return []

        desc = self.frontmatter.get('description', '')
        if not desc:
            return []

        # Extract quoted terms and significant words
        quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", desc)
        keywords = [q[0] or q[1] for q in quoted]

        # Extract parenthetical examples
        parens = re.findall(r'\(([^)]+)\)', desc)
        for p in parens:
            keywords.extend([w.strip() for w in p.split(',')])

        return [k for k in keywords if len(k) > 2]

    def print_report(self):
        """Print validation report."""
        status = "✅ VALID" if len(self.errors) == 0 else "❌ INVALID"
        color = "green" if len(self.errors) == 0 else "red"

        console.print(Panel(
            f"[bold]{self.skill_path.name}[/bold]\n{self.skill_path}",
            title=f"[{color}]{status}[/{color}]",
            box=box.ROUNDED
        ))

        if self.frontmatter:
            table = Table(show_header=False, box=box.SIMPLE)
            table.add_column("Field", style="cyan")
            table.add_column("Value")

            name = self.frontmatter.get('name', 'N/A')
            desc = self.frontmatter.get('description', 'N/A')
            desc_preview = desc[:80] + '...' if len(str(desc)) > 80 else desc

            table.add_row("Name", str(name))
            table.add_row("Description", str(desc_preview))
            table.add_row("Desc Length", f"{len(str(desc))} chars")

            console.print(table)

        if self.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for e in self.errors:
                console.print(f"  ❌ {e}")

        if self.warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for w in self.warnings:
                console.print(f"  ⚠️  {w}")

        if self.info:
            console.print("\n[bold blue]Info:[/bold blue]")
            for i in self.info:
                console.print(f"  ℹ️  {i}")

        keywords = self.get_trigger_keywords()
        if keywords:
            console.print(f"\n[bold]Trigger Keywords:[/bold] {', '.join(keywords[:10])}")


class TriggerTester:
    """Test if a query would trigger a skill."""

    def __init__(self, skill_path: Path):
        self.validator = SkillValidator(skill_path)
        self.validator.validate()

    def test_query(self, query: str) -> tuple[bool, float, list[str]]:
        """
        Test if a query would likely trigger the skill.
        Returns (would_trigger, confidence, matched_keywords).
        """
        if not self.validator.frontmatter:
            return False, 0.0, []

        desc = self.validator.frontmatter.get('description', '').lower()
        name = self.validator.frontmatter.get('name', '').lower()
        query_lower = query.lower()

        matches = []

        # Check name match
        if name in query_lower or query_lower in name:
            matches.append(f"name:{name}")

        # Check keyword matches
        keywords = self.validator.get_trigger_keywords()
        for kw in keywords:
            if kw.lower() in query_lower:
                matches.append(f"keyword:{kw}")

        # Check common trigger words
        trigger_words = ['jira', 'ticket', 'issue', 'search', 'find', 'create', 'update', 'transition']
        for tw in trigger_words:
            if tw in query_lower and tw in desc:
                matches.append(f"trigger:{tw}")

        # Check issue key pattern
        if re.search(r'[A-Z]+-\d+', query):
            if 'issue' in desc or 'ticket' in desc or 'proj-' in desc.lower():
                matches.append("pattern:issue-key")

        # Calculate confidence
        confidence = min(1.0, len(matches) * 0.3)
        would_trigger = confidence >= 0.3

        return would_trigger, confidence, matches


def find_skills(plugin_dir: Path) -> list[Path]:
    """Find all SKILL.md files in a plugin directory."""
    skills_dir = plugin_dir / 'skills'
    if not skills_dir.exists():
        return []
    return list(skills_dir.glob('*/SKILL.md'))


def cmd_validate(args):
    """Validate a single skill."""
    skill_path = Path(args.skill_path)
    if not skill_path.exists():
        console.print(f"[red]File not found: {skill_path}[/red]")
        sys.exit(1)

    validator = SkillValidator(skill_path)
    validator.validate()
    validator.print_report()

    sys.exit(0 if len(validator.errors) == 0 else 1)


def cmd_validate_all(args):
    """Validate all skills in a plugin."""
    plugin_dir = Path(args.plugin_dir)
    skills = find_skills(plugin_dir)

    if not skills:
        console.print(f"[yellow]No skills found in {plugin_dir}[/yellow]")
        sys.exit(1)

    console.print(f"[bold]Found {len(skills)} skills[/bold]\n")

    total_errors = 0
    for skill_path in skills:
        validator = SkillValidator(skill_path)
        validator.validate()
        validator.print_report()
        total_errors += len(validator.errors)
        console.print()

    # Summary
    console.print(Panel(
        f"Total skills: {len(skills)}\nWith errors: {sum(1 for s in skills if SkillValidator(s).validate() is False)}",
        title="Summary",
        box=box.ROUNDED
    ))

    sys.exit(0 if total_errors == 0 else 1)


def cmd_test_trigger(args):
    """Test if a query would trigger a skill."""
    skill_path = Path(args.skill_path)
    if not skill_path.exists():
        console.print(f"[red]File not found: {skill_path}[/red]")
        sys.exit(1)

    tester = TriggerTester(skill_path)
    would_trigger, confidence, matches = tester.test_query(args.query)

    console.print(Panel(
        f"Query: [bold]{args.query}[/bold]",
        title="Trigger Test",
        box=box.ROUNDED
    ))

    status = "✅ WOULD TRIGGER" if would_trigger else "❌ WOULD NOT TRIGGER"
    color = "green" if would_trigger else "red"

    console.print(f"\nResult: [{color}]{status}[/{color}]")
    console.print(f"Confidence: {confidence:.0%}")

    if matches:
        console.print(f"\nMatches: {', '.join(matches)}")
    else:
        console.print("\n[yellow]No keyword matches found[/yellow]")
        console.print("Consider adding more trigger keywords to description")


def cmd_simulate(args):
    """Simulate skill discovery like Claude Code would."""
    plugin_dir = Path(args.plugin_dir)
    skills = find_skills(plugin_dir)

    if not skills:
        console.print(f"[yellow]No skills found in {plugin_dir}[/yellow]")
        sys.exit(1)

    console.print(Panel(
        "Simulating how Claude Code would discover skills",
        title="Skill Discovery Simulation",
        box=box.ROUNDED
    ))

    table = Table(title="Discovered Skills", box=box.ROUNDED)
    table.add_column("Skill", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Description Preview")

    for skill_path in skills:
        validator = SkillValidator(skill_path)
        is_valid = validator.validate()

        name = validator.frontmatter.get('name', 'UNKNOWN') if validator.frontmatter else 'PARSE_ERROR'
        desc = validator.frontmatter.get('description', '') if validator.frontmatter else ''

        # Simulate what Claude would see
        if not is_valid:
            status = "[red]❌ Hidden[/red]"
            desc_preview = "[red]Not discoverable due to YAML issues[/red]"
        elif not desc or desc in ('>', '|'):
            status = "[yellow]⚠️ Broken[/yellow]"
            desc_preview = f"[yellow]Truncated: '{desc}'[/yellow]"
        else:
            status = "[green]✅ Visible[/green]"
            desc_preview = desc[:60] + '...' if len(desc) > 60 else desc

        table.add_row(name, status, desc_preview)

    console.print(table)

    # Show what would appear in system prompt
    console.print("\n[bold]System Prompt Preview:[/bold]")
    console.print("```")
    for skill_path in skills:
        validator = SkillValidator(skill_path)
        validator.validate()
        if validator.frontmatter and len(validator.errors) == 0:
            name = validator.frontmatter.get('name', '')
            desc = validator.frontmatter.get('description', '')
            console.print(f"<skill>")
            console.print(f"<name>{name}</name>")
            console.print(f"<description>{desc}</description>")
            console.print(f"</skill>")
    console.print("```")


def main():
    parser = argparse.ArgumentParser(
        description="Skill Debugging Tool for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s validate skills/jira-communication/SKILL.md
  %(prog)s validate-all ~/.claude/plugins/marketplaces/my-plugin
  %(prog)s test-trigger skills/jira-communication/SKILL.md "find HMKG-123"
  %(prog)s simulate ~/.claude/plugins/marketplaces/my-plugin
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # validate
    p_validate = subparsers.add_parser('validate', help='Validate a single skill')
    p_validate.add_argument('skill_path', help='Path to SKILL.md')
    p_validate.set_defaults(func=cmd_validate)

    # validate-all
    p_validate_all = subparsers.add_parser('validate-all', help='Validate all skills in plugin')
    p_validate_all.add_argument('plugin_dir', help='Path to plugin directory')
    p_validate_all.set_defaults(func=cmd_validate_all)

    # test-trigger
    p_test = subparsers.add_parser('test-trigger', help='Test if query triggers skill')
    p_test.add_argument('skill_path', help='Path to SKILL.md')
    p_test.add_argument('query', help='Query to test')
    p_test.set_defaults(func=cmd_test_trigger)

    # simulate
    p_simulate = subparsers.add_parser('simulate', help='Simulate skill discovery')
    p_simulate.add_argument('plugin_dir', help='Path to plugin directory')
    p_simulate.set_defaults(func=cmd_simulate)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
