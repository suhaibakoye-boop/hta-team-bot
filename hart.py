
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from datetime import datetime, timezone


def create_chart(candles, asset_name, symbol, timeframe):
    if not candles:
        raise ValueError("No candle data available")

    fig, ax = plt.subplots(figsize=(7, 11), dpi=180)

    fig.patch.set_facecolor("#131722")
    ax.set_facecolor("#131722")

    width = 0.62

    for i, candle in enumerate(candles):
        open_price = candle["open"]
        close_price = candle["close"]
        high_price = candle["high"]
        low_price = candle["low"]

        color = "#26a69a" if close_price >= open_price else "#ef5350"

        ax.plot(
            [i, i],
            [low_price, high_price],
            color=color,
            linewidth=1.2
        )

        body_bottom = min(open_price, close_price)
        body_height = abs(close_price - open_price)

        if body_height == 0:
            body_height = max(abs(open_price) * 0.00001, 0.00000001)

        body = Rectangle(
            (i - width / 2, body_bottom),
            width,
            body_height,
            facecolor=color,
            edgecolor=color,
            linewidth=0.8
        )
        ax.add_patch(body)

    ax.set_title(
        f"{asset_name} ({symbol})  |  {timeframe}",
        color="white",
        fontsize=15,
        pad=18
    )

    ax.grid(
        True,
        color="#2a2e39",
        linewidth=0.5,
        alpha=0.7
    )

    ax.tick_params(colors="#d1d4dc", labelsize=8)

    for spine in ax.spines.values():
        spine.set_color("#363a45")

    ax.set_xlim(-1, len(candles))
    ax.margins(y=0.08)

    plt.tight_layout()

    filename = "chart.png"
    fig.savefig(
        filename,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight"
    )
    plt.close(fig)

    return filename
