"""Topic categories. A category picks a topic's cover motif and its group in the topic picker
(DESIGN.md, Covers); a topic without one, such as an accepted suggestion, gets the plain cover."""

from typing import Literal, get_args

TopicCategory = Literal[
    "motorsport", "sport", "science", "climate", "business", "technology", "culture"
]
CATEGORIES: tuple[str, ...] = get_args(TopicCategory)
