@echo off
REM Lance BatCrue sous Windows (Python 3.10 ou plus doit être installé).
cd /d "%~dp0"
python -m pip install --quiet -r requirements.txt
python -m streamlit run app.py
pause
