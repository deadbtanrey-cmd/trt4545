import time
from config import OI_THRESHOLD_PERCENT, INTERVAL_MINUTES

# minute_snapshots[symbol][minute_index] = oi
minute_snapshots = {}
# чтобы не слать по одной и той же минуте по 100 раз
last_signal_minute = {}


def _current_minute_index(ts=None):
    if ts is None:
        ts = time.time()
    return int(ts // 60)


def register_oi(symbol, oi):
    """Запоминаем последний OI для текущей минуты."""
    now = time.time()
    minute_idx = _current_minute_index(now)

    snaps = minute_snapshots.setdefault(symbol, {})
    snaps[minute_idx] = oi

    # чистим старые минуты (оставим последний час)
    for m in list(snaps.keys()):
        if minute_idx - m > 60:
            del snaps[m]


def check_signal(symbol):
    """Проверяем: есть ли полный интервал INTERVAL_MINUTES между двумя минутами.

    Логика:
    - берём OI на minute_now и minute_past = minute_now - INTERVAL_MINUTES
    - считаем % изменения.
    - сигнал только один раз на minute_now.
    """
    snaps = minute_snapshots.get(symbol)
    if not snaps:
        return None

    minute_now = _current_minute_index()
    minute_past = minute_now - INTERVAL_MINUTES

    if minute_past not in snaps or minute_now not in snaps:
        return None

    # уже слали сигнал за эту минуту?
    if last_signal_minute.get(symbol) == minute_now:
        return None

    oi_past = snaps[minute_past]
    oi_now = snaps[minute_now]

    if oi_past <= 0:
        return None

    change = (oi_now - oi_past) / oi_past * 100.0
    delta = oi_now - oi_past

    if change >= OI_THRESHOLD_PERCENT:
        last_signal_minute[symbol] = minute_now
        t_past = minute_past * 60
        t_now = minute_now * 60
        return round(change, 2), delta, oi_past, oi_now, t_past, t_now

    return None
