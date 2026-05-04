"""Message-format helpers for the Anthropic provider.

Anthropic's ``messages.create`` takes a separate ``system=`` string and a
``messages`` list that must not contain system-role entries.  These helpers
translate the OpenAI-style flat ``[{role, content}, ...]`` list that Conexus
uses internally.
"""

from __future__ import annotations

from app.llm.types import ChatMessage


def split_system(messages: list[ChatMessage]) -> tuple[str, list[ChatMessage]]:
    """Separate system-role messages from the conversation turn list.

    Returns a 2-tuple of:
    - ``system_text``: the concatenation of all leading ``system`` messages
      (joined by double newlines), ready to pass to Anthropic's ``system=``
      kwarg. Empty string when there are no system messages.
    - ``conversation``: the remaining messages without system entries.

    All system-role messages are stripped from the returned ``conversation``
    list regardless of their position, but their text is only appended to
    ``system_text`` if the ``content`` field is non-empty.

    Example::

        system, turns = split_system([
            {"role": "system", "content": "Be helpful."},
            {"role": "user",   "content": "Hi"},
        ])
        # system == "Be helpful."
        # turns  == [{"role": "user", "content": "Hi"}]
    """
    system_parts: list[str] = []
    rest: list[ChatMessage] = []
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content") or ""
            if content:
                system_parts.append(content)
        else:
            rest.append(msg)
    return "\n\n".join(system_parts), rest
