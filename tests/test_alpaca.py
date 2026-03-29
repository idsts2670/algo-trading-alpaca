from unittest.mock import MagicMock
from datetime import datetime, timezone


# Patch _get_clients before each test to avoid real SSM/API calls
def _make_mock_clients(mocker):
    mock_trading = MagicMock()
    mock_data = MagicMock()
    mocker.patch("alpaca_broker._get_clients", return_value=(mock_trading, mock_data))
    return mock_trading, mock_data


def test_get_price_history_returns_correct_shape(mocker):
    mock_trading, mock_data = _make_mock_clients(mocker)
    ts = datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc)
    bar = MagicMock(close=150.0, timestamp=ts)
    mock_data.get_stock_bars.return_value = {"AAPL": [bar]}

    import alpaca_broker
    result = alpaca_broker.get_price_history("AAPL", bars=500)

    assert len(result) == 1
    assert result[0]["close"] == 150.0
    assert isinstance(result[0]["datetime"], float)


def test_place_order_buy(mocker):
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    mock_trading, _ = _make_mock_clients(mocker)
    # Force regular hours so the function uses MarketOrderRequest
    mocker.patch("alpaca_broker._is_extended_hours", return_value=False)
    mock_order = MagicMock()
    mock_trading.submit_order.return_value = mock_order

    import alpaca_broker
    result = alpaca_broker.place_order(None, "AAPL", 10, "BUY")

    mock_trading.submit_order.assert_called_once()
    call_arg = mock_trading.submit_order.call_args[0][0]
    assert isinstance(call_arg, MarketOrderRequest)
    assert call_arg.symbol == "AAPL"
    assert call_arg.qty == 10
    assert call_arg.side == OrderSide.BUY
    assert call_arg.time_in_force == TimeInForce.DAY
    assert result is mock_order


def test_place_order_sell(mocker):
    from alpaca.trading.enums import OrderSide

    mock_trading, _ = _make_mock_clients(mocker)
    mocker.patch("alpaca_broker._is_extended_hours", return_value=False)
    mock_trading.submit_order.return_value = MagicMock()

    import alpaca_broker
    alpaca_broker.place_order(None, "MSFT", 5, "SELL")

    call_arg = mock_trading.submit_order.call_args[0][0]
    assert call_arg.side == OrderSide.SELL


def test_place_trailing_stop_order(mocker):
    from alpaca.trading.requests import TrailingStopOrderRequest
    from alpaca.trading.enums import TimeInForce

    mock_trading, _ = _make_mock_clients(mocker)
    mocker.patch("alpaca_broker._is_extended_hours", return_value=False)
    mock_trading.submit_order.return_value = MagicMock()

    import alpaca_broker
    alpaca_broker.place_trailing_stop_order(None, "NVDA", 3, 4.75, "SELL")

    call_arg = mock_trading.submit_order.call_args[0][0]
    assert isinstance(call_arg, TrailingStopOrderRequest)
    assert call_arg.trail_percent == 4.75
    assert call_arg.time_in_force == TimeInForce.GTC


def test_get_clock_returns_clock(mocker):
    mock_trading, _ = _make_mock_clients(mocker)
    mock_clock = MagicMock(is_open=True)
    mock_trading.get_clock.return_value = mock_clock

    import alpaca_broker
    result = alpaca_broker.get_clock()

    assert result is mock_clock
    assert result.is_open is True
