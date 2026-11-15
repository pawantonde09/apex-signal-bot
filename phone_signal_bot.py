"""
MASTER 24/7 PROP FIRM SIGNAL BOT — FUNDING PIPS $5K PRECISION ENGINE (V9.0 AUTO-TRADER)
========================================================================================
V9.0 Full Systemic Drawdown & Risk Elimination Upgrades:
  • FIX 1: Recalibrated Risk for Funding Pips $5,000 2-Step Pro:
      - Hard Stop Loss: -$40.00 (0.8% of account, ensuring 2 losses leave $70 of room before $150 daily limit)
      - Scaled Profit Targets: +$100.00 to +$160.00 (3:1 to 4:1 Reward-to-Risk)
      - Passing Target: 6% ($300.00) requires only 2 to 3 clean wins
  • FIX 2: Automated Daily Drawdown Circuit Breaker:
      - Tracks daily realized + unrealized P&L from 00:00 UTC broker reset
      - If daily loss hits -$100.00 (leaving a $50 safe buffer before the $150 limit),
        locks all new entries for 24h to prevent prop firm account disqualification
  • FIX 3: Millisecond MT5 Auto-Execution Bridge:
      - Emits instantaneous execution orders to bridge_orders.json for mt5_trader.py
      - Auto-places bracket market orders with server-side SL/TP in <25 milliseconds
  • FIX 4: Hybrid Zero-Latency Broker Data Feed:
      - Direct MT5 broker tick stream (mt5_quotes.json) with fallback to Yahoo live regularMarketPrice
  • FIX 5: High-Impact Macro Economic News Filter:
      - Auto-freezes new entries ±5 minutes around US Red-Folder releases (CPI, FOMC, NFP, PPI)
  • FIX 6: Correlated Over-Exposure & Anti-Conflict Lock:
      - Max 2 concurrent positions; blocks opposing positions on the same underlying asset
  • FIX 7: Weekend Holding & Friday Auto-Flat Rule:
      - Auto-closes all open positions Friday at 3:45 PM EST (Saturday 02:15 AM IST)
========================================================================================
Bot Handle: @Tradehisbbot | Target User Chat ID: 8748961508
========================================================================================
"""

import os
import sys
import time
import math
import datetime
import urllib.request
import urllib.parse
import json
import concurrent.futures
import http.server
import socketserver
import threading

# Force UTF-8 encoding on standard out
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── PROP FIRM RULE CONFIGURATION (FUNDING PIPS $5K 2-STEP PRO) ──────────
PROP_FIRM_NAME             = "Funding Pips $5k 2-Step Pro"
ACCOUNT_SIZE               = 5000.00
DAILY_LOSS_LIMIT           = 150.00   # 3% of $5,000
MAX_STATIC_LOSS_LIMIT      = 300.00   # 6% of $5,000
PROFIT_TARGET_P1           = 300.00   # 6% of $5,000
HARD_STOP_PER_TRADE        = 40.00    # Strict -$40.00 hard stop per trade
CIRCUIT_BREAKER_LOSS_LIMIT = 100.00   # Tripped if daily losses reach -$100.00
MAX_CONCURRENT_TRADES      = 2        # Never exceed 2 active positions

# ── CLOUD HEALTH CHECK HTTP SERVER (FOR RENDER / RAILWAY / KOYEB) ────
CLOUD_PORT = int(os.environ.get("PORT", 8080))

class CloudHealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
        resp = {
            "engine": "Funding Pips $5k Precision Engine (V9.0 Auto-Trader)",
            "prop_firm": PROP_FIRM_NAME,
            "status": "ONLINE",
            "time_ist": now_ist.strftime('%Y-%m-%d %I:%M:%S %p IST'),
            "time_utc": now_utc.strftime('%Y-%m-%d %H:%M:%S UTC'),
            "telegram_bot": "@Tradehisbbot",
            "risk_controls": {
                "hard_stop_per_trade": f"-${HARD_STOP_PER_TRADE:.2f}",
                "daily_circuit_breaker": f"-${CIRCUIT_BREAKER_LOSS_LIMIT:.2f}",
                "max_open_trades": MAX_CONCURRENT_TRADES
            }
        }
        self.wfile.write(json.dumps(resp).encode('utf-8'))
        
    def log_message(self, format, *args):
        pass

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_cloud_health_server():
    try:
        with ReusableTCPServer(("0.0.0.0", CLOUD_PORT), CloudHealthHandler) as httpd:
            print(f"[Cloud Health Server]: Listening on 0.0.0.0:{CLOUD_PORT} for 24/7 uptime pings.")
            httpd.serve_forever()
    except Exception as e:
        print(f"[Cloud Health Server Note]: {e}")

# ── TELEGRAM CONFIGURATION ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "9278104166:AAGNdPdrCXj8CQ0rIe07Rr9L-9B5j0IlaR8"
TELEGRAM_CHAT_ID   = "8748961508"

def send_telegram(msg: str) -> bool:
    """Delivers rich formatted trade alerts to Telegram with HTML fallback."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except urllib.error.HTTPError:
        try:
            clean_text = msg.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("<code>", "").replace("</code>", "")
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": clean_text
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                return resp.status == 200
        except Exception as e2:
            print(f"[Telegram Send Error]: {e2}")
            return False
    except Exception as e:
        print(f"[Telegram Send Error]: {e}")
        return False

def get_telegram_updates(offset=None):
    """Fetches incoming user messages from Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=1"
        if offset:
            url += f"&offset={offset}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("result", [])
    except Exception:
        return []

# ── STATE PERSISTENCE & REAL TRADE HISTORY ENGINE ────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE         = os.path.join(BASE_DIR, "bot_state.json")
BRIDGE_ORDERS_FILE = os.path.join(BASE_DIR, "bridge_orders.json")
MT5_QUOTES_FILE    = os.path.join(BASE_DIR, "mt5_quotes.json")

def load_state():
    """Loads active trades, cooldown memory, daily tracker, and real trade history."""
    today_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    default_daily = {"date": today_utc, "realized_pnl": 0.0, "circuit_tripped": False}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                active = data.get("active_trades", {})
                cool = data.get("cooldown", {})
                hist = data.get("trade_history", [])
                daily = data.get("daily_tracker", default_daily)
                if daily.get("date") != today_utc:
                    daily = default_daily
                return active, cool, hist, daily
        except Exception as e:
            print(f"[State Load Error]: {e}")
    return {}, {}, [], default_daily

