import websocket
import json
import threading
import time


class BybitWS:
    def __init__(self, symbols, on_oi_update):
        self.symbols = symbols
        self.on_oi_update = on_oi_update
        self.ws = None
        self.last_msg_time = 0.0

    def connect(self):
        print("🔌 [WS] Подключаюсь к Bybit WebSocket...")
        self.ws = websocket.WebSocketApp(
            "wss://stream.bybit.com/v5/public/linear",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        t = threading.Thread(target=self.ws.run_forever, daemon=True)
        t.start()

        # отдельный поток-watchdog
        threading.Thread(target=self.watchdog, daemon=True).start()

    def on_open(self, ws):
        print("✅ [WS] Соединение установлено. Подписываюсь на тикеры...")
        # бьём список на чанки по 50 символов (лимит Bybit на одну подписку)
        CHUNK = 50
        subs = []
        for i in range(0, len(self.symbols), CHUNK):
            chunk = self.symbols[i:i+CHUNK]
            subs.append({
                "op": "subscribe",
                "args": [f"tickers.{s}" for s in chunk],
            })
        for sub in subs:
            ws.send(json.dumps(sub))
            time.sleep(0.05)

    def on_message(self, ws, msg):
        data = json.loads(msg)
        if "data" in data:
            d = data["data"]
            symbol = d.get("symbol")
            oi_raw = d.get("openInterest")
            if symbol is None or oi_raw is None:
                return
            try:
                oi = float(oi_raw)
            except Exception:
                return

            self.last_msg_time = time.time()
            self.on_oi_update(symbol, oi)

    def on_error(self, ws, error):
        print("❌ [WS] Ошибка:", error)

    def on_close(self, ws, a, b):
        print("⚠️ [WS] Соединение закрыто. Переподключаюсь через 2 сек...")
        time.sleep(2)
        self.connect()

    def watchdog(self):
        """Следим, чтобы WebSocket не зависал надолго без данных."""
        while True:
            now = time.time()
            if self.last_msg_time and (now - self.last_msg_time) > 20:
                print("⚠️ [WS] Нет данных > 20 секунд. Принудительное переподключение.")
                try:
                    self.ws.close()
                except Exception:
                    pass
                self.last_msg_time = 0.0
            time.sleep(5)
