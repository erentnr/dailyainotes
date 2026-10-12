"""The embedding model every vector in the database comes from.

A constant, not a setting: changing the model means a migration and re-embedding everything.
"""

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384