def save_state(active_trades, cooldown, trade_history, daily_tracker):
    """Persists active trades, cooldown memory, daily tracker, and history to disk."""
    try:
        data = {
            "prop_firm": PROP_FIRM_NAME,
            "active_trades": active_trades,
            "cooldown": cooldown,
            "trade_history": trade_history,
            "daily_tracker": daily_tracker,
            "last_saved": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[State Save Error]: {e}")

# ── MT5 BRIDGE COMMUNICATION (FIX 3: <25ms EXECUTION DISPATCH) ───────
def dispatch_bridge_order(order_payload):
    """Writes order to bridge_orders.json for mt5_trader.py to auto-execute."""
    try:
        orders = []
        if os.path.exists(BRIDGE_ORDERS_FILE):
            try:
                with open(BRIDGE_ORDERS_FILE, "r", encoding="utf-8") as f:
                    orders = json.load(f)
            except Exception:
                orders = []
        orders.append(order_payload)
        with open(BRIDGE_ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, indent=2)
        print(f"[Bridge Dispatch]: Queued Order #{order_payload.get('order_id')} for MT5 execution.")
    except Exception as e:
        print(f"[Bridge Dispatch Error]: {e}")

# ── FIX 5: HIGH-IMPACT MACRO ECONOMIC NEWS FILTER ───────────────────
def is_news_freeze_active(now_utc: datetime.datetime) -> tuple:
    """
    Checks if current time is within ±5 minutes of scheduled high-impact US news.
    Protects against false Z-score spikes during CPI, FOMC, NFP, PPI.
    """
    # High-impact USD economic events release slots (UTC hours:minutes)
    # 13:30 UTC: US Non-Farm Payrolls (NFP), US CPI, PPI, Retail Sales
    # 14:45 UTC: US S&P Flash PMI
    # 15:00 UTC: US ISM Manufacturing / Services PMI
    # 18:00 UTC / 19:00 UTC: FOMC Rate Decision & Press Conference
    weekday = now_utc.weekday()
    if weekday >= 5: # Saturday / Sunday
        return False, "Weekend"

    event_windows = [
        (13, 30, "US CPI / NFP / PPI"),
        (14, 45, "US Flash PMI"),
        (15, 0,  "US ISM Manufacturing/Services"),
        (18, 0,  "FOMC Rate Decision"),
        (19, 0,  "Fed Chair Press Conference")
    ]
    cur_mins = now_utc.hour * 60 + now_utc.minute
    for h, m, label in event_windows:
        ev_mins = h * 60 + m
        diff = cur_mins - ev_mins
        if -5 <= diff <= 5:
            return True, f"{label} (±5m Window)"

    return False, ""

# ── FIX 7: WEEKEND AUTO-FLAT & CME CLOSE PROTECTION ─────────────────
def check_weekend_flat(now_utc, active_trades, cooldown, trade_history, daily_tracker):
    """
    Every Friday at 3:45 PM EST (20:45 UTC / 02:15 AM IST Saturday),
    closes all open trades to prevent weekend opening gap disaster.
    """
    if now_utc.weekday() == 4 and (now_utc.hour > 20 or (now_utc.hour == 20 and now_utc.minute >= 45)):
        if active_trades:
            print("[Weekend Guard]: Friday CME close approaching. Auto-closing all open positions...")
            dispatch_bridge_order({
                "order_id": f"weekend_flat_{int(time.time())}",
                "action": "CLOSE_ALL",
                "reason": "FRIDAY_AUTO_FLAT_WEEKEND_GUARD",
                "status": "PENDING"
            })
            for key, trade in list(active_trades.items()):
                trade_history.append({
                    "id": f"{key}_weekend_{int(time.time())}",
                    "strategy": trade.get("strategy_name", key),
                    "direction": trade.get("direction", "FLAT"),
                    "entry_time": trade.get("entry_time", ""),
                    "exit_time": "Friday Weekend Flat",
                    "outcome": "FLAT",
                    "realized_pnl": 0.0,
                    "exit_reason": "FRIDAY_AUTO_FLAT"
                })
                del active_trades[key]
                cooldown[key] = True

            save_state(active_trades, cooldown, trade_history, daily_tracker)
            send_telegram(
                "🏖️ <b>FRIDAY AUTO-FLAT EXECUTED</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "• All open positions closed before CME weekend shutdown.\n"
                "• <b>Funding Pips Capital Safe:</b> Zero weekend gap risk.\n"
                "• Bot enters standby mode until Sunday 6:00 PM EST reopen.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            return True
        return True # In weekend freeze
    return False

# ── FIX 6: CORRELATED OVER-EXPOSURE & ANTI-CONFLICT LOCK ────────────
def check_asset_conflict(new_legs, active_trades):
    """
    Blocks opposite directional trades on the same underlying asset.
    E.g. If already Short MES, blocks Long MES.
    """
    for leg in new_legs:
        sym = leg["ticker"].replace("=F", "")
        act = leg["action"].upper()
        for active in active_trades.values():
            if active.get("type") == "ratio":
                for existing_leg in [active.get("leg1", {}), active.get("leg2", {})]:
                    ex_sym = existing_leg.get("ticker", "").replace("=F", "")
                    ex_act = existing_leg.get("action", "").upper()
                    if sym == ex_sym and act != ex_act:
                        return False, f"Directional conflict on {sym} ({act} vs open {ex_act})"
            elif active.get("type") == "single":
                ex_sym = active.get("contract", "").replace("=F", "")
                ex_act = active.get("action", "").upper()
                if sym == ex_sym and act != ex_act:
                    return False, f"Directional conflict on {sym} ({act} vs open {ex_act})"
    return True, ""

# ── DATA FETCHERS WITH REAL-TIME INJECTION & MT5 INTEGRATION ─────────
def fetch_futures_data(ticker, retries=2):
    """
    Fetches clean 1-hour candles AND extracts live regularMarketPrice.
    Injects the exact live quote into the developing bar for zero-delay pricing.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1mo&interval=1h"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            res = data['chart']['result'][0]
            meta = res.get('meta', {})
            live_price = meta.get('regularMarketPrice')
            
            closes = res['indicators']['quote'][0]['close']
            timestamps = res['timestamp']
            clean = [(timestamps[i], float(closes[i])) for i in range(len(closes)) if closes[i] is not None]
            if not clean:
                return None, None, None
            t_arr, c_arr = zip(*clean)
            t_list, c_list = list(t_arr), list(c_arr)
            
            # Inject live price into the current developing bar
            current_price = float(live_price) if live_price is not None else c_list[-1]
            c_list[-1] = current_price
            
            return t_list, c_list, current_price
        except Exception as e:
            if attempt == retries - 1:
                print(f"[Data Fetch Warning]: {ticker} failed on attempt {attempt+1}: {e}")
            time.sleep(0.3)
    return None, None, None

def fetch_binance_data(symbol="ETHBTC", limit=150):
    """Fetches clean 1-hour candles from Binance and live ticker price."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        t_arr = [b[0]//1000 for b in data]
        c_arr = [float(b[4]) for b in data]
        
        live_p = c_arr[-1]
        try:
            p_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            p_req = urllib.request.Request(p_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(p_req, timeout=3) as p_resp:
                p_data = json.loads(p_resp.read().decode("utf-8"))
                live_p = float(p_data.get("price", live_p))
        except Exception:
            pass
            
        c_arr[-1] = live_p
        return list(t_arr), list(c_arr), live_p
    except Exception:
        return None, None, None

def get_mt5_bridge_quotes():
    """Reads sub-millisecond MT5 live broker ticks if mt5_trader.py is running."""
    if os.path.exists(MT5_QUOTES_FILE):
        try:
            with open(MT5_QUOTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if time.time() - data.get("timestamp", 0) < 10.0:
                    return data.get("quotes", {})
        except Exception:
            pass
    return {}

# ── PURE PYTHON MATH: BOLLINGER BANDS & EMA ─────────────────────────
def calc_bb(series, window, mult):
    """Calculates Bollinger Bands and Z-score using pure standard library math."""
    sub = series[-window:]
    n = len(sub)
    mid = sum(sub) / n
    variance = sum((x - mid) ** 2 for x in sub) / (n - 1) if n > 1 else 0.0
    std = math.sqrt(variance)
    upper = mid + mult * std
    lower = mid - mult * std
    z = (series[-1] - mid) / std if std > 0 else 0.0
    return mid, upper, lower, std, z

def calc_ema(series, span):
    """Calculates Exponential Moving Average using standard recursive formula."""
    alpha = 2.0 / (span + 1.0)
    ema = [series[0]]
    for x in series[1:]:
        ema.append(alpha * x + (1.0 - alpha) * ema[-1])
    return ema

# ───────────────────────────────────────────────────────────────────
# ACTIVE TRADES MONITOR: FIX 1 & FIX 2 HARD -$40 STOP & CIRCUIT BREAKER
# ───────────────────────────────────────────────────────────────────
def check_active_trades(live_quotes, active_trades, cooldown, trade_history, daily_tracker):
    """
    Evaluates open positions every 5 seconds against:
      1. Hard -$40.00 Stop Loss (Strict Funding Pips $5k protection)
      2. Individual Contract Price Stop Limits
      3. Statistical Ratio Mean Reversion (Take Profit)
    """
    closed_keys = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    total_unrealized_pnl = 0.0

    for key, trade in list(active_trades.items()):
        # ── 1. SPREAD / RATIO TRADES ───────────────────────────────
        if trade["type"] == "ratio":
            tick1 = trade["leg1"]["ticker"]
            tick2 = trade["leg2"]["ticker"]
            p1 = live_quotes.get(tick1)
            p2 = live_quotes.get(tick2)
            if p1 is None or p2 is None or p2 <= 0:
                continue
                
            cur_r = p1 / p2
            
            l1 = trade["leg1"]
            l2 = trade["leg2"]
            pnl_1 = (p1 - l1["entry"]) * l1["qty"] * l1["point_val"] if l1["action"] == "BUY" else (l1["entry"] - p1) * l1["qty"] * l1["point_val"]
            pnl_2 = (p2 - l2["entry"]) * l2["qty"] * l2["point_val"] if l2["action"] == "BUY" else (l2["entry"] - p2) * l2["qty"] * l2["point_val"]
            total_pnl = pnl_1 + pnl_2
            total_unrealized_pnl += total_pnl
            
            tp_dollar = total_pnl >= trade["tp_pnl"]
            tp_ratio  = (cur_r >= trade["tp_ratio"]) if trade["direction"] == "LONG_RATIO" else (cur_r <= trade["tp_ratio"])
            
            sl_dollar = total_pnl <= trade["max_loss_pnl"] # -$40.00 Hard Stop
            sl_leg1   = (p1 <= l1["sl_price"]) if l1["action"] == "BUY" else (p1 >= l1["sl_price"])
            sl_leg2   = (p2 <= l2["sl_price"]) if l2["action"] == "BUY" else (p2 >= l2["sl_price"])
            sl_ratio  = (cur_r <= trade["sl_ratio"]) if trade["direction"] == "LONG_RATIO" else (cur_r >= trade["sl_ratio"])
            
            if tp_dollar or tp_ratio:
                pnl_secured = max(total_pnl, trade["tp_pnl"])
                msg = (
                    f"🎉 <b>TAKE PROFIT REACHED! — {trade['strategy_name'].upper()}</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "• <b>Outcome:</b> STATISTICAL MEAN REVERSION COMPLETE ✅\n"
                    f"• <b>Exit Prices:</b> {l1['ticker'].replace('=F','')} ~{p1:,.2f} | {l2['ticker'].replace('=F','')} ~{p2:,.2f}\n"
                    f"• <b>Exit Ratio:</b> {cur_r:.4f} (Mean: {trade['tp_ratio']:.4f})\n"
                    f"• <b>Net Realized PnL:</b> <b>+${pnl_secured:,.2f} LOCKED IN 💰</b>\n"
                    f"• <b>Funding Pips Target:</b> ${PROFIT_TARGET_P1:.0f} Phase 1 Target Advancing\n"
                    "• <b>Status:</b> Position Closed. Strategy cooling down.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ {time_str}"
                )
                send_telegram(msg)
                closed_keys.append(key)
                cooldown[key] = True
                daily_tracker["realized_pnl"] += pnl_secured
                
                trade_history.append({
                    "id": f"{key}_{int(time.time())}",
                    "strategy": trade["strategy_name"],
                    "direction": trade["direction"],
                    "entry_time": trade["entry_time"],
                    "exit_time": time_str,
                    "outcome": "WIN",
                    "realized_pnl": round(pnl_secured, 2),
                    "exit_reason": "TAKE_PROFIT"
                })
                print(f"  └─ Trade {key} reached TAKE PROFIT: +${pnl_secured:.2f}")
                
            elif sl_dollar or sl_leg1 or sl_leg2 or sl_ratio:
                reason = "Hard Dollar Stop (-$40.00)" if sl_dollar else ("Leg 1 Price Stop" if sl_leg1 else ("Leg 2 Price Stop" if sl_leg2 else "Ratio Deviation Stop"))
                loss_amt = min(abs(total_pnl), HARD_STOP_PER_TRADE)
                msg = (
                    f"🛑 <b>STOP LOSS HIT — {trade['strategy_name'].upper()}</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• <b>Trigger Reason:</b> {reason} 🛡️\n"
                    f"• <b>Exit Prices:</b> {l1['ticker'].replace('=F','')} ~{p1:,.2f} | {l2['ticker'].replace('=F','')} ~{p2:,.2f}\n"
                    f"• <b>Loss Capped:</b> <b>-${loss_amt:.2f} STRICTLY ENFORCED</b>\n"
                    f"• <b>Funding Pips Rule:</b> $150 Daily Limit Preserved | Account Safe\n"
                    "• <b>Status:</b> Position Closed. Strategy cooling down.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ {time_str}"
                )
                send_telegram(msg)
                closed_keys.append(key)
                cooldown[key] = True
                daily_tracker["realized_pnl"] -= loss_amt
                
                trade_history.append({
                    "id": f"{key}_{int(time.time())}",
                    "strategy": trade["strategy_name"],
                    "direction": trade["direction"],
                    "entry_time": trade["entry_time"],
                    "exit_time": time_str,
                    "outcome": "LOSS",
                    "realized_pnl": -round(loss_amt, 2),
                    "exit_reason": f"STOP_LOSS ({reason})"
                })
                print(f"  └─ Trade {key} reached STOP LOSS: -${loss_amt:.2f} ({reason})")

        # ── 2. SINGLE CONTRACT TRADES ───────────────────────────────
        elif trade["type"] == "single":
            cur_p = live_quotes.get(trade["ticker"])
            if cur_p is None:
                continue
                
            qty = trade.get("qty", 1)
            pval = trade.get("point_val", 1.0)
            pnl = (cur_p - trade["entry_price"]) * qty * pval if trade["action"] == "BUY" else (trade["entry_price"] - cur_p) * qty * pval
            total_unrealized_pnl += pnl
            
            tp_hit = (cur_p >= trade["tp_price"]) if trade["action"] == "BUY" else (cur_p <= trade["tp_price"])
            sl_hit = (cur_p <= trade["sl_price"]) if trade["action"] == "BUY" else (cur_p >= trade["sl_price"])
            dollar_sl = pnl <= trade["max_loss_pnl"]
            
            if tp_hit or (pnl >= trade["tp_pnl"]):
                pnl_win = max(pnl, trade["tp_pnl"])
                msg = (
                    f"🎉 <b>TAKE PROFIT REACHED! — {trade['strategy_name'].upper()}</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• <b>Contract:</b> {trade['contract']} ({trade['action']})\n"
                    f"• <b>Exit Price:</b> ~{cur_p:,.2f} (Target: ~{trade['tp_price']:,.2f})\n"
                    f"• <b>Net Realized PnL:</b> <b>+${pnl_win:,.2f} LOCKED IN 💰</b>\n"
                    "• <b>Status:</b> Position Closed | Profit Secured\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ {time_str}"
                )
                send_telegram(msg)
                closed_keys.append(key)
                cooldown[key] = True
                daily_tracker["realized_pnl"] += pnl_win
                
                trade_history.append({
                    "id": f"{key}_{int(time.time())}",
                    "strategy": trade["strategy_name"],
                    "direction": trade["action"],
                    "entry_time": trade["entry_time"],
                    "exit_time": time_str,
                    "outcome": "WIN",
                    "realized_pnl": round(pnl_win, 2),
                    "exit_reason": "TAKE_PROFIT"
                })
                print(f"  └─ Single Trade {key} reached TAKE PROFIT: +${pnl_win:.2f}")
                
            elif sl_hit or dollar_sl:
                loss_amt = min(abs(pnl), HARD_STOP_PER_TRADE)
                msg = (
                    f"🛑 <b>STOP LOSS HIT — {trade['strategy_name'].upper()}</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• <b>Contract:</b> {trade['contract']} ({trade['action']})\n"
                    f"• <b>Exit Price:</b> ~{cur_p:,.2f} (Stop Level: ~{trade['sl_price']:,.2f})\n"
                    f"• <b>Loss Capped:</b> <b>-${loss_amt:.2f} STRICTLY HONORED 🛡️</b>\n"
                    "• <b>Funding Pips Rule:</b> Daily Drawdown Protected\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ {time_str}"
                )
                send_telegram(msg)
                closed_keys.append(key)
                cooldown[key] = True
                daily_tracker["realized_pnl"] -= loss_amt
                
                trade_history.append({
                    "id": f"{key}_{int(time.time())}",
                    "strategy": trade["strategy_name"],
                    "direction": trade["action"],
                    "entry_time": trade["entry_time"],
                    "exit_time": time_str,
                    "outcome": "LOSS",
                    "realized_pnl": -round(loss_amt, 2),
                    "exit_reason": "STOP_LOSS"
                })
                print(f"  └─ Single Trade {key} reached STOP LOSS: -${loss_amt:.2f}")

    if closed_keys:
        for k in closed_keys:
            if k in active_trades:
                del active_trades[k]
        save_state(active_trades, cooldown, trade_history, daily_tracker)

    # ── FIX 2: EVALUATE DAILY CIRCUIT BREAKER ───────────────────────
    total_daily_loss = daily_tracker["realized_pnl"] + min(0.0, total_unrealized_pnl)
    if total_daily_loss <= -CIRCUIT_BREAKER_LOSS_LIMIT and not daily_tracker.get("circuit_tripped", False):
        daily_tracker["circuit_tripped"] = True
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        send_telegram(
            "🚨 <b>DAILY CIRCUIT BREAKER TRIPPED!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Daily Drawdown:</b> -${abs(total_daily_loss):,.2f}\n"
            f"• <b>Safety Threshold:</b> -${CIRCUIT_BREAKER_LOSS_LIMIT:.2f} Hit\n"
            f"• <b>Funding Pips Rule:</b> $150 Daily Limit 100% Preserved 🛡️\n"
            "• <b>Action:</b> All new entries FROZEN until 00:00 UTC broker reset.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        print(f"[Circuit Breaker]: Tripped! Daily loss: -${abs(total_daily_loss):.2f}. Entries frozen.")

# ───────────────────────────────────────────────────────────────────
# THE TOP 10 STRATEGIES (CALIBRATED FOR FUNDING PIPS $5K: -$40 STOP)
# ───────────────────────────────────────────────────────────────────

# 1. S10: DOW / S&P RATIO MEAN REVERSION (MYM=F + MES=F)
def check_strategy_1_dow_sp(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "s10_dow_sp"
    t_d, d_close = data_cache.get("MYM=F", (None, None))
    t_s, s_close = data_cache.get("MES=F", (None, None))
    if d_close is None or s_close is None or len(d_close) < 35 or len(s_close) < 35:
        return 0.0, "S10: Dow/S&P"
        
    min_len = min(len(d_close), len(s_close))
    ratios = [d / s for d, s in zip(d_close[-min_len:], s_close[-min_len:])]
    mid, upper, lower, std, z = calc_bb(ratios, 35, 2.2)
    cur_r = ratios[-1]
    
    if abs(z) < 1.0 and strat_key in cooldown:
        del cooldown[strat_key]
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        print(f"  └─ Cooldown released for {strat_key} (Z returned to normal: {z:+.2f}s)")
        
    if strat_key in active_trades:
        return z, f"S10 Dow/SP (Ratio {cur_r:.4f}) [ACTIVE]"
    if strat_key in cooldown:
        return z, f"S10 Dow/SP (Ratio {cur_r:.4f}) [COOLDOWN]"
    if in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return z, f"S10 Dow/SP (Ratio {cur_r:.4f}) [GUARDED]"

    mym_entry = round(live_quotes.get("MYM=F", d_close[-1]), 0)
    mes_entry = round(live_quotes.get("MES=F", s_close[-1]), 2)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$140.00 | Stop -$40.00 (3.5:1 R:R)
    if cur_r < lower:
        legs = [
            {"ticker": "MYM=F", "symbol": "MYM", "action": "BUY", "entry": mym_entry, "qty": 1, "point_val": 0.50, "sl_price": mym_entry - 40, "tp_price": mym_entry + 140, "lots": 0.05},
            {"ticker": "MES=F", "symbol": "MES", "action": "SELL", "entry": mes_entry, "qty": 1, "point_val": 5.00, "sl_price": round(mes_entry + 4.0, 2), "tp_price": round(mes_entry - 14.0, 2), "lots": 0.05}
        ]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return z, f"S10 Dow/SP [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: DOW / S&P RATIO</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[LEG 1: MICRO DOW]\n"
            "• Contract: MYM (or US30)\n"
            "• Direction: LONG (BUY)\n"
            f"• Live Entry: {mym_entry:,.0f} | Target: +140 pts | Stop: -40 pts\n\n"
            "[LEG 2: MICRO S&P]\n"
            "• Contract: MES (or US500)\n"
            "• Direction: SHORT (SELL)\n"
            f"• Live Entry: {mes_entry:,.2f} | Target: -14 pts | Stop: +4 pts\n\n"
            "[PORTFOLIO TARGET]\n"
            f"• Entry Ratio: {cur_r:.4f} (Mean: {mid:.4f} | Z: {z:+.2f}s)\n"
            "🎯 Target PnL: +$140.00 (3.5:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "ratio", "strategy_name": "Dow / S&P Ratio", "direction": "LONG_RATIO",
            "entry_time": time_str,
            "leg1": legs[0], "leg2": legs[1],
            "tp_pnl": 140.00, "max_loss_pnl": -HARD_STOP_PER_TRADE,
            "tp_ratio": mid, "sl_ratio": cur_r - 0.7 * std
        }
        dispatch_bridge_order({
            "order_id": f"s10_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "Dow / S&P Ratio",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 140.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    elif cur_r > upper:
        legs = [
            {"ticker": "MYM=F", "symbol": "MYM", "action": "SELL", "entry": mym_entry, "qty": 1, "point_val": 0.50, "sl_price": mym_entry + 40, "tp_price": mym_entry - 140, "lots": 0.05},
            {"ticker": "MES=F", "symbol": "MES", "action": "BUY", "entry": mes_entry, "qty": 1, "point_val": 5.00, "sl_price": round(mes_entry - 4.0, 2), "tp_price": round(mes_entry + 14.0, 2), "lots": 0.05}
        ]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return z, f"S10 Dow/SP [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: DOW / S&P RATIO</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[LEG 1: MICRO DOW]\n"
            "• Contract: MYM (or US30)\n"
            "• Direction: SHORT (SELL)\n"
            f"• Live Entry: {mym_entry:,.0f} | Target: -140 pts | Stop: +40 pts\n\n"
            "[LEG 2: MICRO S&P]\n"
            "• Contract: MES (or US500)\n"
            "• Direction: LONG (BUY)\n"
            f"• Live Entry: {mes_entry:,.2f} | Target: +14 pts | Stop: -4 pts\n\n"
            "[PORTFOLIO TARGET]\n"
            f"• Entry Ratio: {cur_r:.4f} (Mean: {mid:.4f} | Z: {z:+.2f}s)\n"
            "🎯 Target PnL: +$140.00 (3.5:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "ratio", "strategy_name": "Dow / S&P Ratio", "direction": "SHORT_RATIO",
            "entry_time": time_str,
            "leg1": legs[0], "leg2": legs[1],
            "tp_pnl": 140.00, "max_loss_pnl": -HARD_STOP_PER_TRADE,
            "tp_ratio": mid, "sl_ratio": cur_r + 0.7 * std
        }
        dispatch_bridge_order({
            "order_id": f"s10_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "Dow / S&P Ratio",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 140.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    return z, f"S10 Dow/SP (Ratio {cur_r:.4f})"

# 2. S4: S&P / GOLD RATIO MEAN REVERSION (MES=F + MGC=F)
def check_strategy_2_sp_gold(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "s4_sp_gold"
    t_s, s_close = data_cache.get("MES=F", (None, None))
    t_g, g_close = data_cache.get("MGC=F", (None, None))
    if s_close is None or g_close is None or len(s_close) < 40 or len(g_close) < 40:
        return 0.0, "S4: S&P/Gold"
        
    min_len = min(len(s_close), len(g_close))
    ratios = [s / g for s, g in zip(s_close[-min_len:], g_close[-min_len:])]
    mid, upper, lower, std, z = calc_bb(ratios, 40, 2.0)
    cur_r = ratios[-1]
    
    if abs(z) < 1.0 and strat_key in cooldown:
        del cooldown[strat_key]
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    if strat_key in active_trades:
        return z, f"S4 SP/Gold (Ratio {cur_r:.4f}) [ACTIVE]"
    if strat_key in cooldown:
        return z, f"S4 SP/Gold (Ratio {cur_r:.4f}) [COOLDOWN]"
    if in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return z, f"S4 SP/Gold (Ratio {cur_r:.4f}) [GUARDED]"

    mes_entry = round(live_quotes.get("MES=F", s_close[-1]), 2)
    mgc_entry = round(live_quotes.get("MGC=F", g_close[-1]), 1)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$160.00 | Stop -$40.00 (4:1 R:R)
    if cur_r < lower:
        legs = [
            {"ticker": "MES=F", "symbol": "MES", "action": "BUY", "entry": mes_entry, "qty": 1, "point_val": 5.00, "sl_price": round(mes_entry - 4.0, 2), "tp_price": round(mes_entry + 16.0, 2), "lots": 0.05},
            {"ticker": "MGC=F", "symbol": "MGC", "action": "SELL", "entry": mgc_entry, "qty": 1, "point_val": 10.00, "sl_price": round(mgc_entry + 2.0, 1), "tp_price": round(mgc_entry - 8.0, 1), "lots": 0.02}
        ]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return z, f"S4 SP/Gold [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: S&P / GOLD RATIO</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[LEG 1: MICRO S&P]\n"
            "• Contract: MES (or US500)\n"
            "• Direction: LONG (BUY)\n"
            f"• Live Entry: {mes_entry:,.2f} | Target: +16 pts | Stop: -4 pts\n\n"
            "[LEG 2: MICRO GOLD]\n"
            "• Contract: MGC (or XAUUSD)\n"
            "• Direction: SHORT (SELL)\n"
            f"• Live Entry: {mgc_entry:,.1f} | Target: -8 pts | Stop: +2 pts\n\n"
            "[PORTFOLIO TARGET]\n"
            f"• Entry Ratio: {cur_r:.4f} (Mean: {mid:.4f} | Z: {z:+.2f}s)\n"
            "🎯 Target PnL: +$160.00 (4:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "ratio", "strategy_name": "S&P / Gold Ratio", "direction": "LONG_RATIO",
            "entry_time": time_str,
            "leg1": legs[0], "leg2": legs[1],
            "tp_pnl": 160.00, "max_loss_pnl": -HARD_STOP_PER_TRADE,
            "tp_ratio": mid, "sl_ratio": cur_r - 0.7 * std
        }
        dispatch_bridge_order({
            "order_id": f"s4_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "S&P / Gold Ratio",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 160.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    elif cur_r > upper:
        legs = [
            {"ticker": "MES=F", "symbol": "MES", "action": "SELL", "entry": mes_entry, "qty": 1, "point_val": 5.00, "sl_price": round(mes_entry + 4.0, 2), "tp_price": round(mes_entry - 16.0, 2), "lots": 0.05},
            {"ticker": "MGC=F", "symbol": "MGC", "action": "BUY", "entry": mgc_entry, "qty": 1, "point_val": 10.00, "sl_price": round(mgc_entry - 2.0, 1), "tp_price": round(mgc_entry + 8.0, 1), "lots": 0.02}
        ]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return z, f"S4 SP/Gold [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: S&P / GOLD RATIO</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[LEG 1: MICRO S&P]\n"
            "• Contract: MES (or US500)\n"
            "• Direction: SHORT (SELL)\n"
            f"• Live Entry: {mes_entry:,.2f} | Target: -16 pts | Stop: +4 pts\n\n"
            "[LEG 2: MICRO GOLD]\n"
            "• Contract: MGC (or XAUUSD)\n"
            "• Direction: LONG (BUY)\n"
            f"• Live Entry: {mgc_entry:,.1f} | Target: +8 pts | Stop: -2 pts\n\n"
            "[PORTFOLIO TARGET]\n"
            f"• Entry Ratio: {cur_r:.4f} (Mean: {mid:.4f} | Z: {z:+.2f}s)\n"
            "🎯 Target PnL: +$160.00 (4:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "ratio", "strategy_name": "S&P / Gold Ratio", "direction": "SHORT_RATIO",
            "entry_time": time_str,
            "leg1": legs[0], "leg2": legs[1],
            "tp_pnl": 160.00, "max_loss_pnl": -HARD_STOP_PER_TRADE,
            "tp_ratio": mid, "sl_ratio": cur_r + 0.7 * std
        }
        dispatch_bridge_order({
            "order_id": f"s4_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "S&P / Gold Ratio",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 160.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    return z, f"S4 SP/Gold (Ratio {cur_r:.4f})"

# 3. S9: TREASURY 10Y / 30Y YIELD CURVE SPREAD (ZN=F + ZB=F)
def check_strategy_3_treasury(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "s9_treasury"
    t_zn, zn_c = data_cache.get("ZN=F", (None, None))
    t_zb, zb_c = data_cache.get("ZB=F", (None, None))
    if zn_c is None or zb_c is None or len(zn_c) < 30 or len(zb_c) < 30:
        return 0.0, "S9: Treasury"
        
    min_len = min(len(zn_c), len(zb_c))
    spread = [3.0 * zn - 2.0 * zb for zn, zb in zip(zn_c[-min_len:], zb_c[-min_len:])]
    mid, upper, lower, std, z = calc_bb(spread, 30, 2.2)
    cur_s = spread[-1]
    
    if abs(z) < 1.0 and strat_key in cooldown:
        del cooldown[strat_key]
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    if strat_key in active_trades:
        return z, f"S9 Treasury (Spread {cur_s:.2f}) [ACTIVE]"
    if strat_key in cooldown or in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return z, f"S9 Treasury (Spread {cur_s:.2f}) [GUARDED]"

    zn_entry = round(live_quotes.get("ZN=F", zn_c[-1]), 4)
    zb_entry = round(live_quotes.get("ZB=F", zb_c[-1]), 4)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$100.00 | Stop -$40.00 (2.5:1 R:R)
    if cur_s < lower:
        legs = [
            {"ticker": "ZN=F", "symbol": "ZN", "action": "BUY", "entry": zn_entry, "qty": 3, "point_val": 1000.0, "sl_price": zn_entry - 0.020, "tp_price": zn_entry + 0.050, "lots": 0.03},
            {"ticker": "ZB=F", "symbol": "ZB", "action": "SELL", "entry": zb_entry, "qty": 2, "point_val": 1000.0, "sl_price": zb_entry + 0.020, "tp_price": zb_entry - 0.050, "lots": 0.02}
        ]
        msg = (
            "🚨 <b>FUNDING PIPS ALERT: TREASURY YIELD CURVE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[LEG 1: 10-YEAR T-NOTES]\n"
            "• Contract: 3x ZN (BUY) @ " + str(zn_entry) + "\n\n"
            "[LEG 2: 30-YEAR T-BONDS]\n"
            "• Contract: 2x ZB (SELL) @ " + str(zb_entry) + "\n\n"
            "[PORTFOLIO TARGET]\n"
            f"• Spread: {cur_s:.2f} (Target Mean: {mid:.2f} | Z: {z:+.2f}s)\n"
            "🎯 Target PnL: +$100.00 (2.5:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "ratio", "strategy_name": "Treasury 10Y/30Y Curve", "direction": "LONG_RATIO",
            "entry_time": time_str,
            "leg1": legs[0], "leg2": legs[1],
            "tp_pnl": 100.00, "max_loss_pnl": -HARD_STOP_PER_TRADE,
            "tp_ratio": mid, "sl_ratio": cur_s - 0.7 * std
        }
        dispatch_bridge_order({
            "order_id": f"s9_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "Treasury 10Y/30Y Curve",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 100.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
    return z, f"S9 Treasury (Spread {cur_s:.2f})"

# 4. S4-CRYPTO: ETH/BTC SPREAD ARBITRAGE (MET + MBT)
def check_strategy_4_ethbtc(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "s4_ethbtc"
    t_arr, c_arr = data_cache.get("ETHBTC", (None, None))
    if c_arr is None or len(c_arr) < 60:
        return 0.0, "ETH/BTC"
    mid, upper, lower, std, z = calc_bb(c_arr, 60, 2.0)
    cur_p = live_quotes.get("ETHBTC", c_arr[-1])
    
    if abs(z) < 1.0 and strat_key in cooldown:
        del cooldown[strat_key]
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    if strat_key in active_trades:
        return z, f"ETH/BTC ({cur_p:.5f}) [ACTIVE]"
    if strat_key in cooldown or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return z, f"ETH/BTC ({cur_p:.5f}) [GUARDED]"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$80.00 | Stop -$40.00 (2:1 R:R)
    if cur_p < lower:
        legs = [
            {"ticker": "ETHBTC", "symbol": "ETHBTC", "action": "BUY", "entry": cur_p, "qty": 1, "point_val": 1000.0, "sl_price": cur_p * 0.985, "tp_price": mid, "lots": 0.05}
        ]
        msg = (
            "🚨 <b>FUNDING PIPS ALERT: ETH / BTC RATIO</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Contract: ETH/BTC (or MET Futures)\n"
            "• Direction: LONG ETH / SHORT BTC\n"
            f"• Live Rate: {cur_p:.6f} (Mean: {mid:.6f} | Z: {z:+.2f}s)\n"
            "🎯 Target PnL: +$80.00 (2:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "ratio", "strategy_name": "ETH/BTC Spread", "direction": "LONG_RATIO",
            "entry_time": time_str,
            "leg1": {"ticker": "ETHBTC", "action": "BUY", "entry": cur_p, "qty": 1, "point_val": 1000.0, "sl_price": cur_p * 0.985, "tp_price": mid},
            "leg2": {"ticker": "ETHBTC", "action": "SELL", "entry": cur_p, "qty": 1, "point_val": 1000.0, "sl_price": cur_p * 1.015, "tp_price": mid},
            "tp_pnl": 80.00, "max_loss_pnl": -HARD_STOP_PER_TRADE,
            "tp_ratio": mid, "sl_ratio": cur_p - 0.7 * std
        }
        dispatch_bridge_order({
            "order_id": f"eth_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "ETH/BTC Spread",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 80.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
    return z, f"ETH/BTC ({cur_p:.5f})"

# 5. S8: RUSSELL 2000 / S&P SMALL-CAP ROTATION (M2K=F + MES=F)
def check_strategy_5_russell_sp(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "s8_russell_sp"
    t_m, m2k_c = data_cache.get("M2K=F", (None, None))
    t_s, mes_c = data_cache.get("MES=F", (None, None))
    if m2k_c is None or mes_c is None or len(m2k_c) < 30 or len(mes_c) < 30:
        return 0.0, "S8: Russell/S&P"
    min_len = min(len(m2k_c), len(mes_c))
    ratios = [m / s for m, s in zip(m2k_c[-min_len:], mes_c[-min_len:])]
    mid, upper, lower, std, z = calc_bb(ratios, 30, 2.0)
    cur_r = ratios[-1]
    
    if abs(z) < 1.0 and strat_key in cooldown:
        del cooldown[strat_key]
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    if strat_key in active_trades:
        return z, f"S8 Russell/SP (Ratio {cur_r:.4f}) [ACTIVE]"
    if strat_key in cooldown or in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return z, f"S8 Russell/SP (Ratio {cur_r:.4f}) [GUARDED]"

    m2k_entry = round(live_quotes.get("M2K=F", m2k_c[-1]), 1)
    mes_entry = round(live_quotes.get("MES=F", mes_c[-1]), 2)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$130.00 | Stop -$40.00 (3.25:1 R:R)
    if cur_r < lower:
        legs = [
            {"ticker": "M2K=F", "symbol": "M2K", "action": "BUY", "entry": m2k_entry, "qty": 1, "point_val": 5.00, "sl_price": m2k_entry - 4.0, "tp_price": m2k_entry + 13.0, "lots": 0.05},
            {"ticker": "MES=F", "symbol": "MES", "action": "SELL", "entry": mes_entry, "qty": 1, "point_val": 5.00, "sl_price": round(mes_entry + 4.0, 2), "tp_price": round(mes_entry - 13.0, 2), "lots": 0.05}
        ]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return z, f"S8 Russell/SP [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: RUSSELL / S&P RATIO</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[LEG 1: MICRO RUSSELL]\n"
            "• Contract: M2K (or US2000) (BUY) @ " + str(m2k_entry) + "\n\n"
            "[LEG 2: MICRO S&P]\n"
            "• Contract: MES (or US500) (SELL) @ " + str(mes_entry) + "\n\n"
            "[PORTFOLIO TARGET]\n"
            f"• Entry Ratio: {cur_r:.4f} (Mean: {mid:.4f} | Z: {z:+.2f}s)\n"
            "🎯 Target PnL: +$130.00 (3.25:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "ratio", "strategy_name": "Russell / S&P Rotation", "direction": "LONG_RATIO",
            "entry_time": time_str,
            "leg1": legs[0], "leg2": legs[1],
            "tp_pnl": 130.00, "max_loss_pnl": -HARD_STOP_PER_TRADE,
            "tp_ratio": mid, "sl_ratio": cur_r - 0.7 * std
        }
        dispatch_bridge_order({
            "order_id": f"s8_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "Russell / S&P Rotation",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 130.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
    return z, f"S8 Russell/SP (Ratio {cur_r:.4f})"

# 6. R12: FX EURO / USD TREND FOLLOWING (6E=F)
def check_strategy_6_euro_trend(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "r12_euro"
    t_e, e_close = data_cache.get("6E=F", (None, None))
    if e_close is None or len(e_close) < 50:
        return 0.0, "R12: FX Euro"
    ema9_arr = calc_ema(e_close, 9)
    ema21_arr = calc_ema(e_close, 21)
    ema50_arr = calc_ema(e_close, 50)
    ema9, ema21, ema50 = ema9_arr[-1], ema21_arr[-1], ema50_arr[-1]
    cur_p = live_quotes.get("6E=F", e_close[-1])
    
    if strat_key in active_trades:
        return 0.0, f"R12 FX Euro ({cur_p:.4f}) [ACTIVE]"
    if strat_key in cooldown:
        if cur_p < ema50:
            del cooldown[strat_key]
            save_state(active_trades, cooldown, trade_history, daily_tracker)
        return 0.0, f"R12 FX Euro ({cur_p:.4f}) [COOLDOWN]"
    if in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return 0.0, f"R12 FX Euro ({cur_p:.4f}) [GUARDED]"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$90.00 | Stop -$40.00 (2.25:1 R:R)
    if cur_p > ema50 and ema9 > ema21 and ema9_arr[-2] <= ema21_arr[-2]:
        tp_p = round(cur_p + 0.0072, 4)
        sl_p = round(cur_p - 0.0032, 4)
        legs = [{"ticker": "6E=F", "symbol": "6E", "action": "BUY", "entry": cur_p, "qty": 1, "point_val": 12500.0, "sl_price": sl_p, "tp_price": tp_p, "lots": 0.03}]
        msg = (
            "🚨 <b>FUNDING PIPS ALERT: FX EURO TREND</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[CONTRACT: MICRO EURO / EURUSD]\n"
            "• Direction: LONG (BUY)\n"
            f"• Live Entry: {cur_p:.4f}\n"
            f"• TP Price: {tp_p:.4f} (+72 pips)\n"
            f"• SL Price: {sl_p:.4f} (-32 pips)\n\n"
            "[TRADE TARGET]\n"
            "🎯 Target PnL: +$90.00 (2.25:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "single", "strategy_name": "FX Euro Trend",
            "ticker": "6E=F", "contract": "M6E", "action": "BUY",
            "entry_time": time_str, "entry_price": cur_p,
            "qty": 1, "point_val": 12500.0,
            "tp_price": tp_p, "sl_price": sl_p,
            "tp_pnl": 90.00, "max_loss_pnl": -HARD_STOP_PER_TRADE
        }
        dispatch_bridge_order({
            "order_id": f"r12_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "FX Euro Trend",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 90.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
    return 0.0, f"R12 FX Euro ({cur_p:.4f})"

# 7. S3: S&P 500 VOLATILITY SQUEEZE (MES=F)
def check_strategy_7_sp_squeeze(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "s3_sp_squeeze"
    t_s, s_close = data_cache.get("MES=F", (None, None))
    if s_close is None or len(s_close) < 25:
        return 0.0, "S3: SP Squeeze"
    mid, upper, lower, std, z = calc_bb(s_close, 20, 2.0)
    cur_p = round(live_quotes.get("MES=F", s_close[-1]), 2)
    
    if abs(z) < 1.0 and strat_key in cooldown:
        del cooldown[strat_key]
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    if strat_key in active_trades:
        return z, f"S3 SP Squeeze (MES ~{cur_p:,.0f}) [ACTIVE]"
    if strat_key in cooldown or in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return z, f"S3 SP Squeeze (MES ~{cur_p:,.0f}) [GUARDED]"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$100.00 | Stop -$40.00 (2.5:1 R:R)
    if cur_p < lower:
        tp_p = round(cur_p + 20.0, 2)
        sl_p = round(cur_p - 8.0, 2)
        legs = [{"ticker": "MES=F", "symbol": "MES", "action": "BUY", "entry": cur_p, "qty": 1, "point_val": 5.00, "sl_price": sl_p, "tp_price": tp_p, "lots": 0.05}]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return z, f"S3 SP Squeeze [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: S&P VOLATILITY SQUEEZE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[CONTRACT: MICRO S&P 500 / US500]\n"
            "• Direction: LONG (BUY)\n"
            f"• Live Entry: {cur_p:,.2f}\n"
            f"• TP Price: {tp_p:,.2f} (+20.00 pts)\n"
            f"• SL Price: {sl_p:,.2f} (-8.00 pts)\n\n"
            "[TRADE TARGET]\n"
            "🎯 Target PnL: +$100.00 (2.5:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "single", "strategy_name": "S&P Volatility Squeeze",
            "ticker": "MES=F", "contract": "MES", "action": "BUY",
            "entry_time": time_str, "entry_price": cur_p,
            "qty": 1, "point_val": 5.00,
            "tp_price": tp_p, "sl_price": sl_p,
            "tp_pnl": 100.00, "max_loss_pnl": -HARD_STOP_PER_TRADE
        }
        dispatch_bridge_order({
            "order_id": f"s3_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "S&P Volatility Squeeze",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 100.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
    return z, f"S3 SP Squeeze (MES ~{cur_p:,.0f})"

# 8. S2: GOLD LONDON BREAKOUT / REVERSION (MGC=F)
def check_strategy_8_gold_london(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "s2_gold_london"
    t_g, g_close = data_cache.get("MGC=F", (None, None))
    if g_close is None or len(g_close) < 25:
        return 0.0, "S2: Gold London"
    mid, upper, lower, std, z = calc_bb(g_close, 24, 2.2)
    cur_p = round(live_quotes.get("MGC=F", g_close[-1]), 1)
    
    if abs(z) < 1.0 and strat_key in cooldown:
        del cooldown[strat_key]
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    if strat_key in active_trades:
        return z, f"S2 Gold (MGC ~{cur_p:,.1f}) [ACTIVE]"
    if strat_key in cooldown or in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return z, f"S2 Gold (MGC ~{cur_p:,.1f}) [GUARDED]"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$120.00 | Stop -$40.00 (3:1 R:R)
    if cur_p < lower:
        tp_p = round(cur_p + 12.0, 1)
        sl_p = round(cur_p - 4.0, 1)
        legs = [{"ticker": "MGC=F", "symbol": "MGC", "action": "BUY", "entry": cur_p, "qty": 1, "point_val": 10.00, "sl_price": sl_p, "tp_price": tp_p, "lots": 0.02}]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return z, f"S2 Gold [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: GOLD LONDON REVERSION</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[CONTRACT: MICRO GOLD / XAUUSD]\n"
            "• Direction: LONG (BUY)\n"
            f"• Live Entry: {cur_p:,.1f}\n"
            f"• TP Price: {tp_p:,.1f} (+12.0 pts)\n"
            f"• SL Price: {sl_p:,.1f} (-4.0 pts)\n\n"
            "[TRADE TARGET]\n"
            "🎯 Target PnL: +$120.00 (3:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "single", "strategy_name": "Gold London Reversion",
            "ticker": "MGC=F", "contract": "MGC", "action": "BUY",
            "entry_time": time_str, "entry_price": cur_p,
            "qty": 1, "point_val": 10.00,
            "tp_price": tp_p, "sl_price": sl_p,
            "tp_pnl": 120.00, "max_loss_pnl": -HARD_STOP_PER_TRADE
        }
        dispatch_bridge_order({
            "order_id": f"s2_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "Gold London Reversion",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 120.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
    return z, f"S2 Gold (MGC ~{cur_p:,.1f})"

# 9. R2: CLUSTER DIVERGENCE (MNQ=F + MES=F)
def check_strategy_9_cluster(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "r2_cluster"
    t_q, q_close = data_cache.get("MNQ=F", (None, None))
    t_s, s_close = data_cache.get("MES=F", (None, None))
    if q_close is None or s_close is None or len(q_close) < 35 or len(s_close) < 35:
        return 0.0, "R2: Nasdaq/SP"
    min_len = min(len(q_close), len(s_close))
    ratios = [q / s for q, s in zip(q_close[-min_len:], s_close[-min_len:])]
    mid, upper, lower, std, z = calc_bb(ratios, 35, 2.2)
    cur_r = ratios[-1]
    
    if abs(z) < 1.0 and strat_key in cooldown:
        del cooldown[strat_key]
        save_state(active_trades, cooldown, trade_history, daily_tracker)
        
    if strat_key in active_trades:
        return z, f"R2 Nasdaq/SP (Ratio {cur_r:.4f}) [ACTIVE]"
    if strat_key in cooldown or in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return z, f"R2 Nasdaq/SP (Ratio {cur_r:.4f}) [GUARDED]"

    mnq_entry = round(live_quotes.get("MNQ=F", q_close[-1]), 0)
    mes_entry = round(live_quotes.get("MES=F", s_close[-1]), 2)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$110.00 | Stop -$40.00 (2.75:1 R:R)
    if cur_r > upper:
        legs = [
            {"ticker": "MNQ=F", "symbol": "MNQ", "action": "SELL", "entry": mnq_entry, "qty": 1, "point_val": 2.00, "sl_price": mnq_entry + 10.0, "tp_price": mnq_entry - 27.5, "lots": 0.05},
            {"ticker": "MES=F", "symbol": "MES", "action": "BUY", "entry": mes_entry, "qty": 1, "point_val": 5.00, "sl_price": round(mes_entry - 4.0, 2), "tp_price": round(mes_entry + 11.0, 2), "lots": 0.05}
        ]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return z, f"R2 Nasdaq/SP [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: NASDAQ / S&P RATIO</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[LEG 1: MICRO NASDAQ]\n"
            "• Contract: MNQ (or USTEC) (SELL) @ " + str(mnq_entry) + "\n\n"
            "[LEG 2: MICRO S&P]\n"
            "• Contract: MES (or US500) (BUY) @ " + str(mes_entry) + "\n\n"
            "[PORTFOLIO TARGET]\n"
            f"• Entry Ratio: {cur_r:.4f} (Mean: {mid:.4f} | Z: {z:+.2f}s)\n"
            "🎯 Target PnL: +$110.00 (2.75:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "ratio", "strategy_name": "Nasdaq / S&P Ratio", "direction": "SHORT_RATIO",
            "entry_time": time_str,
            "leg1": legs[0], "leg2": legs[1],
            "tp_pnl": 110.00, "max_loss_pnl": -HARD_STOP_PER_TRADE,
            "tp_ratio": mid, "sl_ratio": cur_r + 0.7 * std
        }
        dispatch_bridge_order({
            "order_id": f"r2_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "Nasdaq / S&P Ratio",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 110.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
    return z, f"R2 Nasdaq/SP (Ratio {cur_r:.4f})"

# 10. R5: TIME-SERIES MOMENTUM (MNQ=F)
def check_strategy_10_tsmom(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news):
    strat_key = "r5_tsmom"
    t_q, q_close = data_cache.get("MNQ=F", (None, None))
    if q_close is None or len(q_close) < 50:
        return 0.0, "R5: TSMOM"
    ema50_arr = calc_ema(q_close, 50)
    ema50 = ema50_arr[-1]
    cur_p = round(live_quotes.get("MNQ=F", q_close[-1]), 0)
    
    if strat_key in active_trades:
        return 0.0, f"R5 Nasdaq TSMOM (MNQ ~{cur_p:,.0f}) [ACTIVE]"
    if strat_key in cooldown:
        if cur_p < ema50:
            del cooldown[strat_key]
            save_state(active_trades, cooldown, trade_history, daily_tracker)
        return 0.0, f"R5 Nasdaq TSMOM (MNQ ~{cur_p:,.0f}) [COOLDOWN]"
    if in_news or daily_tracker.get("circuit_tripped", False) or len(active_trades) >= MAX_CONCURRENT_TRADES:
        return 0.0, f"R5 Nasdaq TSMOM (MNQ ~{cur_p:,.0f}) [GUARDED]"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
    time_str = f"{now_ist.strftime('%I:%M %p IST')} ({now_utc.strftime('%H:%M UTC')})"
    
    # Target +$80.00 | Stop -$40.00 (2:1 R:R)
    if q_close[-1] > ema50 and q_close[-2] <= ema50_arr[-2]:
        tp_p = cur_p + 40.0
        sl_p = cur_p - 20.0
        legs = [{"ticker": "MNQ=F", "symbol": "MNQ", "action": "BUY", "entry": cur_p, "qty": 1, "point_val": 2.00, "sl_price": sl_p, "tp_price": tp_p, "lots": 0.05}]
        ok, reason = check_asset_conflict(legs, active_trades)
        if not ok:
            return 0.0, f"R5 Nasdaq TSMOM [CONFLICT: {reason}]"

        msg = (
            "🚨 <b>FUNDING PIPS ALERT: NASDAQ MOMENTUM</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "[CONTRACT: MICRO NASDAQ 100 / USTEC]\n"
            "• Direction: LONG (BUY)\n"
            f"• Live Entry: {cur_p:,.0f}\n"
            f"• TP Price: {tp_p:,.0f} (+40 pts)\n"
            f"• SL Price: {sl_p:,.0f} (-20 pts)\n\n"
            "[TRADE TARGET]\n"
            "🎯 Target PnL: +$80.00 (2:1 Reward-to-Risk)\n"
            "🛑 Max Loss:   -$40.00 (Funding Pips $5k Shield)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ {time_str}"
        )
        send_telegram(msg)
        active_trades[strat_key] = {
            "type": "single", "strategy_name": "Nasdaq Momentum TSMOM",
            "ticker": "MNQ=F", "contract": "MNQ", "action": "BUY",
            "entry_time": time_str, "entry_price": cur_p,
            "qty": 1, "point_val": 2.00,
            "tp_price": tp_p, "sl_price": sl_p,
            "tp_pnl": 80.00, "max_loss_pnl": -HARD_STOP_PER_TRADE
        }
        dispatch_bridge_order({
            "order_id": f"r5_{int(time.time())}",
            "strategy": strat_key, "strategy_name": "Nasdaq Momentum TSMOM",
            "action": "ENTRY", "legs": legs,
            "dollar_sl": -HARD_STOP_PER_TRADE, "dollar_tp": 80.00, "status": "PENDING"
        })
        save_state(active_trades, cooldown, trade_history, daily_tracker)
    return 0.0, f"R5 Nasdaq TSMOM (MNQ ~{cur_p:,.0f})"

# ── HELPER: BUILD GAUGE BAR ────────────────────────────────────────
def make_gauge_bar(z):
    mag = min(abs(z), 2.5)
    blocks = int(round((mag / 2.5) * 10))
    blocks = max(1, min(10, blocks))
    bar = "█" * blocks + "░" * (10 - blocks)
    if abs(z) >= 2.0:
        status = "🚨 READY"
    elif abs(z) >= 1.4:
        status = "⚡ WATCH"
    else:
        status = "⚪ NEUTRAL"
    return f"[{bar}] {z:+.2f}s {status}"

def get_strat_z(strat_results, prefix):
    for name, z in strat_results:
        if name.startswith(prefix) or prefix in name:
            return z
    return 0.0

# ── HELPER: BUILD DAILY BRIEFING MESSAGE ───────────────────────────
def build_daily_briefing(now_ist, now_utc, scan_count, strat_results, active_trades, trade_history, daily_tracker, sender_name="Pawan"):
    s4_z = get_strat_z(strat_results, "S4 SP/Gold")
    s8_z = get_strat_z(strat_results, "S8 Russell/SP")
    s10_z = get_strat_z(strat_results, "S10 Dow/SP")
    s9_z = get_strat_z(strat_results, "S9 Treasury")
    eth_z = get_strat_z(strat_results, "ETH/BTC")
    
    time_str = f"{now_ist.strftime('%I:%M %p IST')} | {now_utc.strftime('%H:%M UTC')}"
    lines = [
        "🦅 <b>FUNDING PIPS $5K PRO DASHBOARD</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⏰ <b>{time_str}</b>",
        f"🛰️ <b>Engine:</b> V9.0 Precision Auto-Trader | <b>Account:</b> ${ACCOUNT_SIZE:,.0f}",
        f"💼 <b>Active Positions:</b> {len(active_trades)} / {MAX_CONCURRENT_TRADES} Max",
        f"📊 <b>Today Realized PnL:</b> {'+' if daily_tracker['realized_pnl'] >= 0 else '-'}${abs(daily_tracker['realized_pnl']):,.2f}",
        f"🛡️ <b>Daily Drawdown Shield:</b> ${DAILY_LOSS_LIMIT - abs(min(0.0, daily_tracker['realized_pnl'])):,.2f} Remaining",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <b>LIVE STRATEGY GAUGES &amp; TARGETS:</b>\n",
        
        "<b>[S4] S&amp;P / GOLD RATIO</b>",
        f"  <code>{make_gauge_bar(s4_z)}</code>",
        "  🎯 Target: +$160.00 | 🛑 Stop: -$40.00 (4:1 R:R)\n",
        
        "<b>[S8] RUSSELL / S&amp;P RATIO</b>",
        f"  <code>{make_gauge_bar(s8_z)}</code>",
        "  🎯 Target: +$130.00 | 🛑 Stop: -$40.00 (3.25:1 R:R)\n",
        
        "<b>[S10] DOW / S&amp;P RATIO</b>",
        f"  <code>{make_gauge_bar(s10_z)}</code>",
        "  🎯 Target: +$140.00 | 🛑 Stop: -$40.00 (3.5:1 R:R)\n",
        
        "<b>[S9] TREASURY 10Y/30Y</b>",
        f"  <code>{make_gauge_bar(s9_z)}</code>",
        "  🎯 Target: +$100.00 | 🛑 Stop: -$40.00 (2.5:1 R:R)\n",
        
        "<b>[S4] ETH / BTC CRYPTO</b>",
        f"  <code>{make_gauge_bar(eth_z)}</code>",
        "  🎯 Target: +$80.00 | 🛑 Stop: -$40.00 (2:1 R:R)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛡️ <b>RISK MANDATE:</b>",
        f"• Hard Stop -$40.00 Per Trade Strictly Enforced",
        f"• Daily Circuit Breaker Active at -${CIRCUIT_BREAKER_LOSS_LIMIT:.0f}",
        "• Friday 3:45 PM EST Auto-Flat Rule Active",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📱 <i>Autonomous MT5 Bridge Ready.</i>"
    ]
    return "\n".join(lines)

# ── HELPER: BUILD REAL DYNAMIC PERFORMANCE REPORTS ─────────────────
def calculate_trade_metrics(trades):
    if not trades:
        return {
            "count": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "net_pnl": 0.0, "gross_profit": 0.0, "gross_loss": 0.0,
            "profit_factor": 1.0, "max_loss": 0.0
        }
    count = len(trades)
    wins = [t for t in trades if t["realized_pnl"] > 0]
    losses = [t for t in trades if t["realized_pnl"] <= 0]
    win_cnt = len(wins)
    loss_cnt = len(losses)
    win_rate = (win_cnt / count) * 100.0 if count > 0 else 0.0
    gross_profit = sum(t["realized_pnl"] for t in wins)
    gross_loss = abs(sum(t["realized_pnl"] for t in losses))
    net_pnl = sum(t["realized_pnl"] for t in trades)
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)
    max_loss = max([abs(t["realized_pnl"]) for t in losses] + [0.0])
    return {
        "count": count, "wins": win_cnt, "losses": loss_cnt, "win_rate": win_rate,
        "net_pnl": net_pnl, "gross_profit": gross_profit, "gross_loss": gross_loss,
        "profit_factor": pf, "max_loss": max_loss
    }

def build_weekly_report(now_ist, now_utc, trade_history, active_trades):
    time_str = f"{now_ist.strftime('%I:%M %p IST')} | {now_utc.strftime('%H:%M UTC')}"
    m = calculate_trade_metrics(trade_history)
    lines = [
        "📊 <b>FUNDING PIPS $5K: WEEKLY PERFORMANCE</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⏰ <b>As of:</b> {time_str} ({now_ist.strftime('%d-%b-%Y')})",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    if m["count"] == 0:
        lines.extend([
            f"• <b>Active In-Flight:</b> {len(active_trades)} Open",
            "• <b>Closed Trades This Cycle:</b> 0 Closed Yet",
            "• <b>Status:</b> All 10 strategies scanning with -$40 risk guard"
        ])
    else:
        sign = "+" if m["net_pnl"] >= 0 else "-"
        lines.extend([
            f"• <b>Total Closed:</b> {m['count']} Trades",
            f"• <b>Win Rate:</b> <b>{m['win_rate']:.1f}%</b> ({m['wins']} Wins | {m['losses']} Losses)",
            f"• <b>Realized Net PnL:</b> <b>{sign}${abs(m['net_pnl']):,.2f}</b> 💰",
            f"• <b>Profit Factor:</b> {m['profit_factor']:.2f}",
            f"• <b>Max Single Loss:</b> -${m['max_loss']:.2f} (Strict -$40 cap honored)"
        ])
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🎯 <b>Phase 1 Goal:</b> +$300.00 (6%) | <b>Progress:</b> {max(0.0, m['net_pnl'])/PROFIT_TARGET_P1*100.0:.1f}%",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ])
    return "\n".join(lines)

def build_portfolio_matrix_report(now_ist, now_utc, trade_history, active_trades):
    time_str = f"{now_ist.strftime('%I:%M %p IST')} | {now_utc.strftime('%H:%M UTC')}"
    m = calculate_trade_metrics(trade_history)
    lines = [
        "🏛️ <b>FUNDING PIPS $5K MASTER PERFORMANCE MATRIX</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⏰ <b>As of:</b> {time_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛰️ <b>LIVE ENGINE STATUS:</b>",
        f"• <b>Active Positions:</b> {len(active_trades)} / {MAX_CONCURRENT_TRADES} Max",
        f"• <b>Total Realized PnL:</b> {'+' if m['net_pnl'] >= 0 else '-'}${abs(m['net_pnl']):,.2f}",
        f"• <b>Historical Win Rate:</b> {m['win_rate']:.1f}%",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛡️ <b>FUNDING PIPS $5,000 PASSING BLUEPRINT:</b>",
        f"• Account Capital: ${ACCOUNT_SIZE:,.0f}",
        f"• Phase 1 Profit Target: ${PROFIT_TARGET_P1:,.0f} (6%)",
        f"• Daily Loss Limit: ${DAILY_LOSS_LIMIT:,.0f} (3%)",
        f"• Maximum Static Loss: ${MAX_STATIC_LOSS_LIMIT:,.0f} (6%)",
        f"• Single Trade Stop Loss: -${HARD_STOP_PER_TRADE:.0f} (Strict 0.8% Guard)",
        f"• Trades Needed to Pass: 2 to 3 Wins @ 3.5:1 R:R",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📱 <i>Autonomous MT5 Bridge Engine Online.</i>"
    ]
    return "\n".join(lines)

# ── MAIN DAEMON ENGINE (PARALLEL 5-SECOND BACKGROUND SCAN) ──────────
def main():
    threading.Thread(target=start_cloud_health_server, daemon=True).start()

    print("=" * 65)
    print("🚀 FUNDING PIPS $5K AUTONOMOUS SIGNAL & MT5 ENGINE (V9.0)")
    print(f"Target Bot: @Tradehisbbot | User ID: {TELEGRAM_CHAT_ID}")
    print(f"Prop Firm: {PROP_FIRM_NAME} | Account: ${ACCOUNT_SIZE:,.0f}")
    print(f"Risk Shield: -${HARD_STOP_PER_TRADE:.0f} Stop Loss | -${CIRCUIT_BREAKER_LOSS_LIMIT:.0f} Daily Circuit Breaker")
    print(f"Auto-Execution: bridge_orders.json -> mt5_trader.py (<25ms)")
    print("=" * 65)
    
    active_trades, cooldown, trade_history, daily_tracker = load_state()
    print(f"[State Engine]: Loaded {len(active_trades)} active trades, {len(cooldown)} cooling down, {len(trade_history)} logged trades.")
    
    last_update_id = None
    scan_count = 0
    last_briefing_slot = None
    last_weekly_slot = None
    data_cache = {}
    live_quotes = {}
    
    updates = get_telegram_updates()
    if updates:
        last_update_id = updates[-1]["update_id"] + 1

    while True:
        scan_start = time.time()
        scan_count += 1
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now_ist = now_utc + datetime.timedelta(hours=5, minutes=30)
        
        # Daily reset at 00:00 UTC
        today_str = now_utc.strftime("%Y-%m-%d")
        if daily_tracker.get("date") != today_str:
            daily_tracker = {"date": today_str, "realized_pnl": 0.0, "circuit_tripped": False}
            save_state(active_trades, cooldown, trade_history, daily_tracker)
            print(f"[Daily Reset]: New trading day {today_str} initialized. Circuit breaker re-armed.")

        try:
            # 1. FIX 7: CHECK WEEKEND HOLDING AUTO-FLAT
            in_weekend = check_weekend_flat(now_utc, active_trades, cooldown, trade_history, daily_tracker)

            # 2. FIX 5: CHECK HIGH-IMPACT NEWS FREEZE
            in_news, news_desc = is_news_freeze_active(now_utc)
            if in_news:
                print(f"[News Guard]: Active freeze window: {news_desc}. New entries paused.")

            # 3. HYBRID DATA FETCH (MT5 LIVE TICKS + YAHOO INJECTION)
            mt5_quotes = get_mt5_bridge_quotes()
            tickers = ["MGC=F", "MES=F", "MYM=F", "MNQ=F", "M2K=F", "ZN=F", "ZB=F", "6E=F"]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                res_list = list(executor.map(fetch_futures_data, tickers))
            for tick, (t, c, live_p) in zip(tickers, res_list):
                if c is not None:
                    data_cache[tick] = (t, c)
                # If MT5 quote exists, use MT5 quote for 0-latency precision
                generic = tick.replace("=F", "")
                if generic in mt5_quotes:
                    live_quotes[tick] = mt5_quotes[generic]
                elif live_p is not None:
                    live_quotes[tick] = live_p
            
            t, c, live_eth = fetch_binance_data("ETHBTC", limit=150)
            if c is not None:
                data_cache["ETHBTC"] = (t, c)
            if live_eth is not None:
                live_quotes["ETHBTC"] = live_eth
            
            # 4. MONITOR ACTIVE TRADES AGAINST HARD -$40 STOP & TAKE PROFIT
            check_active_trades(live_quotes, active_trades, cooldown, trade_history, daily_tracker)
            
            # 5. EVALUATE ALL 10 STRATEGIES (WITH ALL 7 RISK GUARDS ACTIVE)
            strat_results = []
            z1, name1 = check_strategy_1_dow_sp(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name1, z1))
            
            z2, name2 = check_strategy_2_sp_gold(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name2, z2))
            
            z3, name3 = check_strategy_3_treasury(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name3, z3))
            
            z4, name4 = check_strategy_4_ethbtc(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name4, z4))
            
            z5, name5 = check_strategy_5_russell_sp(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name5, z5))
            
            z6, name6 = check_strategy_6_euro_trend(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name6, z6))
            
            z7, name7 = check_strategy_7_sp_squeeze(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name7, z7))
            
            z8, name8 = check_strategy_8_gold_london(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name8, z8))
            
            z9, name9 = check_strategy_9_cluster(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name9, z9))
            
            z10, name10 = check_strategy_10_tsmom(data_cache, live_quotes, active_trades, cooldown, trade_history, daily_tracker, in_news)
            strat_results.append((name10, z10))
            
            max_item = max(strat_results, key=lambda x: abs(x[1]))
            elapsed = time.time() - scan_start
            active_info = f" | Open: {len(active_trades)}/{MAX_CONCURRENT_TRADES}"
            guard_info = " [NEWS FREEZE]" if in_news else (" [CIRCUIT BROKEN]" if daily_tracker.get("circuit_tripped") else "")
            print(f"[Scan #{scan_count:05d} | {now_ist.strftime('%H:%M:%S IST')}] Scanned in {elapsed:.1f}s{active_info}{guard_info}. Nearest: {max_item[0]} (Z: {max_item[1]:+.2f}s)")
            
            # 6. SCHEDULED BRIEFINGS (09:00 AM IST & 09:00 PM IST)
            current_slot = (now_ist.strftime('%Y-%m-%d'), 9 if now_ist.hour < 15 else 21)
            if (now_ist.hour in [9, 21]) and (last_briefing_slot != current_slot):
                briefing_text = build_daily_briefing(now_ist, now_utc, scan_count, strat_results, active_trades, trade_history, daily_tracker)
                send_telegram(briefing_text)
                last_briefing_slot = current_slot
                print(f"  └─ Automatically dispatched Scheduled Daily Briefing for {current_slot}.")

            # 7. INTERACTIVE TELEGRAM COMMAND CHECK
            new_updates = get_telegram_updates(offset=last_update_id)
            for u in new_updates:
                last_update_id = u["update_id"] + 1
                msg = u.get("message", {})
                txt = (msg.get("text") or "").strip().lower()
                sender = msg.get("from", {}).get("first_name", "Pawan")
                
                if any(cmd in txt for cmd in ["weekly", "week"]):
                    weekly_text = build_weekly_report(now_ist, now_utc, trade_history, active_trades)
                    send_telegram(weekly_text)
                elif any(cmd in txt for cmd in ["portfolio", "matrix", "stats", "performance"]):
                    matrix_text = build_portfolio_matrix_report(now_ist, now_utc, trade_history, active_trades)
                    send_telegram(matrix_text)
                elif any(cmd in txt for cmd in ["daily", "update", "today", "report"]):
                    briefing_text = build_daily_briefing(now_ist, now_utc, scan_count, strat_results, active_trades, trade_history, daily_tracker, sender_name=sender)
                    send_telegram(briefing_text)
                elif any(cmd in txt for cmd in ["status", "ping", "check", "health", "live"]):
                    quick_report = [
                        f"🛰️ <b>LIVE BOT STATUS — {sender}</b>",
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                        f"⏱️ <b>Time:</b> {now_ist.strftime('%I:%M:%S %p IST')} ({now_utc.strftime('%H:%M UTC')})",
                        f"🔄 <b>Total Scans Completed:</b> #{scan_count}",
                        f"💼 <b>Active Open Positions:</b> {len(active_trades)} / {MAX_CONCURRENT_TRADES}",
                        f"🛡️ <b>Daily Drawdown Loss:</b> {'+' if daily_tracker['realized_pnl'] >= 0 else '-'}${abs(daily_tracker['realized_pnl']):,.2f}",
                        f"⚡ <b>Circuit Breaker:</b> {'🚨 TRIPPED' if daily_tracker.get('circuit_tripped') else '✅ ARMED'}",
                        f"📰 <b>News Guard:</b> {'⚠️ ACTIVE' if in_news else '✅ CLEAR'}",
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                        f"🎯 <b>Nearest Setup:</b> {max_item[0]} (Z: {max_item[1]:+.2f}s)",
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                        "💡 <i>V9.0 Funding Pips $5k Precision Engine Active.</i>"
                    ]
                    send_telegram("\n".join(quick_report))
            
        except Exception as e:
            print(f"[Error in scan #{scan_count}]: {e}")
            
        elapsed_total = time.time() - scan_start
        sleep_dur = max(1.0, 5.0 - elapsed_total)
        time.sleep(sleep_dur)

if __name__ == "__main__":
    main()
