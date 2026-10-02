import os
import sys


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# digit converter (FA/AR -> EN)
_FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_TO_EN = str.maketrans(_FA_DIGITS + _AR_DIGITS, "0123456789" * 2)


def to_english_digits(s) -> str:
    if s is None:
        return ""
    return str(s).translate(_TO_EN)


# Jalali calendar (algorithm from jalaali-js)
_JALALI_BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181,
                  1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394,
                  2456, 3178]


def jalali_is_leap(jy: int) -> bool:
    if jy < _JALALI_BREAKS[0] or jy >= _JALALI_BREAKS[-1]:
        return False

    jp = _JALALI_BREAKS[0]
    jump = 0
    for jm in _JALALI_BREAKS[1:]:
        jump = jm - jp
        if jy < jm:
            break
        jp = jm

    n = jy - jp
    if jump - n < 6:
        n = n - jump + ((jump + 4) // 33) * 33
    leap = (((n + 1) % 33) - 1) % 4
    return leap == 0


def jalali_days_in_month(jy: int, jm: int) -> int:
    if 1 <= jm <= 6:
        return 31
    if 7 <= jm <= 11:
        return 30
    if jm == 12:
        return 30 if jalali_is_leap(jy) else 29
    return 0


def validate_jalali_date(y: int, m: int, d: int):
    if y < 1200 or y > 1600:
        return False, "سال معتبر نیست (مثلاً 1404)."

    if m < 1 or m > 12:
        return False, "ماه باید بین 1 تا 12 باشد."

    if d < 1:
        return False, "روز باید حداقل 1 باشد."

    max_day = jalali_days_in_month(y, m)
    if d > max_day:
        return False, f"برای ماه {m}، روز باید حداکثر {max_day} باشد."

    return True, ""
