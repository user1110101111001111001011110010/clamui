"""Curated source presets, verified against operator-owned pages.

This is a catalog, not a health check. Keep the user's current source selection.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Mirror:
    key: str
    name: str
    url: str
    mode: str
    source: str
    note: str


MIRRORS = (
    Mirror("microsoft", "Microsoft", "https://packages.microsoft.com/clamav", "private_only",
           "https://packages.microsoft.com/clamav/",
           "На сервере Microsoft опубликованы main.cvd, daily.cvd и bytecode.cvd."),
    Mirror("truenetwork", "TrueNetwork · Россия", "https://mirror.truenetwork.ru/clamav", "private_only",
           "https://mirror.truenetwork.ru/clamav/",
           "Зеркало TrueNetwork. Тот же оператор, что у clamav-mirror.ru."),
    Mirror("clamav_mirror", "clamav-mirror.ru · Россия", "https://clamav-mirror.ru", "private_only",
           "https://clamav-mirror.ru/",
           "Тот же оператор, что TrueNetwork; не независимый резервный сервер."),
    Mirror("official", "ClamAV · официальный CDN", "https://database.clamav.net", "official",
           "https://docs.clamav.net/manual/Usage/Configuration.html",
           "Включает официальный режим и проверку версии через DNS ClamAV."),
)
VERIFIED_DATE = "2026-10-05"
