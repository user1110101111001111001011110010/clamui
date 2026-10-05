# Известные источники баз ClamAV

Каталог источников встроен в `clamui/mirrors.py`. Адреса добавлены для удобного
выбора при ручном запуске обновления. Он не проверяет доступность сети в реальном
времени. Дата сверки операторских страниц: 2026-10-05.

| Название | Адрес в каталоге | Режим ClamUI | Основание |
|---|---|---|---|
| Microsoft | `https://packages.microsoft.com/clamav` | `PrivateMirror` | [Каталог Microsoft](https://packages.microsoft.com/clamav/) перечисляет `main.cvd`, `daily.cvd`, `bytecode.cvd` и FILE_MANIFEST |
| TrueNetwork, Россия | `https://mirror.truenetwork.ru/clamav` | `PrivateMirror` | [Страница зеркала](https://mirror.truenetwork.ru/clamav/) подтверждает ClamAV mirror и TrueNetwork как оператора |
| clamav-mirror.ru, Россия | `https://clamav-mirror.ru` | `PrivateMirror` | [Страница оператора](https://clamav-mirror.ru/) публикует конфигурацию PrivateMirror и сообщает о ежечасном обновлении |
| Официальный CDN ClamAV | `database.clamav.net` | Официальный режим | Рекомендуемый `DatabaseMirror` по [документации ClamAV](https://docs.clamav.net/manual/Usage/Configuration.html) |

`mirror.truenetwork.ru` и `clamav-mirror.ru` обслуживаются TrueNetwork. Их можно
использовать как разные адреса доступа, но это не два независимых оператора для
резервирования. Microsoft — отдельный оператор. URL окончания `/` нормализуется
ClamAV при разборе PrivateMirror; сам каталог хранит адреса без завершающей косой.

Официальный CDN выбирает распределённую инфраструктуру ClamAV; он не считается
сторонним частным зеркалом. Выбор официального CDN включает официальный режим и
штатную DNS-проверку. Режим `private_only` не имеет скрытого возврата на него.

Freshclam загружает подписанные базы, а приложение сохраняет `TestDatabases yes`.
Наличие публичного каталога не гарантирует, что сервер доступен из конкретной сети,
актуален или корректно обслуживает будущие запросы. При ошибке freshclam сообщает
об источнике и сохраняет ранее активные базы. Кнопка «Проверить зеркало» пока не
проводит отдельный сетевой тест; фактическая проверка доступности происходит при
нажатии «Обновить базы».
