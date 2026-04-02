"""Power CLI - AI-powered command interpretation and pattern recognition."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from aicp_cli.power.alias_resolver import AliasResolver
from aicp_cli.power.context_collector import ContextCollector
from aicp_cli.power.intent_detector import IntentDetector
from aicp_cli.power.skill_engine import SkillEngine
from aicp_cli.power.suggestion_engine import SuggestionEngine


@dataclass
class PowerCLIConfig:
    """Configuration for Power CLI behavior."""

    fuzzy_threshold: float = 0.6
    max_suggestions: int = 5
    alias_expansion_enabled: bool = True
    intent_detection_enabled: bool = True
    context_aware: bool = True
    skill_enabled: bool = True
    learn_patterns: bool = True
    pattern_store_path: str = ".aicp/patterns.json"


@dataclass
class InterpretationResult:
    """Result of CLI power interpretation."""

    original_input: str
    resolved_command: str
    resolved_args: dict[str, Any]
    intent: str | None
    confidence: float
    suggestions: list[str] = field(default_factory=list)
    skills_matched: list[str] = field(default_factory=list)
    aliases_expanded: list[str] = field(default_factory=list)
    context_used: dict[str, Any] = field(default_factory=list)
    transformation_log: list[str] = field(default_factory=list)


class PowerCLI:
    """AI-powered CLI with pattern recognition and intent detection."""

    def __init__(self, config: PowerCLIConfig | None = None):
        self.config = config or PowerCLIConfig()
        self._alias_resolver = AliasResolver()
        self._intent_detector = IntentDetector(
            threshold=self.config.fuzzy_threshold
        )
        self._context_collector = ContextCollector()
        self._suggestion_engine = SuggestionEngine(
            max_suggestions=self.config.max_suggestions
        )
        self._skill_engine = SkillEngine()

    def interpret(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> InterpretationResult:
        """Interpret user input and resolve to executable command."""
        
        log = []
        original_input = user_input
        current_input = user_input
        resolved_args = {}
        
        # Step 1: Collect context
        ctx = context or {}
        if self.config.context_aware:
            ctx = self._context_collector.collect(ctx)
            log.append(f"Context collected: {list(ctx.keys())}")
        
        # Step 2: Expand aliases (e.g., "gc" -> "git commit")
        if self.config.alias_expansion_enabled:
            expanded, alias_log = self._alias_resolver.resolve(current_input)
            if expanded != current_input:
                log.append(f"Alias expanded: '{current_input}' -> '{expanded}'")
                current_input = expanded
                ctx["_aliases_expanded"] = alias_log
        
        # Step 3: Match skills/macros (e.g., "deploy" -> workflow)
        if self.config.skill_enabled:
            skill_result, skill_log = self._skill_engine.execute(current_input, ctx)
            if skill_result:
                log.append(f"Skill matched: {skill_log.get('skill_name', 'unknown')}")
                return InterpretationResult(
                    original_input=original_input,
                    resolved_command=skill_result.get("command", ""),
                    resolved_args=skill_result.get("args", {}),
                    intent=skill_result.get("intent"),
                    confidence=skill_result.get("confidence", 1.0),
                    skills_matched=[skill_log.get("skill_name", "")],
                    transformation_log=log,
                )
        
        # Step 4: Intent detection
        intent = None
        confidence = 1.0
        if self.config.intent_detection_enabled:
            intent_result = self._intent_detector.detect(current_input, ctx)
            intent = intent_result.intent
            confidence = intent_result.confidence
            if intent_result.transformation:
                log.append(f"Intent transformed: {current_input} -> {intent_result.transformation}")
                current_input = intent_result.transformation
            
            # Parse command and args from intent
            parsed = self._parse_command_args(current_input)
            current_input = parsed["command"]
            resolved_args.update(parsed["args"])
        
        # Step 5: Generate suggestions
        suggestions = []
        if self.config.context_aware:
            suggestions = self._suggestion_engine.suggest(current_input, ctx)
            log.append(f"Generated {len(suggestions)} suggestions")
        
        return InterpretationResult(
            original_input=original_input,
            resolved_command=current_input,
            resolved_args=resolved_args,
            intent=intent,
            confidence=confidence,
            suggestions=suggestions,
            context_used=ctx,
            transformation_log=log,
        )

    def _parse_command_args(self, input_str: str) -> dict[str, Any]:
        """Parse command string into command + arguments."""
        parts = input_str.strip().split()
        if not parts:
            return {"command": "", "args": {}}
        
        command = parts[0]
        args = {}
        
        # Parse key=value arguments
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                args[key] = value
            else:
                args[f"arg_{len(args)}"] = part
        
        return {"command": command, "args": args}

    def register_alias(self, alias: str, expansion: str) -> None:
        """Register a new command alias."""
        self._alias_resolver.register(alias, expansion)

    def register_pattern(
        self,
        pattern: str,
        intent: str,
        transformation: str,
    ) -> None:
        """Register an intent pattern."""
        self._intent_detector.register_pattern(pattern, intent, transformation)

    def register_skill(
        self,
        name: str,
        pattern: str,
        command: str,
        args: dict[str, Any] | None = None,
    ) -> None:
        """Register a skill/macro."""
        self._skill_engine.register(name, pattern, command, args or {})

    def learn_from_execution(
        self,
        user_input: str,
        resolved_command: str,
        was_successful: bool,
    ) -> None:
        """Learn from execution to improve future interpretations."""
        if self.config.learn_patterns and was_successful:
            # Could store successful patterns for future matching
            pass