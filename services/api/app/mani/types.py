"""Column types that differ between PostgreSQL and SQLite (the default test database)."""
import json

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, Text
from sqlalchemy.types import TypeDecorator

from app.mani.config import EMBEDDING_DIMENSIONS


class Embedding(TypeDecorator):
    """A vector(1024) on PostgreSQL. A JSON text on SQLite, which cannot search by
    similarity: tests that need real vector search run on PostgreSQL only."""

    impl = Text
    cache_ok = True

    class comparator_factory(TypeDecorator.Comparator):
        """pgvector's distance operators, for `order_by(Chunk.embedding.cosine_distance(v))`.
        PostgreSQL only; SQLite has no such operators."""

        def l2_distance(self, other):
            return self.op("<->", return_type=Float)(other)

        def max_inner_product(self, other):
            return self.op("<#>", return_type=Float)(other)

        def cosine_distance(self, other):
            return self.op("<=>", return_type=Float)(other)

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        values = [float(x) for x in value]
        if len(values) != self.dimensions:
            raise ValueError(f"An embedding has {self.dimensions} values, got {len(values)}.")
        return values if dialect.name == "postgresql" else json.dumps(values)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return [float(x) for x in value]
        return json.loads(value)
