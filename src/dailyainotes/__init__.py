"""Daily AI Notes: AI takes notes on what's happening, every day, on the things you care about."""

import warnings

# langchain-core imports its Pydantic v1 shim at startup and warns on Python 3.14; we use no
# Pydantic v1 API. pyproject.toml filters the same warning for pytest.
warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14",
    category=UserWarning,
)
