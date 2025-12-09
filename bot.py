import time
import requests
import telegram

from config import TELEGRAM_BOT_TOKEN, CHAT_ID, INTERVAL_MINUTES
from symbol_manager import load_all_symbols
from bybit_ws import BybitWS
from oi_logic import register_oi, check_signal


bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
sent_cache = {}  # symbol -> last_ts (подстраховка от спама)


def send(text: str):
    if not TELEGRAM_BOT_TOKEN or CHAT_ID == 0:
        print("❗ ВНИМАНИЕ: TELEGRAM_BOT_TOKEN или CHAT_ID не заданы в config.py")
        print("   Сообщение не отправлено, но вот оно:")
        print(text)
        return
    bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")


def price(sym: str) -> str:
    url = "https://api.bybit.com/v5/market/tickers"
    res = requests.get(url, params={"category": "linear", "symbol": sym}, timeout=10).json()
    try:
        return res["result"]["list"][0]["lastPrice"]
    except Exception:
        return "N/A"


def on_update(symbol: str, oi: float):
    # записываем OI-снапшот для текущей минуты
    register_oi(symbol, oi)

    # проверяем, есть ли сигнал по закрытию интервала
    result = check_signal(symbol)
    if not result:
        return

    pct, delta, oi_past, oi_now, t_past, t_now = result

    now_ts = time.time()
    # дополнительный антиспам: не чаще 1 раза в 60 секунд по одной монете
    last = sent_cache.get(symbol, 0)
    if now_ts - last < 60:
        return
    sent_cache[symbol] = now_ts

    pr = price(symbol)
    # считаем примерный прирост в USDT
    try:
        pr_f = float(pr)
        delta_usdt = delta * pr_f
        delta_usdt_str = f"{delta_usdt:,.0f} USDT"
    except Exception:
        delta_usdt = None
        delta_usdt_str = "N/A"

    t_str = time.strftime('%H:%M:%S', time.localtime(t_now))

    # правильная ссылка на CoinGlass (Bybit_)
    link = f"https://www.coinglass.com/tv/Bybit_{symbol}"

    # лог для дебага в консоль
    print(
        f"[SIGNAL] {symbol} | "
        f"OI_past={oi_past:.0f} OI_now={oi_now:.0f} | "
        f"ΔOI={delta:.0f} (~{delta_usdt_str}) | "
        f"{pct}% за {INTERVAL_MINUTES}m | "
        f"t_past={time.strftime('%H:%M:%S', time.localtime(t_past))} "
        f"t_now={t_str}"
    )

    msg = (
        f"🔥 <b>{symbol}</b>\n"
        f"📈 +{pct}% OI за {INTERVAL_MINUTES}m\n"
        f"📦 ΔOI: {delta:,.0f} контрактов (~{delta_usdt_str})\n"
        f"💲 Цена: {pr}\n"
        f"⏰ Время: {t_str}\n"
        f"🔗 <a href=\"{link}\">Открыть график на CoinGlass</a>"
    )

    send(msg)


def main():
    print("🚀 Загружаю список монет...")
    symbols = load_all_symbols()
    print(f"📊 Монет найдено: {len(symbols)}")

    print("🔌 Подключаю WebSocket...")
    ws = BybitWS(symbols, on_update)
    ws.connect()

    print(f"🟢 Бот запущен. OI мониторинг активен (по закрытию {INTERVAL_MINUTES}-минутных интервалов).")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
