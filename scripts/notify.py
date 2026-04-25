import io
import os
import sys
import json
import logging
import re
import pandas as pd
import requests

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _config, _db

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('notify')
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fh = logging.FileHandler('logs/notify.log')
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger

logger = setup_logger()
config = _config.load_config()

MDV2_SPECIAL = r'_*[]()~`>#+-=|{}.!\\'

def md_escape(s):
    s = str(s) if s is not None else ''
    return re.sub(r'([_\*\[\]\(\)~`>#\+\-=\|\{\}\.!\\])', r'\\\1', s)


def send_telegram(text):
    token = (
        getattr(config.telegram, 'bot_token', '') or
        os.environ.get(getattr(config.notify, 'telegram_bot_token_env', 'TG_TOKEN'), '')
    )
    chat_id = (
        getattr(config.telegram, 'chat_id', '') or
        getattr(config.notify, 'telegram_chat_id', '')
    )
    if not token or not chat_id:
        logger.warning("Telegram credentials missing — skipping send. Message follows:\n" + text)
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'MarkdownV2',
                'disable_web_page_preview': True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Telegram sent.")
        return True
    except Exception as e:
        logger.error(f"Telegram failed: {e}")
        return False


def get_breadth():
    screen_path = 'output/screen_today.csv'
    if not os.path.exists(screen_path):
        return None, None, None
    df = pd.read_csv(screen_path)
    bullish = int((df['bucket'] == 'Bullish').sum())
    bearish = int((df['bucket'] == 'Bearish').sum())
    pd_today = int(df.get('purple_dot', pd.Series([0])).sum()) if 'purple_dot' in df.columns else 0
    return bullish, bearish, pd_today


def get_position_summary():
    try:
        with _db.portfolio_conn() as conn:
            df = pd.read_sql_query("SELECT state, COUNT(*) c FROM positions GROUP BY state", conn)
        return {row['state']: int(row['c']) for _, row in df.iterrows()}
    except Exception:
        return {}


def build_message():
    with open('output/regime_today.json') as f:
        regime_data = json.load(f)
    cands = pd.read_csv('output/candidates.csv') if os.path.exists('output/candidates.csv') else pd.DataFrame()

    regime = regime_data['regime']
    score = regime_data['pillars_passed']
    date = regime_data['date']
    bullish, bearish, pd_today = get_breadth()
    pos = get_position_summary()

    emoji = {'RISK_ON': '🟢', 'CAUTION': '🟡', 'RISK_OFF': '🔴'}.get(regime, '⚪')
    lines = []
    lines.append(f"*SwingEdge Lite* — {md_escape(date)}")
    lines.append(f"{emoji} Regime: *{md_escape(regime)}* \\({score}/4\\)")

    if bullish is not None:
        lines.append(f"Bullish {bullish} / Bearish {bearish}  \\|  Purple Dots: {pd_today}")

    if regime == 'RISK_OFF':
        lines.append("")
        lines.append("_No signals \\(regime \\= RISK\\_OFF\\)_")
    else:
        primaries = cands[cands['tier'] == 'primary'] if not cands.empty else pd.DataFrame()
        secondaries = cands[cands['tier'] == 'secondary'] if not cands.empty else pd.DataFrame()
        lines.append("")
        lines.append(f"*PRIMARY* \\({len(primaries)}\\):")
        if primaries.empty:
            lines.append("_none_")
        else:
            for i, r in enumerate(primaries.itertuples(), 1):
                lines.append(
                    f"{i}\\. *{md_escape(r.symbol)}* close {md_escape(f'{r.close:.2f}')} "
                    f"stop {md_escape(f'{r.suggested_stop:.2f}')} "
                    f"size {r.size_shares}sh grade {md_escape(r.grade)} "
                    f"\\[PD×{r.purple_dot_count_30d}/30d\\]"
                )

        if not secondaries.empty:
            lines.append("")
            syms = ", ".join(md_escape(s) for s in secondaries['symbol'].head(10))
            lines.append(f"_Secondary \\({len(secondaries)}\\):_ {syms}")

    if pos:
        lines.append("")
        parts = [f"{md_escape(k)}\\={v}" for k, v in pos.items()]
        lines.append("Positions: " + " \\| ".join(parts))

    return "\n".join(lines)


def run_notify():
    if not os.path.exists('output/regime_today.json'):
        logger.error("Missing regime_today.json")
        return
    msg = build_message()
    send_telegram(msg)


def main():
    run_notify()


if __name__ == '__main__':
    main()
