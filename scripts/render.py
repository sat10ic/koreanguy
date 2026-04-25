import os
import sys
import pandas as pd
import json
import sqlite3
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts import _db, _config, _grade_helper

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('render')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler('logs/render.log')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

logger = setup_logger()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SwingEdge Dashboard - {date}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Outfit:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #05070a;
            --card-bg: rgba(20, 24, 33, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-green: #10b981;
            --accent-cyan: #06b6d4;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --glass-blur: blur(12px);
        }}

        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 40px;
            background-image: radial-gradient(circle at 50% 0%, #1e293b 0%, #05070a 100%);
            min-height: 100vh;
        }}

        h1, h2, h3 {{
            font-family: 'Outfit', sans-serif;
            margin: 0;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
        }}

        .title-group h1 {{
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #f1f5f9 0%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .date-badge {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 8px 16px;
            border-radius: 99px;
            font-size: 14px;
            color: var(--text-secondary);
            backdrop-filter: var(--glass-blur);
        }}

        /* Regime Hero Card */
        .regime-hero {{
            background: linear-gradient(135deg, {regime_color_start} 0%, {regime_color_end} 100%);
            padding: 40px;
            border-radius: 24px;
            text-align: center;
            margin-bottom: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            position: relative;
            overflow: hidden;
        }}

        .regime-hero::after {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url("https://www.transparenttextures.com/patterns/carbon-fibre.png");
            opacity: 0.1;
        }}

        .regime-label {{
            font-size: 16px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            margin-bottom: 12px;
            opacity: 0.8;
        }}

        .regime-state {{
            font-size: 64px;
            font-weight: 900;
            margin-bottom: 24px;
            font-family: 'Outfit', sans-serif;
        }}

        .pillar-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            max-width: 1000px;
            margin: 0 auto;
        }}

        .pillar-card {{
            background: rgba(0,0,0,0.2);
            padding: 16px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }}

        .pillar-name {{
            font-size: 12px;
            text-transform: uppercase;
            color: rgba(255,255,255,0.6);
            margin-bottom: 4px;
        }}

        .pillar-val {{
            font-weight: 700;
            font-size: 14px;
        }}

        /* Section Grids */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 40px;
        }}

        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 24px;
            backdrop-filter: var(--glass-blur);
            margin-bottom: 40px;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}

        .card-header h2 {{
            font-size: 20px;
            font-weight: 700;
        }}

        /* Table Styles */
        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            text-align: left;
            padding: 12px;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 1px solid var(--card-border);
        }}

        td {{
            padding: 16px 12px;
            border-bottom: 1px solid rgba(255,255,255,0.02);
            font-size: 14px;
        }}

        .symbol {{
            font-weight: 700;
            color: var(--text-primary);
        }}

        .grade {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 800;
            font-size: 12px;
        }}

        .grade-a {{ background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .grade-b {{ background: rgba(6, 182, 212, 0.2); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3); }}
        .grade-c {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .grade-f {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }}

        .pnl-pos {{ color: var(--accent-green); font-weight: 600; }}
        .pnl-neg {{ color: var(--accent-red); font-weight: 600; }}

        /* Matrix Grid */
        .matrix-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}

        .matrix-item {{
            background: rgba(255,255,255,0.03);
            padding: 12px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .matrix-sym {{ font-weight: 600; font-size: 13px; }}
        
        .trend-line {{
            display: flex;
            gap: 2px;
        }}

        .trend-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }}

        .dot-green {{ background: var(--accent-green); }}
        .dot-yellow {{ background: var(--accent-amber); }}
        .dot-red {{ background: var(--accent-red); }}
        .dot-gray {{ background: #334155; }}

    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title-group">
                <h1>SwingEdge Lite</h1>
            </div>
            <div class="date-badge">Session: {date}</div>
        </div>

        <div class="regime-hero">
            <div class="regime-label">Current Market State</div>
            <div class="regime-state">{regime_state}</div>
            <div class="pillar-grid">
                <div class="pillar-card">
                    <div class="pillar-name">Trend</div>
                    <div class="pillar-val">{p1_status}</div>
                </div>
                <div class="pillar-card">
                    <div class="pillar-name">Momentum</div>
                    <div class="pillar-val">{p2_status}</div>
                </div>
                <div class="pillar-card">
                    <div class="pillar-name">Breadth</div>
                    <div class="pillar-val">{p3_status}</div>
                </div>
                <div class="pillar-card">
                    <div class="pillar-name">Volatility</div>
                    <div class="pillar-val">{p4_status}</div>
                </div>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="left-col">
                <!-- Primary Candidates -->
                <div class="card">
                    <div class="card-header">
                        <h2>🎯 Verified Candidates (Primary)</h2>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Grade</th>
                                <th>RS Score</th>
                                <th>Suggested Size</th>
                                <th>Stop Loss</th>
                            </tr>
                        </thead>
                        <tbody>
                            {primary_rows}
                        </tbody>
                    </table>
                </div>

                <!-- Secondary Candidates -->
                <div class="card">
                    <div class="card-header">
                        <h2>🔍 Secondary Signals</h2>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Grade</th>
                                <th>RS Score</th>
                                <th>Setup</th>
                            </tr>
                        </thead>
                        <tbody>
                            {secondary_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="right-col">
                <!-- Open Positions -->
                <div class="card">
                    <div class="card-header">
                        <h2>💼 Open Positions</h2>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>P&L</th>
                                <th>Days</th>
                            </tr>
                        </thead>
                        <tbody>
                            {portfolio_rows}
                        </tbody>
                    </table>
                </div>

                <!-- Watchlist Matrix -->
                <div class="card">
                    <div class="card-header">
                        <h2>📈 Watchlist Matrix</h2>
                    </div>
                    <div class="matrix-grid">
                        {matrix_items}
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

def get_grade_class(grade):
    if 'A' in grade: return 'grade-a'
    if 'B' in grade: return 'grade-b'
    if 'C' in grade: return 'grade-c'
    return 'grade-f'

def run_render():
    regime_path = 'output/regime_today.json'
    candidates_path = 'output/candidates.csv'
    screen_path = 'output/screen_today.csv'
    
    if not all(os.path.exists(p) for p in [regime_path, candidates_path, screen_path]):
        logger.error("Missing required data files for rendering.")
        return
        
    with open(regime_path, 'r') as f:
        regime_data = json.load(f)
        
    cand_df = pd.read_csv(candidates_path)
    screen_df = pd.read_csv(screen_path)
    portfolio_conn = _db.portfolio_conn()
    open_pos = pd.read_sql_query("SELECT * FROM portfolio_state WHERE state='OPEN'", portfolio_conn)
    
    # Colors
    regime = regime_data['regime']
    colors = {
        'RISK_ON': ('#064e3b', '#065f46'),
        'CAUTION': ('#92400e', '#78350f'),
        'RISK_OFF': ('#7f1d1d', '#991b1b')
    }
    r_start, r_end = colors.get(regime, ('#1e293b', '#0f172a'))
    
    # Pillar Status
    p1 = "PASS" if regime_data['pillars']['trend']['pass'] else "FAIL"
    p2 = "PASS" if regime_data['pillars']['momentum']['pass'] else "FAIL"
    p3 = "PASS" if regime_data['pillars']['breadth']['pass'] else "FAIL"
    p4 = "PASS" if regime_data['pillars']['volatility']['pass'] else "FAIL"
    
    # Rows
    def format_row(row, is_primary=True):
        grade = row['grade']
        g_class = get_grade_class(grade)
        if is_primary:
            return f"<tr><td><span class='symbol'>{row['symbol']}</span></td><td><span class='grade {g_class}'>{grade}</span></td><td>{row['rs_score']:.2f}</td><td>{row['size_shares']} sh ({row['size_pct']:.1%})</td><td>{row['suggested_stop']:.2f}</td></tr>"
        else:
            return f"<tr><td><span class='symbol'>{row['symbol']}</span></td><td><span class='grade {g_class}'>{grade}</span></td><td>{row['rs_score']:.2f}</td><td>Passed Screen</td></tr>"

    primary_rows = ""
    secondary_rows = ""
    
    if not cand_df.empty:
        primaries = cand_df[cand_df['tier'] == 'Primary']
        secondaries = cand_df[cand_df['tier'] == 'Secondary']
        primary_rows = "".join([format_row(r) for _, r in primaries.iterrows()])
        secondary_rows = "".join([format_row(r, False) for _, r in secondaries.iterrows()])
        
    if not primary_rows: primary_rows = "<tr><td colspan='5' style='text-align:center; color:var(--text-secondary)'>No Primary Candidates Today</td></tr>"
    if not secondary_rows: secondary_rows = "<tr><td colspan='4' style='text-align:center; color:var(--text-secondary)'>No Secondary Signals Today</td></tr>"

    # Portfolio
    port_rows = ""
    for _, pos in open_pos.iterrows():
        # Get current price
        cur_row = screen_df[screen_df['symbol'] == pos['symbol']]
        cur_price = cur_row.iloc[0]['close'] if not cur_row.empty else pos['entry_price']
        pnl = (cur_price - pos['entry_price']) / pos['entry_price']
        pnl_class = 'pnl-pos' if pnl >= 0 else 'pnl-neg'
        port_rows += f"<tr><td><span class='symbol'>{pos['symbol']}</span></td><td><span class='{pnl_class}'>{pnl:.2%}</span></td><td>{pos['days_held']}d</td></tr>"
    if not port_rows: port_rows = "<tr><td colspan='3' style='text-align:center; color:var(--text-secondary)'>No Open Positions</td></tr>"

    # Matrix
    # Get last 5 dates
    feat_conn = _db.features_conn()
    ohlcv_conn = _db.ohlcv_conn()
    cursor = feat_conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM features ORDER BY date DESC LIMIT 5")
    past_dates = [row[0] for row in cursor.fetchall()]
    
    config = _config.load_config()
    watchlist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), getattr(config.universe, 'watchlist_file', 'watchlist.csv'))
    watchlist_df = pd.read_csv(watchlist_path)
    watchlist_symbols = watchlist_df['symbol'].tolist()
    
    matrix_html = ""
    for sym in watchlist_symbols:
        # Get history
        dots = ""
        for d in reversed(past_dates):
            d_grades = _grade_helper.calculate_grades_for_date(feat_conn, ohlcv_conn, d)
            s_row = d_grades[d_grades['symbol'] == sym]
            if s_row.empty:
                dots += "<div class='trend-dot dot-gray'></div>"
            else:
                g = s_row.iloc[0]['grade']
                if 'A' in g: dots += "<div class='trend-dot dot-green'></div>"
                elif 'B' in g: dots += "<div class='trend-dot dot-yellow'></div>"
                else: dots += "<div class='trend-dot dot-red'></div>"
        
        cur_grade = "N/A"
        cur_row = screen_df[screen_df['symbol'] == sym]
        if not cur_row.empty: cur_grade = cur_row.iloc[0]['grade']
        
        matrix_html += f"""
        <div class='matrix-item'>
            <span class='matrix-sym'>{sym}</span>
            <div class='trend-line'>{dots}</div>
            <span class='grade {get_grade_class(cur_grade)}'>{cur_grade}</span>
        </div>
        """

    # Final Render
    final_html = HTML_TEMPLATE.format(
        date=regime_data['date'],
        regime_state=regime,
        regime_color_start=r_start,
        regime_color_end=r_end,
        p1_status=p1, p2_status=p2, p3_status=p3, p4_status=p4,
        primary_rows=primary_rows,
        secondary_rows=secondary_rows,
        portfolio_rows=port_rows,
        matrix_items=matrix_html
    )
    
    out_path = 'output/dashboard.html'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    logger.info(f"Dashboard rendered successfully to {out_path}.")

def main():
    run_render()

if __name__ == '__main__':
    main()
