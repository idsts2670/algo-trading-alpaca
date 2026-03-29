import logging
import os
import time
import traceback
from datetime import datetime
from decimal import Decimal

import boto3
import pandas as pd

from alpaca_broker import (
    NY_TZ, _is_extended_hours,
    get_clock, get_price_history, get_orders, cancel_order,
    get_current_quotes, place_order, place_trailing_stop_order,
    get_account, get_all_positions,
)

logger = logging.getLogger()
logger.setLevel("INFO")

MAGNIFICENT_7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 3, 16, 9
MACD_MIN_BARS = MACD_SLOW + MACD_SIGNAL  # 25
INTRADAY_BARS = 500
TRAILING_STOP_PERCENTAGE = 4.75

def _get_table():
    return boto3.resource("dynamodb").Table(
        os.environ.get("PORTFOLIO_TABLE_NAME", "algotrading-portfolios")
    )


# --- DynamoDB helpers ---

def _store_portfolio(portfolio: dict) -> None:
    _get_table().put_item(Item=portfolio)


def _get_portfolio(account_hash: str) -> dict:
    response = _get_table().get_item(Key={"accountHash": account_hash})
    return response.get("Item", {"accountHash": account_hash, "cash": Decimal(0), "positions": {}})


# --- MACD strategy ---

def calculate_macd_signal(symbol: str, price_data: list[dict]) -> float:
    if len(price_data) < MACD_MIN_BARS:
        logger.warning(f"{symbol}: only {len(price_data)} bars (need {MACD_MIN_BARS}), skipping")
        return 0.0
    closes = pd.Series([d["close"] for d in price_data])
    ema_fast = closes.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = closes.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    score = float(macd_line.iloc[-1] - signal_line.iloc[-1])
    logger.info(f"{symbol} MACD signal score: {score:.6f}")
    return score


def build_target_portfolio() -> list[str]:
    signals = {}
    for symbol in MAGNIFICENT_7:
        price_data = get_price_history(symbol, bars=INTRADAY_BARS)
        signals[symbol] = calculate_macd_signal(symbol, price_data)
    selected = [s for s, score in signals.items() if score > 0]
    if not selected:
        logger.info("All MACD signals negative — holding cash.")
        return []
    logger.info(f"Selected symbols with positive MACD: {selected}")
    return selected


# --- Portfolio execution helpers ---

def _get_ask_price(current_quotes: dict, symbol: str) -> Decimal | None:
    if symbol not in current_quotes:
        logger.warning(f"{symbol} NOT IN FETCHED QUOTES")
        return None
    return Decimal(str(current_quotes[symbol]["askPrice"]))


def _portfolio_value(positions: dict, cash: Decimal) -> Decimal:
    if not positions:
        return cash
    quotes = get_current_quotes(list(positions.keys()))
    total = cash
    for symbol, qty in positions.items():
        price = _get_ask_price(quotes, symbol)
        if price:
            total += price * Decimal(str(qty))
    return total


def _desired_positions(stocks: list[str], amount: Decimal) -> dict:
    if not stocks:
        return {}
    quotes = get_current_quotes(stocks)
    per_stock = amount / Decimal(len(stocks))
    result = {}
    for symbol in stocks:
        price = _get_ask_price(quotes, symbol)
        if price and price > 0:
            qty = int(per_stock // price)
            if qty > 0:
                result[symbol] = qty
    logger.info(f"Desired positions: {result}")
    return result


def _position_changes(current: dict, desired: dict) -> tuple[dict, dict]:
    sell, buy = {}, {}
    for symbol in set(current) | set(desired):
        cur_qty = Decimal(str(current.get(symbol, 0)))
        des_qty = Decimal(str(desired.get(symbol, 0)))
        diff = des_qty - cur_qty
        if diff > 0:
            buy[symbol] = int(diff)
        elif diff < 0:
            sell[symbol] = int(-diff)
    return sell, buy


# --- Main run logic ---

def run() -> None:
    logger.info("Starting bot")
    desired_stocks = build_target_portfolio()
    logger.info(f"Desired stocks: {desired_stocks}")

    account = get_account()
    account_hash = str(account.id)
    buying_power = Decimal(str(account.buying_power))

    positions_raw = get_all_positions()
    current_positions = {p.symbol: int(float(p.qty)) for p in positions_raw}

    portfolio = _get_portfolio(account_hash)
    portfolio["cash"] = buying_power
    portfolio["positions"] = current_positions

    portfolio_value = _portfolio_value(current_positions, buying_power)
    logger.info(f"Account {account_hash}: portfolio_value={portfolio_value}")

    # Cancel open orders before rebalancing
    for order in get_orders():
        cancel_order(None, str(order.id))
        logger.info(f"Cancelled order {order.id}")

    desired = _desired_positions(desired_stocks, portfolio_value)
    sell_pos, buy_pos = _position_changes(current_positions, desired)

    logger.info(f"Selling: {sell_pos}")
    logger.info(f"Buying: {buy_pos}")

    for symbol, qty in sell_pos.items():
        place_order(None, symbol, qty, "SELL")

    if sell_pos:
        time.sleep(2)  # allow sell orders to settle before buying

    for symbol, qty in buy_pos.items():
        place_order(None, symbol, qty, "BUY")

    if buy_pos:
        time.sleep(2)

    # Refresh positions and store to DynamoDB
    positions_raw = get_all_positions()
    portfolio["positions"] = {p.symbol: int(float(p.qty)) for p in positions_raw}
    _store_portfolio(portfolio)

    # Place trailing stops on all held positions
    for symbol, qty in portfolio["positions"].items():
        if qty > 0:
            place_trailing_stop_order(None, symbol, qty, TRAILING_STOP_PERCENTAGE, "SELL")


def handler(event, context):
    clock = get_clock()
    now = datetime.now(NY_TZ)
    # Allow regular hours OR weekday extended/overnight sessions
    is_weekday = now.weekday() < 5
    in_extended = _is_extended_hours() and is_weekday
    if not clock.is_open and not in_extended:
        logger.info("Market is closed — skipping run.")
        return {"status": "skipped", "reason": "market_closed"}
    try:
        run()
        return {"statusCode": 200}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"statusCode": 500, "error": str(e), "trace": traceback.format_exc()}
