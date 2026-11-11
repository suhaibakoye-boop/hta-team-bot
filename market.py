
import os
import aiohttp

BINANCE_URL = "https://api.binance.com/api/v3/klines"
TWELVE_URL = "https://api.twelvedata.com/time_series"

ASSETS = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana",
    "BNBUSDT": "BNB",
    "XRPUSDT": "XRP",
    "EUR/USD": "EUR/USD",
    "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
}

TIMEFRAMES = [
    "1m", "5m", "15m", "30m", "45m",
    "1h", "2h", "4h", "8h", "1d", "1w", "1M"
]

TWELVE_INTERVALS = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "45m": "45min",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "8h": "8h",
    "1d": "1day",
    "1w": "1week",
    "1M": "1month",
}

CRYPTO_INTERVALS = {
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h",
    "12h", "1d", "3d", "1w", "1M"
}


async def get_crypto_candles(symbol, interval, limit=100):
    if symbol not in ASSETS:
        raise ValueError("Unsupported symbol")

    if interval not in TIMEFRAMES:
        raise ValueError("Unsupported timeframe")

    timeout = aiohttp.ClientTimeout(total=25)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        if symbol.endswith("USDT"):
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }

            async with session.get(
                BINANCE_URL, params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()

            return [
                {
                    "time": candle[0],
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                }
                for candle in data
            ]

        api_key = os.environ.get("TWELVEDATA_API_KEY")
        if not api_key:
            raise RuntimeError("TWELVEDATA_API_KEY is missing")

        if interval not in TWELVE_INTERVALS:
            raise ValueError(
                f"{interval} is not supported by Twelve Data"
            )

        params = {
            "symbol": symbol,
            "interval": TWELVE_INTERVALS[interval],
            "outputsize": limit,
            "apikey": api_key,
            "timezone": "UTC",
        }

        async with session.get(
            TWELVE_URL, params=params
        ) as response:
            response.raise_for_status()
            data = await response.json()

    if "values" not in data:
        raise RuntimeError(
            data.get("message", "Market data unavailable")
        )

    return [
        {
            "time": candle["datetime"],
            "open": float(candle["open"]),
            "high": float(candle["high"]),
            "low": float(candle["low"]),
            "close": float(candle["close"]),
        }
        for candle in reversed(data["values"])
    ]
