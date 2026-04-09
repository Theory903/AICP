"""
AICP GitHub Integration Module
Based on: https://github.com/anthropics/claude-code-action
"""

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

DEFAULT_STUDY_PATH = Path(__file__).parent.parent.parent.parent.parent / "ref" / "study"


class ExecutionMode(Enum):
    AUTO = "auto"
    REVIEW = "review"
    IMPLEMENT = "implement"
    QUESTION = "question"


class CloudProvider(Enum):
    ANTHROPIC = "anthropic"
    AWS_BEDROCK = "aws-bedrock"
    GOOGLE_VERTEX = "google-vertex"
    AZURE = "azure"


@dataclass
class ActionConfig:
    prompt: str = ""
    claude_args: list[str] = field(default_factory=list)
    mode: ExecutionMode = ExecutionMode.AUTO
    provider: CloudProvider = CloudProvider.ANTHROPIC

    github_token: str | None = None
    anthropic_api_key: str | None = None

    mcp_servers: list[str] = field(default_factory=list)
    mcp_permissions: dict[str, str] = field(default_factory=dict)

    max_iterations: int = 100
    checkout_repo: bool = True

    def to_env(self) -> dict[str, str]:
        env = {}

        if self.github_token:
            env["GITHUB_TOKEN"] = self.github_token
        if self.anthropic_api_key:
            env["ANTHROPIC_API_KEY"] = self.anthropic_api_key

        env["CLAUDE_ACTION_MODE"] = self.mode.value

        return env

    def to_action_inputs(self) -> dict[str, str]:
        """Convert config to GitHub Action inputs."""
        inputs = {}

        if self.prompt:
            inputs["prompt"] = self.prompt
        if self.claude_args:
            inputs["claude_args"] = json.dumps(self.claude_args)

        inputs["mode"] = self.mode.value

        return inputs


@dataclass
class WorkflowTrigger:
    on_pr: bool = True
    on_issue: bool = True
    on_mention: bool = True
    on_schedule: str | None = None

    paths: list[str] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)

    @classmethod
    def pr_review_only(cls) -> "WorkflowTrigger":
        return cls(on_pr=True, on_issue=False, on_mention=False)

    @classmethod
    def issue_triage(cls) -> "WorkflowTrigger":
        return cls(on_pr=False, on_issue=True, on_mention=True)


class GitHubActionGenerator:
    def __init__(self, config: ActionConfig, trigger: WorkflowTrigger):
        self.config = config
        self.trigger = trigger

    def generate_workflow(self) -> str:
        lines = [
            "name: Claude Code",
            "",
            "on:",
        ]

        # Build trigger conditions
        triggers = []
        if self.trigger.on_pr:
            triggers.extend([
                "  pull_request:",
                "    types: [opened, synchronize, reopened]",
            ])
            if self.trigger.paths:
                lines.append("    paths:")
                for p in self.trigger.paths:
                    lines.append(f'      - "{p}"')

        if self.trigger.on_issue:
            triggers.append("  issues:")

        if self.trigger.on_mention:
            triggers.append("  issue_comment:")
            triggers.append("  pull_request_review_comment:")

        if self.trigger.on_schedule:
            triggers.append("  schedule:")
            triggers.append(f'    - cron: "{self.trigger.on_schedule}"')

        lines.extend(triggers)
        lines.extend([
            "",
            "jobs:",
            "  claude:",
            "    runs-on: ubuntu-latest",
            "    steps:",
            "      - name: Checkout",
            "        if: ${{ github.event_name == 'pull_request' }}",
            "        uses: actions/checkout@v4",
            "        with:",
            "          fetch-depth: 0",
            "",
            "      - name: Run Claude Code",
            "        uses: anthropics/claude-code-action@v1",
            "        with:",
        ])

        # Add inputs
        if self.config.prompt:
            lines.append('          prompt: |')
            for line in self.config.prompt.split("\n"):
                lines.append(f"            {line}")

        if self.config.claude_args:
            lines.append(f"          claude_args: '{' '.join(self.config.claude_args)}'")

        lines.append(f"          mode: {self.config.mode.value}")

        lines.extend([
            "        env:",
            "          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}",
            "          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}",
        ])

        return "\n".join(lines)

    def save_workflow(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.generate_workflow())


@dataclass
class PRReviewConfig:
    check_security: bool = True
    check_performance: bool = True
    check_tests: bool = True
    require_tests: bool = False

    paths_critical: list[str] = field(default_factory=list)

    @classmethod
    def security_focused(cls) -> "PRReviewConfig":
        return cls(check_security=True, check_performance=False, check_tests=False)

    def to_prompt(self) -> str:
        prompt_parts = [
            "Review this pull request with focus on:"
        ]

        if self.check_security:
            prompt_parts.append("- Security vulnerabilities")
        if self.check_performance:
            prompt_parts.append("- Performance implications")
        if self.check_tests:
            prompt_parts.append("- Test coverage and quality")

        if self.require_tests:
            prompt_parts.append("- Ensure tests are required for new code")

        if self.paths_critical:
            prompt_parts.append(f"\nPay extra attention to: {', '.join(self.paths_critical)}")

        return "\n".join(prompt_parts)


class ClaudeCodeRunner:
    def __init__(self, config: ActionConfig):
        self.config = config

    def build_cli_args(self) -> list[str]:
        args = ["--mode", self.config.mode.value]

        if self.config.prompt:
            args.extend(["--prompt", self.config.prompt])

        args.extend(self.config.claude_args)

        return args

    def get_action_inputs(self) -> dict[str, str]:
        return {
            "prompt": self.config.prompt,
            "claude_args": " ".join(self.config.claude_args),
            "mode": self.config.mode.value,
        }


def create_pr_review_workflow(
    output_path: Path,
    prompt: str | None = None,
    check_security: bool = True,
) -> Path:
    config = ActionConfig(
        prompt=prompt or "Review this pull request. Check for bugs, security issues, code quality, and provide constructive feedback.",
        mode=ExecutionMode.REVIEW,
    )
    trigger = WorkflowTrigger.pr_review_only()

    generator = GitHubActionGenerator(config, trigger)
    generator.save_workflow(output_path)

    return output_path


def create_issue_triage_workflow(
    output_path: Path,
    prompt: str | None = None,
) -> Path:
    """Create an issue triage workflow."""
    config = ActionConfig(
        prompt=prompt or "Analyze this issue. Add appropriate labels, prioritize, and provide initial assessment.",
        mode=ExecutionMode.QUESTION,
    )
    trigger = WorkflowTrigger(on_pr=False, on_issue=True, on_mention=True)

    generator = GitHubActionGenerator(config, trigger)
    generator.save_workflow(output_path)

    return output_path


__all__ = [
    "ActionConfig",
    "WorkflowTrigger",
    "GitHubActionGenerator",
    "PRReviewConfig",
    "ClaudeCodeRunner",
    "ExecutionMode",
    "CloudProvider",
    "create_pr_review_workflow",
    "create_issue_triage_workflow",
    "DEFAULT_STUDY_PATH",
]
