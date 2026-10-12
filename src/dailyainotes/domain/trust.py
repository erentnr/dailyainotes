"""Starting trust for a publisher, by kind (INTENT.md, Architectural Constraints).

A primary source is trusted most for claims about itself; user-generated content can support
only "X said Y".
"""

from typing import Literal

PublisherKind = Literal["primary", "wire", "editorial", "specialist", "user_generated", "unknown"]

TRUST_PRIOR: dict[PublisherKind, float] = {
    "primary": 0.85,
    "wire": 0.80,
    "editorial": 0.75,
    "specialist": 0.60,
    "unknown": 0.50,
    "user_generated": 0.35,
}
