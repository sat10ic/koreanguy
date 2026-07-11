"""Shadow-only alpha research primitives for sat10ic os.

This package is intentionally isolated from eligibility, governance and sizing.
It produces evidence and research diagnostics; it cannot place or size trades.
"""

from .schema import ensure_schema

__all__ = ["ensure_schema"]
