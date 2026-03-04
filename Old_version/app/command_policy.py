from __future__ import annotations

import json
from typing import Any, Iterable


def normalize_command_entry(entry: str) -> str:
    """Normalize allowlist entry by trimming whitespace and tabs."""
    if entry is None:
        return ""
    return str(entry).strip(" \t")


def normalize_command(command: str) -> str:
    """Normalize an incoming command string by trimming whitespace and tabs."""
    if command is None:
        return ""
    return str(command).strip(" \t")


def parse_allowed_commands(value: Any) -> list[str]:
    """Parse allowed commands from JSON list or comma-separated string."""
    if value is None:
        return []

    raw: list[str] = []
    if isinstance(value, (list, tuple, set)):
        raw = [str(item) for item in value]
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    raw = [str(item) for item in parsed]
                else:
                    raw = [text]
            except json.JSONDecodeError:
                raw = [item for item in text.split(",")]
        else:
            raw = [item for item in text.split(",")]
    else:
        raw = [str(value)]

    normalized = [normalize_command_entry(item) for item in raw]
    return [item for item in normalized if item]


def allow_any_enabled(settings) -> bool:
    """UNSAFE: bypass allowlist only when explicitly enabled."""
    return bool(getattr(settings, "unsafe_allow_any_commands", False))


def is_command_allowed(
    command: str,
    allowed_commands: Iterable[str],
    allow_any: bool,
) -> tuple[bool, str]:
    """Check if a command is allowed under the current allowlist policy."""
    normalized_command = normalize_command(command)
    if not normalized_command:
        return False, ""
    if allow_any:
        return True, normalized_command

    base_command = normalized_command.split()[0] if normalized_command else ""
    for allowed in allowed_commands:
        allowed_normalized = normalize_command_entry(allowed)
        if not allowed_normalized:
            continue
        if base_command == allowed_normalized:
            return True, normalized_command
        if (
            normalized_command == allowed_normalized
            or normalized_command.startswith(allowed_normalized + " ")
        ):
            return True, normalized_command

    return False, normalized_command
