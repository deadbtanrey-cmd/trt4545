import requests

BYBIT_INSTRUMENTS = "https://api.bybit.com/v5/market/instruments-info"


def load_all_symbols():
    """Загружаем все USDT линейные перпетуалы со статусом Trading."""
    symbols = []
    cursor = None

    while True:
        params = {
            "category": "linear",
            "status": "Trading",
        }
        if cursor:
            params["cursor"] = cursor

        res = requests.get(BYBIT_INSTRUMENTS, params=params, timeout=10).json()
        data = res.get("result", {}).get("list", []) or []

        for item in data:
            symbol = item.get("symbol")
            ctype = item.get("contractType")
            if ctype == "LinearPerpetual" and symbol and symbol.endswith("USDT"):
                symbols.append(symbol)

        cursor = res.get("result", {}).get("nextPageCursor")
        if not cursor:
            break

    # убираем дубли
    return sorted(set(symbols))
