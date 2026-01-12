from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_CATEGORIES = [
    "Work",
    "Social",
    "Video",
    "Gaming",
    "Reading",
    "Communication",
    "Idle",
    "Other",
]


@dataclass
class Rule:
    rule_id: int
    enabled: bool
    match_type: str
    process_pattern: str | None
    title_pattern: str | None
    category: str
    priority: int


@dataclass
class AppContext:
    process_name: str
    window_title: str


def match_rule(rule: Rule, context: AppContext) -> bool:
    if not rule.enabled:
        return False
    process_match = True
    title_match = True
    if rule.process_pattern:
        process_match = _match(rule.match_type, rule.process_pattern, context.process_name)
    if rule.title_pattern:
        title_match = _match(rule.match_type, rule.title_pattern, context.window_title)
    return process_match and title_match


def apply_rules(rules: list[Rule], context: AppContext) -> str:
    for rule in sorted(rules, key=lambda r: (r.priority, r.rule_id)):
        if match_rule(rule, context):
            return rule.category
    return "Other"


def _match(match_type: str, pattern: str, value: str) -> bool:
    value = value or ""
    if match_type == "regex":
        try:
            return re.search(pattern, value, re.IGNORECASE) is not None
        except re.error:
            return False
    return pattern.lower() in value.lower()

