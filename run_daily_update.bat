@echo off
cd /d "c:\Users\satta\Downloads\koreanguy"
echo === Downloading latest NSE Bhavcopy ===
python bhavcopy_extractor/download_bhavcopy.py --source both --days 5
echo === ChartsMaze scrape ===
cd chartsmaze_extractor
python extractor.py --headless
cd ..
echo === Running 15-stage EOD Pipeline (incl. agent debate/coach/lessons/run_card) ===
python run_manas_cli.py run-eod
echo === Done ===
