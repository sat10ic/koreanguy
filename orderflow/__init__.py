"""Order-flow layer — entry-quality and failure detection from live book data.

Greenfield package (build manual: ``plan/ORDERFLOW_BUILD_MANUAL.md``).
Phase 0 (this package's only code so far) is the feed-capability measurement
apparatus: canonical schemas, the FYERS adapter, the websocket manager and the
capability auditor. It never contacts the live feed by itself; the owner runs
live sessions.

Standing boundaries for every file in this package:

* No ``import traderlog``, no ``import manas_os``. Adopt by copying with a
  provenance header (worked example: ``traderlog/adopted/activity.py``).
* No order routing, no position sizing advice. Ever (manual R8).
* Credentials never enter this package: no env reads, no config reads. The
  owner supplies auth out-of-band (manual R7).
* Raw-FYERS field knowledge lives in exactly one file,
  ``orderflow/market_data/fyers_adapter.py``. Everything downstream speaks the
  canonical models from ``schemas.py`` only.
* Missing source fields are ``None``, never invented (manual R5).
"""
