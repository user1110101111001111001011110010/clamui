"""Small built-in translations for the terminal interface."""
from __future__ import annotations

import re


EN = {
    "Главное меню": "Main menu", "Проверка": "Scan", "Обновить базы": "Update databases",
    "История": "History", "Базы и зеркала": "Databases and mirrors", "Настройки": "Settings",
    "Справка": "Help", "Выход": "Exit", "Выйти из ClamUI": "Exit ClamUI",
    "Выбрать файл или папку…": "Select a file or folder…", "Открыть подробный журнал": "Open full log",
    "Назад": "Back", "Продолжить сканирование": "Resume scan", "Подтвердить остановку": "Confirm stop",
    "Известные зеркала → выбрать из списка": "Known mirrors → choose from list",
    "не задано": "not set", "Посмотреть фрагмент freshclam.conf": "Preview freshclam.conf snippet",
    "Сохранить источники": "Save sources", "Сохранить и обновить базы": "Save and update databases",
    "Назад без сохранения": "Back without saving", "Включить официальный режим": "Use official sources",
    "Назад к списку": "Back to list", "Сделать основным зеркалом": "Set as primary mirror",
    "Сделать резервным зеркалом": "Set as backup mirror", "[Выбрать эту папку]": "[Select this folder]",
    "[..] На уровень выше": "[..] Parent directory", "Отменить обновление": "Cancel update",
    "Начать обновление": "Start update", "Журнал обновления": "Update log", "Настроить зеркала": "Configure mirrors",
    "Вложенные папки: да": "Recursive: yes", "Вложенные папки: нет": "Recursive: no",
    "Вложенные папки по умолчанию: да": "Recursive by default: yes",
    "Вложенные папки по умолчанию: нет": "Recursive by default: no",
    "Цветной интерфейс: да": "Color interface: yes", "Цветной интерфейс: нет": "Color interface: no",
    "Остаться": "Stay", "Отменить текущую операцию и выйти": "Cancel the current operation and exit",
    "ClamUI: увеличьте терминал минимум до 70×20": "ClamUI: enlarge the terminal to at least 70×20",
    "Задание продолжается. Esc — выход.": "The job is still running. Esc — exit.",
    "Enter — остаться; ↓ Enter — отменить и выйти": "Enter — stay; ↓ Enter — cancel and exit",
    "Главное меню": "Main menu", "Предпросмотр конфигурации": "Configuration preview",
    "Результат проверки": "Scan result", "Текущий результат": "Live results",
    "Завершение работы": "Exit", "Известные зеркала": "Known mirrors", "Выбор зеркала": "Mirror selection",
    "Выбор файла или папки": "Select a file or folder", "Обновление баз": "Database update",
    "Подтверждение остановки": "Confirm scan stop", "Движок не установлен": "ClamAV is not installed",
    "Выберите действие и нажмите Enter.": "Choose an action and press Enter.",
    "Локальное сканирование • действия только вручную": "Local scanning • manual actions only",
    "ClamAV is an open-source antivirus toolkit for detecting malicious software.":
        "ClamAV is an open-source antivirus toolkit for detecting malicious software.",
    "It includes a command-line scanner and FreshClam database updater.":
        "It includes a command-line scanner and FreshClam database updater.",
    "Установка идёт… вывод пакетного менеджера обновляется ниже.": "Installing… package-manager output appears below.",
    "Для установки ClamAV потребуются права администратора.": "Administrator privileges are required to install ClamAV.",
    "PgUp/PgDn — прокрутка вывода установки.": "PgUp/PgDn — scroll installation output.",
    "Проверка ещё не запускалась": "No scan has been run yet",
    "Угроз не обнаружено": "No threats detected", "Находок пока нет": "No detections yet",
    "Список находок пуст": "No detections", "Источники обновления локальных баз ClamUI.":
        "Update sources for ClamUI's local databases.",
    "Системный freshclam не меняется. Новые адреса нужно сохранить.":
        "The system freshclam configuration is unchanged. Save new addresses to use them.",
    "Выберите сервер; затем назначьте основным или резервным.": "Choose a server, then set it as primary or backup.",
    "После выбора нажмите «Сохранить источники» или «Сохранить и обновить».":
        "After choosing, select Save sources or Save and update.",
    "Готово к обновлению": "Ready to update", "Обновление идёт…": "Update in progress…",
    "Открыта страница ClamUI на GitHub.": "Opened the ClamUI GitHub page.",
    "Браузер недоступен; ссылка GitHub скопирована в буфер обмена.":
        "Browser unavailable; GitHub URL copied to clipboard.",
    "Базы успешно обновлены": "Databases updated successfully",
    "Ошибка обновления — прежние базы сохранены": "Update failed — previous databases were preserved",
    "Обновление отменено": "Update cancelled", "Enter: открыть · Space: выбрать · F2: эта папка · .: скрытые":
        "Enter: open · Space: select · F2: this folder · .: hidden files",
    "Лимиты действуют для следующей проверки; Enter позволяет изменить МиБ.":
        "Limits apply to the next scan; press Enter to change MiB values.",
    "История пуста. Запустите первую проверку.": "History is empty. Run your first scan.",
    "Текущая операция будет остановлена; прежние базы сохранятся.":
        "The current operation will be stopped; existing databases will be preserved.",
    "Остановить текущую проверку? Её неполный результат сохранится в истории.":
        "Stop the current scan? Its partial result will be saved to history.",
    "↑↓ меню  PgUp/PgDn список угроз  Enter Открыть  Esc Назад  F1 Справка":
        "↑↓ menu  PgUp/PgDn detections  Enter open  Esc back  F1 help",
    "↑↓ Выбор/прокрутка  Enter Открыть  Esc Назад  F1 Справка":
        "↑↓ select/scroll  Enter open  Esc back  F1 help",
    "↑↓ меню  F5 Запуск  F6 Остановить  PgUp/PgDn список угроз  Esc назад":
        "↑↓ menu  F5 start  F6 stop  PgUp/PgDn detections  Esc back",
    "↑↓ выбор  Enter действие  PgUp/PgDn журнал установки  Esc выход":
        "↑↓ select  Enter action  PgUp/PgDn install log  Esc exit",
    "ClamUI · прототип 0.2": "ClamUI · prototype 0.2",
    "↑↓ или j/k — выбор; Enter — действие; Esc — назад.": "↑↓ or j/k — select; Enter — action; Esc — back.",
    "Tab — следующий пункт. PgUp/PgDn — прокрутка результата.": "Tab — next item. PgUp/PgDn — scroll results.",
    "На экране проверки F5 Запуск, F6 Остановить (с подтверждением).":
        "On the scan screen, F5 starts and F6 stops (after confirmation).",
    "Ctrl+C — запрос выхода с отменой активной проверки.": "Ctrl+C — request exit and cancel the active scan.",
    "Путь: выбор из списка или ручной ввод с дополнением по Tab.":
        "Path: select from the browser or type it with Tab completion.",
    "Меню истории хранит последние 100 записей (время UTC).": "History keeps the latest 100 entries (UTC).",
    "Подробный журнал хранит полный вывод ClamAV последней проверки.": "The full log stores all ClamAV output from the latest scan.",
    "Процент = обработанные файлы / первоначальный список файлов.": "Progress = processed files / initial file list.",
    "Это не процент времени или байтов. Ошибки показаны отдельно.": "This is not a percentage of time or bytes. Errors are shown separately.",
    "Новые файлы после подсчёта в задание не добавляются.": "Files added after inventory are not included in the scan.",
    "Symlink и другие файловые системы не обходятся.": "Symlinks and other filesystems are not traversed.",
    "Нулевой код ClamAV не доказывает проверку всех файлов.": "A zero ClamAV exit code does not prove every file was scanned.",
    "Зеркала: основной адрес, необязательный резервный адрес.": "Mirrors: a primary address and an optional backup.",
    "Сохранение задаёт источники кнопки «Обновить базы».": "Saved sources are used by Update databases.",
    "Предпросмотр — фрагмент, не готовый системный конфиг.": "The preview is a snippet, not a complete system configuration.",
    "Обновление идёт в пользовательский каталог без root.": "Updates run as the current user in a private data directory.",
    "Сканирование затем использует успешно обновлённые базы.": "Scans use the successfully updated databases.",
    "Карантин и расписание появятся позже.": "Quarantine and scheduling are planned for a later release.",
    "Используется при пользовательском обновлении.": "Used by ClamUI's per-user update operation.",
    "Системная служба и /etc не изменяются.": "System services and /etc are not modified.",
    "Ошибка настроек:": "Configuration error:", "Esc — вернуться и исправить": "Esc — go back and fix it",
    "Обновление ещё не запускалось в этой сессии": "No update has been run in this session",
    "Enter — сохранить число МиБ · диапазон показан выше · Esc — отмена":
        "Enter — save MiB value · range shown above · Esc — cancel",
    "Enter — принять · Tab — дополнить путь · Ctrl+U — очистить":
        "Enter — accept · Tab — complete path · Ctrl+U — clear",
    "Совпадений нет": "No matches", "Символьные ссылки не сканируются": "Symbolic links are not scanned",
    "Сначала выберите основное зеркало": "Choose a primary mirror first",
    "Это зеркало уже задано основным": "This is already the primary mirror",
    "Выбор ещё не сохранён. Сохраните источники перед обновлением.":
        "The selection is not saved. Save sources before updating.",
    "Источники сохранены для обновления баз ClamUI.": "Sources saved for ClamUI database updates.",
    "Параметры можно изменить после завершения проверки": "Settings can be changed after the scan completes",
    "Укажите путь": "Enter a path", "Отменяем обновление…": "Cancelling update…",
    "Проверка уже завершена": "The scan has already finished", "Запрошена остановка проверки…": "Scan stop requested…",
    "Все обязательные исполняемые файлы ClamAV уже доступны.": "All required ClamAV executables are available.",
    "Пакетный менеджер не распознан. Установите ClamAV вручную; поддерживаются: ":
        "No supported package manager was found. Install ClamAV manually; supported managers: ",
    "Запрос прав sudo прервали с клавиатуры.": "The sudo authorization request was interrupted.",
    "Установка выполняется; дождитесь её завершения.": "Installation is running; please wait for it to finish.",
    "Компоненты ClamAV установлены и доступны.": "ClamAV components are installed and available.",
    "Проверка уже выполняется": "A scan is already running", "Активной проверки нет": "No active scan",
    "Источники обновления пользовательских баз ClamUI": "ClamUI user database update sources",
    "Системный freshclam.conf не меняется": "The system freshclam.conf is unchanged",
    "Проверка": "Scan", "Начать проверку": "Start scan", "Остановить проверку…": "Stop scan…",
    "Нет файлов для расчёта процента": "No files available to calculate progress",
    "Проверка идёт — можно переходить между экранами": "Scan running — you can switch screens",
    "Базы обновляются — можно переходить между экранами": "Databases are updating — you can switch screens",
    "Язык интерфейса изменён на русский.": "Interface language changed to Russian.",
    "Язык интерфейса должен быть en или ru": "Interface language must be en or ru",
    "Обнаруженные файлы": "Detected files", "Действие с файлом": "File actions",
    "Карантин ClamUI": "ClamUI quarantine", "Файл в карантине": "Quarantined file",
    "Подтверждение карантина": "Confirm quarantine", "Подтверждение восстановления": "Confirm restore",
    "Переместить в карантин…": "Move to quarantine…", "Назад к находкам": "Back to detections",
    "Восстановить исходный файл…": "Restore original file…", "Назад к карантину": "Back to quarantine",
    "Подтвердить перемещение в карантин": "Confirm move to quarantine",
    "Подтвердить восстановление": "Confirm restore", "Отмена": "Cancel",
    "Удалить файл…": "Delete file…", "Игнорировать в следующих проверках…": "Ignore in future scans…",
    "Подтвердить удаление файла": "Confirm file deletion",
    "Подтвердить добавление в белый список": "Confirm adding to allowlist",
    "Убрать путь из белого списка": "Remove path from allowlist",
    "Белый список ClamUI": "ClamUI allowlist", "Подтверждение удаления": "Confirm deletion",
    "Подтверждение белого списка": "Confirm allowlist", "Убрать путь из белого списка": "Remove allowlisted path",
    "Файл будет удалён без возможности восстановления:": "The file will be permanently deleted:",
    "Этот точный путь будет пропускаться в следующих проверках:":
        "This exact path will be skipped in future scans:",
    "После удаления пути из белого списка файл будет проверяться снова:":
        "Removing this path from the allowlist will include it in future scans:",
    "Сначала выберите путь из белого списка": "Select an allowlisted path first",
    "Сначала выберите обнаруженный файл": "Select a detected file first",
    "Сначала выберите файл в карантине": "Select a quarantined file first",
    "Неизвестный язык интерфейса": "Unknown interface language",
    "Действия с находками доступны вручную: карантин, удаление или белый список.":
        "Detection actions are manual: quarantine, delete, or allowlist.",
    "Карантин обратим; удаление требует подтверждения. Белый список хранит точный путь.":
        "Quarantine is reversible; deletion requires confirmation. The allowlist stores exact paths.",
    "Источники обновления локальных баз ClamUI.": "Update sources for ClamUI's local databases.",
    "Ошибка настроек:": "Settings error:",
    "Определяем версию ClamAV…": "Detecting the ClamAV version…",
    "Пакетный менеджер не распознан — установка вручную": "No supported package manager — install manually",
    "Перемещение начнётся только после отдельного подтверждения.":
        "The file will be moved only after a separate confirmation.",
    "Если путь занят, операция завершится без перезаписи.":
        "If the destination exists, the operation stops without overwriting it.",
    "Восстановление не перезапишет существующий файл.": "Restore will not overwrite an existing file.",
    "Восстановить файл по исходному пути?": "Restore the file to its original path?",
    "Файл будет удалён из исходного места и сохранён в карантине ClamUI:":
        "The file will be removed from its original location and stored in ClamUI quarantine:",
    "Некорректная запись карантина": "Invalid quarantine record",
    "Исходный каталог отсутствует; файл оставлен в карантине":
        "The original directory is missing; the file remains in quarantine",
    "Нет файлов для проверки": "No files to scan",
    "Проверка идёт": "Scan in progress", "Угроз не обнаружено в проверенных файлах": "No threats found in scanned files",
    "Обнаружены угрозы или предупреждения ClamAV": "ClamAV detections or warnings found",
    "Ошибка: проверка неполная": "Error: scan was incomplete",
    "Проверка отменена": "Scan cancelled", "Проверка прервана": "Scan interrupted",
    "Ещё Tab — варианты: ": "Press Tab again for options: ",
    "Настройки: ": "Settings: ", "История: ": "History: ",
    "Символьные ссылки не сканируются; выберите исходный файл": "Symbolic links are not scanned; select the original file",
}


