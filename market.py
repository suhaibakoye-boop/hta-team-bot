
import aiohttp

BINANCE_URL = "https://api.binance.com/api/v3/klines"

ASSETS = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana",
    "BNBUSDT": "BNB",
    "XRPUSDT": "XRP",
}

TIMEFRAMES = [
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h",
    "12h", "1d", "3d", "1w", "1M"
]


async def get_crypto_candles(symbol, interval, limit=100):
    if symbol not in ASSETS:
        raise ValueError("Unsupported crypto symbol")

    if interval not in TIMEFRAMES:
        raise ValueError("Unsupported timeframe")

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(BINANCE_URL, params=params) as response:
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

