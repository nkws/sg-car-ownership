#!/bin/bash
# Launch the Streamlit dashboard from wherever this script lives.
cd "$(dirname "$0")"
python3 -m streamlit run app.py --server.headless true --server.port 8501