def english(text: str) -> str:
    """Translate a displayed Russian UI string; preserve dynamic user data."""
    if text in EN:
        return EN[text]
    if text.startswith("› ") or text.startswith("  "):
        prefix, body = text[:2], text[2:]
        return prefix + english(body)
    if text.startswith("/ "):
        return "/ " + EN.get(text[2:], text[2:])
    for label in ("Основное", "Резервное"):
        if text == f"{label}: не задано":
            return ("Primary" if label == "Основное" else "Backup") + ": not set"
    patterns = (
        (r"^Источники: официальные серверы$", "Sources: official servers"),
        (r"^Источники: только свои зеркала$", "Sources: private mirrors only"),
        (r"^Режим: только свои зеркала$", "Mode: private mirrors only"),
        (r"^Режим: официальные серверы$", "Mode: official servers"),
        (r"^Цветной интерфейс: да$", "Color interface: on"),
        (r"^Цветной интерфейс: нет$", "Color interface: off"),
        (r"^Вложенные папки: да$", "Recursive: yes"),
        (r"^Вложенные папки: нет$", "Recursive: no"),
        (r"^Вложенные папки по умолчанию: да$", "Recursive by default: yes"),
        (r"^Вложенные папки по умолчанию: нет$", "Recursive by default: no"),
        (r"^Путь: (.*) \[Tab\]$", r"Path: \1 [Tab]"),
        (r"^Откройте ссылку GitHub: (.*)$", r"Open this GitHub URL: \1"),
        (r"^Карантин · (\d+)$", r"Quarantine · \1"),
        (r"^Белый список · (\d+)$", r"Allowlist · \1"),
        (r"^Действия с находками · (\d+)$", r"Detection actions · \1"),
        (r"^Перемещено в карантин: (.*)$", r"Moved to quarantine: \1"),
        (r"^Файл перемещён в карантин: (.*)$", r"File moved to quarantine: \1"),
        (r"^Файл восстановлен: (.*)$", r"File restored: \1"),
        (r"^Файл удалён: (.*)$", r"File deleted: \1"),
        (r"^Путь добавлен в белый список: (.*)$", r"Path added to allowlist: \1"),
        (r"^Путь удалён из белого списка: (.*)$", r"Path removed from allowlist: \1"),
        (r"^Файл изменился во время операции; повторите её$", "The file changed during the operation; retry"),
        (r"^Файл изменился после проверки; исходник оставлен на месте$", "The file changed since the scan; the original was left in place"),
        (r"^Выбранный путь больше не является обычным файлом$", "The selected path is no longer a regular file"),
        (r"^В карантин можно переместить только обычный файл$", "Only regular files can be moved to quarantine"),
        (r"^Контрольная сумма файла не совпала$", "The file checksum did not match"),
        (r"^Файл больше недоступен: (.*)$", r"File is no longer accessible: \1"),
        (r"^Путь уже занят; файл оставлен в карантине: (.*)$", r"Destination already exists; file remains quarantined: \1"),
        (r"^Проверка идёт · (\d+) с$", r"Scan in progress · \1 s"),
        (r"^Угроз не обнаружено в проверенных файлах · (\d+) с$", r"No threats found in scanned files · \1 s"),
        (r"^Обнаружены угрозы или предупреждения ClamAV · (\d+) с$", r"ClamAV detections or warnings found · \1 s"),
        (r"^Ошибка: проверка неполная · (\d+) с$", r"Error: scan was incomplete · \1 s"),
        (r"^Проверка отменена · (\d+) с$", r"Scan cancelled · \1 s"),
        (r"^Проверка прервана · (\d+) с$", r"Scan interrupted · \1 s"),
        (r"^Базы ClamUI · (.*)$", r"ClamUI databases · \1"),
        (r"^Системные базы · (.*)$", r"System databases · \1"),
        (r"^Лимиты clamscan: файл (\d+) МиБ; проверка (\d+) МиБ\.$", r"clamscan limits: file \1 MiB; scan \2 MiB."),
        (r"^Ещё Tab — варианты: (.*)$", r"Press Tab again for options: \1"),
        (r"^Невозможно обновить настройки: (.*)$", r"Could not update settings: \1"),
        (r"^Неизвестный режим (.*)$", r"Unknown mode: \1"),
        (r"^Максимальный размер файла должен быть от (.*)$", r"Maximum file size must be \1"),
        (r"^Максимальный объём сканирования должен быть от (.*)$", r"Maximum scan size must be \1"),
        (r"^Нужен адрес http\(s\)://сервер\[/путь\], без пароля и параметров$", "Enter an http(s)://host[/path] address without credentials or query parameters"),
        (r"^В адресе зеркала недопустимы пробелы и управляющие символы$", "Mirror addresses cannot contain spaces or control characters"),
        (r"^В режиме своих зеркал адреса clamav\.net запрещены$", "clamav.net addresses are not allowed in private mirror mode"),
        (r"^Основное и резервное зеркала должны отличаться$", "Primary and backup mirrors must be different"),
        (r"^Для своих зеркал укажите основной адрес$", "Set a primary address for private mirror mode"),
        (r"^Проверка ещё не запускалась(?: · (.*))?$", r"No scan has been run yet\1"),
        (r"^Нет файлов для расчёта процента$", "No files available to calculate progress"),
        (r"^Основное: (.*)$", r"Primary: \1"),
        (r"^Резервное: (.*)$", r"Backup: \1"),
        (r"^Источники: (.*)$", r"Sources: \1"),
        (r"^Каталог: (.*)$", r"Directory: \1"),
        (r"^Код ClamAV: (.*)$", r"ClamAV exit code: \1"),
        (r"^Максимальный размер файла: (\d+) МиБ$", r"Maximum file size: \1 MiB"),
        (r"^Максимальный объём сканирования: (\d+) МиБ$", r"Maximum scan size: \1 MiB"),
        (r"^Язык интерфейса: English$", "Interface language: English"),
        (r"^Язык интерфейса: Русский$", "Interface language: Russian"),
        (r"^Не найдены обязательные исполняемые файлы: (.*)$", r"Required executables not found: \1"),
        (r"^После попытки установки всё ещё не найдены: (.*)$", r"Still missing after installation: \1"),
        (r"^Процесс установки завершился с кодом (.*)\.$", r"The installer exited with code \1."),
        (r"^Не удалось получить права sudo \(код (.*)\)\.$", r"Could not obtain sudo access (exit code \1)."),
        (r"^Не удалось получить права для установки: (.*)$", r"Could not obtain installation privileges: \1"),
        (r"^Не удалось запустить установщик: (.*)$", r"Could not start the installer: \1"),
        (r"^Автоустановка требует sudo; запустите эту команду от root: (.*)$", r"Automatic installation needs sudo; run as root: \1"),
        (r"^Установленные исполняемые файлы доступны, но (.*)$", r"Executables are available, but \1"),
        (r"^Исполняемые файлы доступны, но (.*)$", r"Executables are available, but \1"),
        (r"^Максимальный размер файла \(МиБ, 1–2048\)$", "Maximum file size (MiB, 1–2048)"),
        (r"^Максимальный объём сканирования \(МиБ, 1–4096\)$", "Maximum scan size (MiB, 1–4096)"),
        (r"^Адрес зеркала: https://сервер/путь$", "Mirror URL: https://host/path"),
        (r"^Путь к файлу или папке$", "File or folder path"),
        (r"^Строки (\d+)–(\d+) / (\d+)$", r"Lines \1–\2 / \3"),
        (r"^Каталог источников от (.*); доступность не проверена\.$", r"Source catalog dated \1; availability has not been checked."),
        (r"^Проверка завершена · (\d+) с$", r"Scan complete · \1 s"),
        (r"^Составление списка… найдено файлов: (\d+)$", r"Building file list… found \1 files"),
        (r"^Загрузка баз… 0% · 0/(\d+) файлов$", r"Loading databases… 0% · 0/\1 files"),
        (r"^(\d+)% · обработано (\d+)/(\d+) файлов · находок (\d+)$", r"\1% · processed \2/\3 files · detections \4"),
        (r"^Текущая проверка · ошибок: (\d+) · пропусков: (\d+)$", r"Scan in progress · errors: \1 · skipped: \2"),
        (r"^Ошибок: (\d+) · Пропусков: (\d+)$", r"Errors: \1 · Skipped: \2"),
        (r"^Обнаруженные угрозы · (\d+)$", r"Detections · \1"),
    )
    for pattern, replacement in patterns:
        match = re.match(pattern, text)
        if match:
            return re.sub(pattern, replacement, text)
    return text
