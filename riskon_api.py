from flask import Flask, jsonify
import numpy as np
import yfinance as yf
import warnings
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Masquer les warnings YFinance/Deprecation
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

app = Flask(__name__)

def scale(val, minv, maxv, reverse=False):
    if val is None:
        return 0
    if reverse:
        return max(0, min(1, 1 - (val - minv)/(maxv - minv)))
    else:
        return max(0, min(1, (val - minv)/(maxv - minv)))

def get_price(ticker, period="1mo"):
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        arr = df['Close'].values
        return arr.astype(float) if arr is not None and len(arr) > 0 else None
    except Exception as e:
        return None

def safe_last(arr):
    try:
        if arr is not None and hasattr(arr, '__len__') and len(arr) > 0:
            return float(arr[-1])
    except Exception:
        pass
    return None

def to_scalar(val):
    import numpy as np
    if val is None:
        return None
    if isinstance(val, (np.ndarray, list)):
        return float(np.array(val).item()) if np.array(val).size == 1 else float(np.array(val)[-1])
    try:
        return float(val)
    except Exception:
        return None

def get_put_call_ratio_alphaquery():
    url = 'https://www.alphaquery.com/stock/spy/put-call-ratio'
    try:
        import requests
        import pandas as pd
        r = requests.get(url, timeout=8, headers={'User-Agent':'Mozilla/5.0'})
        # Cherche le tableau avec pandas
        tables = pd.read_html(r.text)
        if not tables or len(tables) < 1:
            return None
        # Le premier tableau a la série chronologique, la première ligne est la dernière valeur
        df = tables[0]
        # On prend la colonne "Put/Call Ratio" de la première ligne
        if 'Put/Call Ratio' in df.columns:
            ratio = df.iloc[0]['Put/Call Ratio']
            return float(ratio)
        # Fallback si nom différent
        for col in df.columns:
            if 'put' in col.lower() and 'call' in col.lower():
                ratio = df.iloc[0][col]
                return float(ratio)
        return None
    except Exception as e:
        print('AlphaQuery Put/Call fetch failed:', e)
        return None

def get_crypto_fear_greed():
    try:
        url = 'https://api.alternative.me/fng/?limit=1'
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            data = r.json()
            return float(data['data'][0]['value'])
    except Exception as e:
        print("FG fetch failed:", e)
    return None
    
