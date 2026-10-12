"""Checking an Ask answer while it streams: citation markers that point at no source are
dropped, and a model that answers NOT_ENOUGH shows nothing of it."""

import re

NOT_ENOUGH = "Not enough in the notes to answer that."
# What the model answers when the notes do not cover the question.
NOT_ENOUGH_REPLY = "NOT_ENOUGH"
# A marker with the space before it, so a dropped one leaves no double space.
MARKER = re.compile(r"(\s?)\[(\d+)\]")
# An unfinished marker at the end of the text so far: "[" or "[1".
OPEN_MARKER = re.compile(r"\s?\[\d*$")


class AnswerFilter:
    def __init__(self, sources: int) -> None:
        self.allowed = set(range(1, sources + 1))
        self.cited: list[int] = []
        self.insufficient = False
        self._pending = ""
        self._started = False

    def feed(self, chunk: str) -> str:
        """The part of the answer that is safe to show now."""
        self._pending += chunk
        if self.insufficient:
            return ""
        if not self._started:
            head = self._pending.lstrip()
            if NOT_ENOUGH_REPLY.startswith(head):
                return ""  # could still become NOT_ENOUGH
            if head.startswith(NOT_ENOUGH_REPLY):
                self.insufficient = True
                return ""
            self._started = True
            self._pending = head
        # Hold back an unfinished marker, and trailing space a dropped marker would orphan.
        open_marker = OPEN_MARKER.search(self._pending)
        cut = open_marker.start() if open_marker else len(self._pending.rstrip())
        ready, self._pending = self._pending[:cut], self._pending[cut:]
        return self._clean(ready)

    def flush(self) -> str:
        """The rest, once the stream has ended."""
        if not self._started and NOT_ENOUGH_REPLY.startswith(self._pending.strip()):
            self.insufficient = True
        if self.insufficient:
            return ""
        rest, self._pending = self._pending, ""
        return self._clean(rest)

    def _clean(self, text: str) -> str:
        def keep_or_drop(match: re.Match[str]) -> str:
            marker = int(match.group(2))
            if marker not in self.allowed:
                return ""
            if marker not in self.cited:
                self.cited.append(marker)
            return match.group(0)

        return MARKER.sub(keep_or_drop, text)
