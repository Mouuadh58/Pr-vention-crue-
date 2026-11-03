#!/usr/bin/env sh
# Lance BatCrue sous Linux ou macOS (Python 3.10 ou plus).
cd "$(dirname "$0")" || exit 1
python3 -m pip install --quiet -r requirements.txt
python3 -m streamlit run app.py
