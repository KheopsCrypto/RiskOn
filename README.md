# RiskOn Dashboard

This project provides a simple Flask API (`riskon_api.py`) and a front-end (`index.html`) to display risk-on sentiment scores.

## Requirements

The code was developed for **Python 3.9**. Use a Python 3.9 environment and install the dependencies:

```bash
pip install -r requirements.txt
```

## Running

1. Start the Flask API:
   ```bash
   python3 riskon_api.py
   ```
2. Open `index.html` in a browser. It fetches data from `/api/riskon` on the same host.

## Notes

The API queries external services for market data. If you run this in a restricted network environment, those requests may fail, which will impact the computed scores.
