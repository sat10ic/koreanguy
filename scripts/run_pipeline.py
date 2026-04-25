"""Pipeline orchestrator — runs the full daily pipeline end-to-end.

fetch_yf -> indicators -> regime -> screen -> verify -> track

Each stage updates a shared status dict (passed in) so the FastAPI backend can
stream progress to the dashboard.
"""
import os
import sys
import time
import traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import fetch_yf, indicators, regime, screen, verify, track, _db, _grade_helper


def _now():
    return datetime.now(timezone.utc).isoformat()


def run_full_pipeline(status: dict | None = None, max_symbols: int | None = None):
    """Run all stages sequentially. Updates `status` dict in place if given."""
    if status is None:
        status = {}
    # Always run from the project root so 'output/' and 'logs/' write to /app
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    status.update({
        'running': True,
        'started_at': _now(),
        'finished_at': None,
        'stages': [],
        'error': None,
        'current_stage': None,
        'progress': {'done': 0, 'total': 0, 'symbol': '', 'detail': ''},
    })

    def stage_log(name, payload=None, ok=True):
        status['stages'].append({
            'name': name,
            'ok': ok,
            'ts': _now(),
            'detail': payload,
        })

    try:
        # Stage 1: fetch
        status['current_stage'] = 'fetch'
        def _pcb(i, t, s, st):
            status['progress'] = {'done': i, 'total': t, 'symbol': s, 'detail': st}
        fetch_summary = fetch_yf.run_fetch(progress_cb=_pcb, max_symbols=max_symbols)
        stage_log('fetch', fetch_summary)

        # Stage 2: indicators
        status['current_stage'] = 'indicators'
        ind_summary = indicators.run_indicators(progress_cb=_pcb)
        stage_log('indicators', ind_summary)

        # clear grade cache between runs
        _grade_helper.clear_cache()

        # Stage 3: regime
        status['current_stage'] = 'regime'
        feat_conn = _db.features_conn()
        result = regime.evaluate_regime(feat_conn)
        if result:
            os.makedirs('output', exist_ok=True)
            import json as _json
            with open('output/regime_today.json', 'w') as f:
                _json.dump(result, f, indent=2)
            stage_log('regime', {'regime': result['regime'], 'pillars_passed': result['pillars_passed'], 'date': result['date']})
        else:
            stage_log('regime', {'msg': 'no data'}, ok=False)

        # Stage 4: screen
        status['current_stage'] = 'screen'
        screen_df = screen.run_screen(_db.features_conn(), _db.ohlcv_conn())
        stage_log('screen', {'rows': 0 if screen_df is None else len(screen_df)})

        # Stage 5: verify
        status['current_stage'] = 'verify'
        verify.run_verify()
        stage_log('verify', {'msg': 'ok'})

        # Stage 6: track
        status['current_stage'] = 'track'
        track.run_track()
        stage_log('track', {'msg': 'ok'})

    except Exception as e:
        status['error'] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        stage_log('error', status['error'], ok=False)
    finally:
        status['running'] = False
        status['finished_at'] = _now()
        status['current_stage'] = None

    return status


if __name__ == '__main__':
    s = {}
    run_full_pipeline(s)
    print({k: v for k, v in s.items() if k != 'stages'})
    for stg in s['stages']:
        print(stg)
