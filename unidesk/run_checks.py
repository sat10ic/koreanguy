"""Path shim mirroring traderlog/run_checks.py: makes the check runnable from
any cwd and ignores ambient PYTHONPATH so the repo's packages resolve
deterministically."""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unidesk.checks.runner import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
