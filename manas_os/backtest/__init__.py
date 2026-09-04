"""Replay/backtest helpers for Manas OS.

NOTE: do not re-export `replay.replay` under the name `replay` here — it would
shadow the submodule on `import manas_os.backtest.replay` (PEP 328 getattr
binding), breaking module-level access to THIN_N/GENERATORS in tests.
"""

from manas_os.backtest.replay import format_ab_table, format_replay_table
from manas_os.backtest.replay import replay as run_replay

__all__ = ["format_replay_table", "format_ab_table", "run_replay"]
