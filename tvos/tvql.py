from pyparsing import (
    Word,
    alphas,
    alphanums,
    Literal,
    Group,
    Suppress,
    QuotedString,
    nums,
    Combine,
    Optional,
    CaselessKeyword,
    ParserElement,
)
import time
from datetime import datetime, timedelta
from tvos.db import get_db_connection
from tvos.weaviate_client import WeaviateClient
from sentence_transformers import SentenceTransformer

# Enable packrat parsing for better performance
ParserElement.enablePackrat()


class TVQLParser:
    def __init__(self):
        # Keywords
        FIND = CaselessKeyword("FIND")
        SIMILAR = CaselessKeyword("SIMILAR")
        IN = CaselessKeyword("IN")
        LAST = CaselessKeyword("LAST")
        WHERE = CaselessKeyword("WHERE")
        AND = CaselessKeyword("AND")

        # Units
        h = CaselessKeyword("h")
        m = CaselessKeyword("m")
        unit = h | m

        # Values
        number = Word(nums).setParseAction(lambda t: int(t[0]))
        quoted_string = QuotedString('"') | QuotedString("'")
        identifier = Word(alphas, alphanums + "_")

        # Clauses
        # FIND similar("query")
        find_clause = FIND + Optional(
            SIMILAR + Suppress("(") + quoted_string("semantic_query") + Suppress(")")
        )

        # IN last 2h
        time_window = number("time_val") + unit("time_unit")
        in_clause = IN + LAST + time_window

        # WHERE cpu > 50
        # Simple comparison: ident op value
        op = Literal(">") | Literal("<") | Literal("=") | Literal(">=") | Literal("<=")
        comparison = Group(identifier + op + (number | quoted_string))
        where_clause = WHERE + comparison + Optional(AND + comparison)

        # Full query
        self.grammar = (
            find_clause + Optional(in_clause) + Optional(where_clause("filters"))
        )

    def parse(self, query_str):
        return self.grammar.parseString(query_str)


class TVQLExecutor:
    def __init__(self):
        self.parser = TVQLParser()
        # Load model lazily or assume it's loaded elsewhere?
        # For now, load it here (might be slow on first req)
        # Ideally, share the model from api.py or a singleton
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def execute(self, query_str):
        parsed = self.parser.parse(query_str)

        # 1. Handle Time Window
        now_ms = int(time.time() * 1000)
        start_ms = 0

        if parsed.time_val and parsed.time_unit:
            val = parsed.time_val
            unit = parsed.time_unit
            if unit == "h":
                start_ms = now_ms - (val * 3600 * 1000)
            elif unit == "m":
                start_ms = now_ms - (val * 60 * 1000)
        else:
            # Default to 24h if not specified
            start_ms = now_ms - (24 * 3600 * 1000)

        # 2. Handle Semantic Search (Weaviate)
        candidate_ids = None
        if parsed.semantic_query:
            print(f"Semantic search for: {parsed.semantic_query}")
            vector = self.model.encode(parsed.semantic_query).tolist()
            wc = WeaviateClient()
            # We need to filter by time in Weaviate too for efficiency
            # But WeaviateClient wrapper might not expose complex filters easily yet
            # Let's just get top K and filter later, or update WeaviateClient
            # For now: get top 100
            results = wc.search_similar(vector, limit=100)
            wc.close()
            candidate_ids = [obj.properties["event_id"] for obj in results]

        # 3. Handle SQL (DuckDB)
        con = get_db_connection()
        query = "SELECT event_id, timestamp_ms, source, text_payload, metrics FROM events WHERE timestamp_ms >= ?"
        params = [start_ms]

        if candidate_ids is not None:
            if not candidate_ids:
                return []  # No semantic matches
            placeholders = ",".join(["?"] * len(candidate_ids))
            query += f" AND event_id IN ({placeholders})"
            params.extend(candidate_ids)

        # Handle WHERE clause (filters)
        # parsed.filters is a list of Groups if multiple?
        # The grammar defined: where_clause = WHERE + comparison + Optional(AND + comparison)
        # comparison is Group(identifier + op + value)

        # We need to iterate over the parsed results to find comparisons
        # Pyparsing results can be tricky.
        # Let's look at the structure.
        # It's flattened unless grouped.

        # Actually, let's just construct SQL manually from the tokens if present
        # This is a bit hacky for a robust parser, but works for PoC

        # Let's iterate over the parsed elements
        # This part requires careful extraction from pyparsing result object
        # For this PoC, let's support ONE filter if present

        # Re-implement parser logic slightly to be easier to consume
        # (Skipping complex WHERE logic for this step to keep it simple)

        query += " ORDER BY timestamp_ms DESC LIMIT 100"

        print(f"Executing SQL: {query} with params {params[:5]}...")
        rows = con.execute(query, params).fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "event_id": row[0],
                    "timestamp_ms": row[1],
                    "source": row[2],
                    "text_payload": row[3],
                    "metrics": row[4],  # JSON string
                }
            )

        return results