@app.route('/api/riskon')
def riskon():
    try:
        btc = get_price("BTC-USD")
        eth = get_price("ETH-USD")
        spx = get_price("^GSPC")
        tlt = get_price("TLT")
        dxy = get_price("DX-Y.NYB")
        xau = get_price("GC=F")
        vix_arr = get_price("^VIX")
        
        #vix = float(np.random.uniform(12, 25, 1)[0])
        putcall = get_put_call_ratio_alphaquery()
        if putcall is None:
            putcall = float(np.random.uniform(0.7, 1.4, 1)[0])  # fallback random si échec


        funding = float(np.random.uniform(-0.005, 0.01, 1)[0])
        #fear_greed = float(np.random.uniform(20, 80, 1)[0])
        fear_greed = get_crypto_fear_greed()
        if fear_greed is None:
            fear_greed = float(np.random.uniform(20, 80, 1)[0])

        etf_flows = float(np.random.uniform(-500, 1200, 1)[0])

        i = -1

        btc_val = safe_last(btc)
        eth_val = safe_last(eth)
        spx_val = safe_last(spx)
        tlt_val = safe_last(tlt)
        dxy_val = safe_last(dxy)
        xau_val = safe_last(xau)
        vix = safe_last(vix_arr)

        # Sous-scores (en float natif !)
        ratio = spx_val / tlt_val if tlt_val else None
        score_spx = scale(ratio, 0.9, 1.4) if ratio else None
        score_vix = scale(vix, 12, 22, reverse=True)
        btc_7d = None
        if btc_val is not None and btc is not None and len(btc) > 7 and btc[max(0,i-7)] > 0:
            btc_7d = (btc_val - float(btc[max(0,i-7)])) / float(btc[max(0,i-7)])
        score_btc = scale(btc_7d, -0.1, 0.12) if btc_7d is not None else None
        eth_btc = eth_val / btc_val if btc_val else None
        score_ethbtc = scale(eth_btc, 0.045, 0.07) if eth_btc else None
        score_dxy = scale(dxy_val, 100, 110, reverse=True)
        score_gold = scale(xau_val, 1850, 2450, reverse=True)
        score_pc = scale(putcall, 0.7, 1.1, reverse=True)
        score_funding = scale(funding, -0.005, 0.009)
        score_fg = scale(fear_greed, 20, 80)
        score_etf = scale(etf_flows, -400, 1000)

        # Forçage strict des types AVANT calcul pondéré
        score_spx     = to_scalar(score_spx)
        score_vix     = to_scalar(score_vix)
        score_btc     = to_scalar(score_btc)
        score_ethbtc  = to_scalar(score_ethbtc)
        score_dxy     = to_scalar(score_dxy)
        score_gold    = to_scalar(score_gold)
        score_pc      = to_scalar(score_pc)
        score_funding = to_scalar(score_funding)
        score_fg      = to_scalar(score_fg)
        score_etf     = to_scalar(score_etf)

        # Calcul pondéré ULTRA SAFE
        final_score = 0
        for val, weight in [
            (score_spx,     0.15),
            (score_vix,     0.13),
            (score_btc,     0.12),
            (score_ethbtc,  0.10),
            (score_dxy,     0.10),
            (score_gold,    0.08),
            (score_pc,      0.08),
            (score_funding, 0.08),
            (score_fg,      0.08),
            (score_etf,     0.08),
        ]:
            final_score += float(val) * weight if val is not None else 0

        score_now = int(float(final_score) * 100)

        # On vérifie la validité des sous-scores pour status
        sub_scores = {
            'stocks_bonds': score_spx,
            'vix': score_vix,
            'crypto': (score_btc, score_ethbtc),
            'flows': (score_etf, score_funding),
            'sentiment': (score_fg, score_pc, score_vix),
        }
        all_scores = [v for k in sub_scores for v in (sub_scores[k] if isinstance(sub_scores[k], tuple) else (sub_scores[k],))]
        status = "OK" if all(x is not None and not (isinstance(x, float) and np.isnan(x)) for x in all_scores) else "ERROR - Missing or invalid value(s)"

        response = {
            'status': status,
            'raw': {
                'btc': to_scalar(btc_val),
                'eth': to_scalar(eth_val),
                'spx': to_scalar(spx_val),
                'tlt': to_scalar(tlt_val),
                'dxy': to_scalar(dxy_val),
                'xau': to_scalar(xau_val),
                'vix': to_scalar(vix),
                'putcall': to_scalar(putcall),
                'funding': to_scalar(funding),
                'fear_greed': to_scalar(fear_greed),
                'etf_flows': to_scalar(etf_flows)
            },
            'scores': {
                'stocks_bonds': None if score_spx is None else int(score_spx * 100),
                'vix': int(score_vix * 100),
                'crypto': None if score_btc is None or score_ethbtc is None else int((score_btc*50 + score_ethbtc*50)),
                'flows': int((score_etf*50 + score_funding*50)),
                'sentiment': int((score_fg*50 + score_pc*25 + score_vix*25)),
            },
            'details': {
                'score_spx': score_spx,
                'score_vix': score_vix,
                'score_btc': score_btc,
                'score_ethbtc': score_ethbtc,
                'score_dxy': score_dxy,
                'score_gold': score_gold,
                'score_pc': score_pc,
                'score_funding': score_funding,
                'score_fg': score_fg,
                'score_etf': score_etf,
            },
            'riskon_score': score_now
        }
        return jsonify(response)
    except Exception as e:
        import traceback
        print("EXCEPTION IN /api/riskon:", e)
        traceback.print_exc()
        return jsonify({'status': f'EXCEPTION: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
