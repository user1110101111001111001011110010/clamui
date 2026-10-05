"""A dependency-free curses adapter. Core logic never imports curses."""
from __future__ import annotations

import curses
from dataclasses import replace
from pathlib import Path
import os
import queue
import shutil
import subprocess
import threading
import sqlite3
import time
import unicodedata
import webbrowser

from .core import (Config, Scanner, STATUS, Store, engine_status,
                   missing_clamav_tools, safe_text)
from .i18n import english
from .paths import FileBrowser, complete_path
from .package_managers import PACKAGE_MANAGERS, detect_package_manager, manual_install_command
from .updates import Updater
from .mirrors import MIRRORS, VERIFIED_DATE
from .quarantine import Quarantine

PROJECT_URL = "https://github.com/user1110101111001111001011110010/clamui.git"


def clipped(text: str, width: int) -> str:
    result = ""
    size = 0
    for char in safe_text(text):
        step = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in "WF" else 1)
        if size + step > width:
            break
        result += char
        size += step
    return result


class TerminalUI:
    def __init__(self, screen, store: Store, config: Config):
        self.win = screen
        self.store, self.config = store, config
        self.draft = replace(config)
        self.mirror_choice = MIRRORS[0]
        self.scanner = Scanner(store)
        self.updater = Updater(store)
        self.quarantine = Quarantine(store)
        self.browser = FileBrowser()
        self.completions = None
        self.update_was_busy = False
        self.page = "engine_missing" if missing_clamav_tools() else "home"
        self.selected = 0
        self.scroll = 0
        self.scan_list_scroll = 0
        self.target = str(Path.home())
        self.notice = ""
        self.install_output = []
        self.installing = False
        self.install_follow = True
        self.engine = "Определяем версию ClamAV…"
        self.rows = []
        self.record = None
        self.selected_detection = None
        self.selected_detection_identity = None
        self.quarantine_entries = []
        self.selected_quarantine = None
        self.ignored_paths = []
        self.selected_ignored_path = None
        self.edit = None
        self.exit_requested = False
        self.previous = "home"
        self.has_colors = False

    def set_engine(self):
        try:
            database = self.store.active_database()
            self.engine = ("Базы ClamUI · " if database else "Системные базы · ") + engine_status(database)
        except (OSError, ValueError) as exc:
            self.engine = safe_text(exc)

    def open_project_link(self):
        """Open the project page, copying its URL when no browser can be launched."""
        try:
            opened = webbrowser.open(PROJECT_URL, new=2)
        except (OSError, webbrowser.Error):
            opened = False
        if opened:
            self.notice = ("Открыта страница ClamUI на GitHub."
                           if self.config.language == "ru" else "Opened the ClamUI GitHub page.")
            return
        clipboard_commands = (
            ("wl-copy", []),
            ("xclip", ["-selection", "clipboard"]),
            ("xsel", ["--clipboard", "--input"]),
        )
        for executable, args in clipboard_commands:
            path = shutil.which(executable)
            if not path:
                continue
            try:
                result = subprocess.run([path, *args], input=PROJECT_URL, text=True,
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        timeout=3, check=False)
            except (OSError, subprocess.SubprocessError):
                continue
            if result.returncode == 0:
                self.notice = ("Браузер недоступен; ссылка GitHub скопирована в буфер обмена."
                               if self.config.language == "ru"
                               else "Browser unavailable; GitHub URL copied to clipboard.")
                return
        self.notice = ("Откройте ссылку GitHub: " if self.config.language == "ru"
                       else "Open this GitHub URL: ") + PROJECT_URL

    def go(self, page):
        old_page = self.page
        self.page, self.selected, self.scroll, self.notice = page, 0, 0, ""
        if page == "history":
            self.rows = self.store.history()
        if page == "quarantine":
            self.quarantine_entries = self.quarantine.entries()
        if page == "ignore_list":
            self.ignored_paths = self.store.ignored_paths()
        if page == "mirrors" and old_page not in {"preview", "mirror_catalog", "mirror_choice"}:
            self.draft = replace(self.config)

    def menu(self):
        yes = lambda value: "да" if value else "нет"
        if self.page == "home":
            items = [("Проверка", "scan"), ("Обновить базы", "updates"), ("История", "history")]
            count = len(self.quarantine.entries())
            if count:
                items.append((f"Карантин · {count}", "quarantine"))
            ignored_count = len(self.store.ignored_paths())
            if ignored_count:
                items.append((f"Белый список · {ignored_count}", "ignore_list"))
            return items + [
                    ("Базы и зеркала", "mirrors"), ("Настройки", "settings"),
                    ("Справка", "help"), ("GitHub · clamui", "github"), ("Выход", "exit")]
        if self.page == "engine_missing":
            manager = detect_package_manager()
            label = ("Установить через " + manager.label + ": " + ", ".join(manager.packages)
                     if manager else "Пакетный менеджер не распознан — установка вручную")
            return [(label, "install_engine"),
                    ("Выйти из ClamUI", "exit")]
        if self.page == "scan":
            items = [("Выбрать файл или папку…", "browse"),
                    ("Путь: " + safe_text(self.target) + " [Tab]", "path"),
                    ("Вложенные папки: " + yes(self.config.recursive), "recursive"),
                    ("Остановить проверку…" if self.scanner.busy else "Начать проверку",
                     "cancel" if self.scanner.busy else "start"),
                    ]
            detections = self.scanner.finding_paths_snapshot()
            if detections and not self.scanner.busy:
                items.append((f"Действия с находками · {len(detections)}", "detections"))
            return items + [("Открыть подробный журнал", "live"), ("Назад", "home")]
        if self.page == "detections":
            return [(safe_text(path), f"detection:{index}")
                    for index, path in enumerate(self.scanner.finding_paths_snapshot())] + [("Назад", "scan")]
        if self.page == "detection_action":
            return [("Переместить в карантин…", "quarantine_confirm"),
                    ("Удалить файл…", "delete_confirm"),
                    ("Игнорировать в следующих проверках…", "ignore_confirm"),
                    ("Назад к находкам", "detections")]
        if self.page == "quarantine":
            return [(Path(entry.original).name + " · " + entry.original, f"quarantine:{index}")
                    for index, entry in enumerate(self.quarantine_entries)] + [("Назад", "home")]
        if self.page == "quarantine_item":
            return [("Восстановить исходный файл…", "restore_confirm"), ("Назад к карантину", "quarantine")]
        if self.page == "quarantine_confirm":
            return [("Подтвердить перемещение в карантин", "confirm_quarantine"), ("Отмена", "detection_action")]
        if self.page == "restore_confirm":
            return [("Подтвердить восстановление", "confirm_restore"), ("Отмена", "quarantine_item")]
        if self.page == "ignore_list":
            return [(safe_text(path), f"ignored:{index}")
                    for index, path in enumerate(self.ignored_paths)] + [("Назад", "home")]
        if self.page == "ignore_remove_confirm":
            return [("Убрать путь из белого списка", "confirm_unignore"), ("Отмена", "ignore_list")]
        if self.page == "delete_confirm":
            return [("Подтвердить удаление файла", "confirm_delete"), ("Отмена", "detection_action")]
        if self.page == "ignore_confirm":
            return [("Подтвердить добавление в белый список", "confirm_ignore"), ("Отмена", "detection_action")]
        if self.page == "scan_confirm":
            return [("Продолжить сканирование", "resume_scan"),
                    ("Подтвердить остановку", "confirm_scan_cancel")]
        if self.page == "mirrors":
            private = self.draft.mode == "private_only"
            return [("Режим: " + ("только свои зеркала" if private else "официальные серверы"), "mode"),
                    ("Известные зеркала → выбрать из списка", "mirror_catalog"),
                    ("Основное: " + (self.draft.primary or "не задано"), "primary"),
                    ("Резервное: " + (self.draft.backup or "не задано"), "backup"),
                    ("Посмотреть фрагмент freshclam.conf", "preview"),
                    ("Сохранить источники", "save_mirrors"), ("Сохранить и обновить базы", "save_update"),
                    ("Назад без сохранения", "home")]
        if self.page == "mirror_catalog":
            return [(mirror.name, "preset:" + str(i)) for i, mirror in enumerate(MIRRORS)] + [("Назад", "mirrors")]
        if self.page == "mirror_choice":
            if self.mirror_choice.mode == "official":
                return [("Включить официальный режим", "preset_official"), ("Назад к списку", "mirror_catalog")]
            return [("Сделать основным зеркалом", "preset_primary"),
                    ("Сделать резервным зеркалом", "preset_backup"), ("Назад к списку", "mirror_catalog")]
        if self.page == "browser":
            return [("[Выбрать эту папку]", "choose_dir"), ("[..] На уровень выше", "parent")] + [
                (("[DIR] " if kind == "dir" else "[LINK] " if kind == "link" else "      ") + safe_text(name), "entry:" + str(i))
                for i, (name, _, kind) in enumerate(self.browser.entries)]
        if self.page == "updates":
            return [("Отменить обновление" if self.updater.busy else "Начать обновление", "cancel_update" if self.updater.busy else "start_update"),
                    ("Журнал обновления", "update_log"), ("Настроить зеркала", "mirrors"), ("Назад", "home")]
        if self.page == "settings":
            return [("Вложенные папки по умолчанию: " + yes(self.config.recursive), "recursive"),
                    (f"Максимальный размер файла: {self.config.max_filesize_mib} МиБ", "max_filesize_mib"),
                    (f"Максимальный объём сканирования: {self.config.max_scansize_mib} МиБ", "max_scansize_mib"),
                    ("Язык интерфейса: " + ("English" if self.config.language == "en" else "Русский"), "language"),
                    ("Цветной интерфейс: " + yes(self.config.color), "color"), ("Назад", "home")]
        if self.page == "history":
            return [(f"{r['started'][:16].replace('T', ' ')} UTC | {STATUS.get(r['status'], r['status'])} | {safe_text(r['path'])}",
                     str(i)) for i, r in enumerate(self.rows)] + [("Назад", "home")]
        if self.page == "exit":
            return [("Остаться", "stay"), ("Отменить текущую операцию и выйти", "confirm_exit")]
        return []

    def write(self, y, x, text, style=0):
        text = str(text)
        if self.config.language == "en":
            text = english(text)
        height, width = self.win.getmaxyx()
        if y < 0 or y >= height or x >= width - 1:
            return
        try:
            self.win.addstr(y, x, clipped(str(text), width - x - 1), style)
        except curses.error:
            pass

    def render(self):
        self.win.erase()
        h, w = self.win.getmaxyx()
        if h < 20 or w < 70:
            self.write(0, 0, "ClamUI: увеличьте терминал минимум до 70×20")
            self.write(2, 0, "Задание продолжается. Esc — выход.")
            if self.page == "exit":
                self.write(3, 0, "Enter — остаться; ↓ Enter — отменить и выйти")
            self.win.refresh()
            return
        accent = curses.color_pair(1) if self.has_colors and self.config.color else curses.A_BOLD
        titles = {"home": "Главное меню", "scan": "Проверка", "history": "История",
                  "mirrors": "Базы и зеркала", "settings": "Настройки", "help": "Справка",
                  "preview": "Предпросмотр конфигурации", "detail": "Результат проверки",
                  "live": "Текущий результат", "exit": "Завершение работы",
                  "mirror_catalog": "Известные зеркала", "mirror_choice": "Выбор зеркала",
                  "browser": "Выбор файла или папки", "updates": "Обновление баз", "update_log": "Журнал обновления",
                  "scan_confirm": "Подтверждение остановки", "engine_missing": "Движок не установлен",
                  "detections": "Обнаруженные файлы", "detection_action": "Действие с файлом",
                  "quarantine": "Карантин ClamUI", "quarantine_item": "Файл в карантине",
                  "quarantine_confirm": "Подтверждение карантина", "restore_confirm": "Подтверждение восстановления",
                  "delete_confirm": "Подтверждение удаления", "ignore_confirm": "Подтверждение белого списка",
                  "ignore_list": "Белый список ClamUI", "ignore_remove_confirm": "Убрать путь из белого списка"}
        self.write(1, 2, "ClamUI", accent | curses.A_BOLD)
        self.write(1, 12, "/ " + titles.get(self.page, self.page))
        self.write(2, 2, "─" * (w - 5), accent)
        self.write(3, 2, str(self.browser.directory) if self.page == "browser" else self.engine, curses.A_DIM)
        items = self.menu()
        if items:
            self.selected = max(0, min(self.selected, len(items) - 1))
            slots = (h - 10) if self.page == "browser" else min(8, h - 12)
            first = max(0, self.selected - slots + 1)
            for y, (label, _) in enumerate(items[first:first + slots], 5):
                index = first + y - 5
                self.write(y, 2, ("› " if index == self.selected else "  ") + label,
                           curses.A_REVERSE if index == self.selected else 0)
        y = 5 + min(len(items), min(8, h - 12)) + 1
        if self.page == "home":
            self.write(y, 4, "Выберите действие и нажмите Enter.", curses.A_DIM)
            self.write(y + 1, 4, "Локальное сканирование • действия только вручную", curses.A_DIM)
        elif self.page == "engine_missing":
            missing = ", ".join(missing_clamav_tools())
            self.write(y, 2, "Не найдены обязательные исполняемые файлы: " + missing, accent)
            self.write(y + 1, 2, "ClamAV is an open-source antivirus toolkit for detecting malicious software.")
            self.write(y + 2, 2, "It includes a command-line scanner and FreshClam database updater.")
            self.write(y + 3, 2, "Установка идёт… вывод пакетного менеджера обновляется ниже." if self.installing else
                       "Для установки ClamAV потребуются права администратора.")
            self.write(y + 4, 2, "PgUp/PgDn — прокрутка вывода установки.", curses.A_DIM)
            if self.install_output:
                top, bottom = y + 6, h - 4
                visible = max(0, bottom - top)
                max_scroll = max(0, len(self.install_output) - visible)
                self.scroll = max(0, min(self.scroll, max_scroll))
                for row, line in enumerate(self.install_output[self.scroll:self.scroll + visible], top):
                    self.write(row, 2, line, curses.A_DIM)
        elif self.page == "scan":
            status, _, _, _ = self.scanner.snapshot()
            elapsed = time.monotonic() - self.scanner.started if self.scanner.busy else self.scanner.elapsed
            progress = self.scanner.progress()
            self.write(y, 2, STATUS.get(status, "Проверка ещё не запускалась") + (f" · {elapsed:.0f} с" if status else ""), accent)
            self.write(y + 1, 2, self.progress_label(progress), accent)
            if progress["percent"] is not None:
                blocks = progress["percent"] * 20 // 100
                self.write(y + 2, 2, "[" + "#" * blocks + "-" * (20 - blocks) + "] " +
                           f"Ошибок: {progress['errors']} · Пропусков: {progress['skipped']}")
            elif status == "running":
                self.write(y + 2, 2,
                           f"Текущая проверка · ошибок: {progress['errors']} · пропусков: {progress['skipped']}")
            self.write(y + 3, 2, progress["current"], curses.A_DIM)
            list_top = y + 5
            list_bottom = h - 4
            list_rows = max(0, list_bottom - list_top)
            findings = self.scanner.findings_snapshot()
            if list_rows:
                caption = (f"Обнаруженные угрозы · {len(findings)}" if findings else
                           "Угроз не обнаружено" if status == "clean" else
                           "Находок пока нет" if self.scanner.busy else "Список находок пуст")
                rule_width = max(0, w - 5)
                caption = clipped(caption, rule_width - 4)
                remaining = max(0, rule_width - len(caption) - 2)
                left = remaining // 2
                divider = "─" * left + " " + caption + " " + "─" * (remaining - left)
                self.write(y + 4, 2, divider, curses.A_DIM)
                max_scroll = max(0, len(findings) - list_rows)
                self.scan_list_scroll = max(0, min(self.scan_list_scroll, max_scroll))
                for row, line in enumerate(findings[self.scan_list_scroll:self.scan_list_scroll + list_rows], list_top):
                    self.write(row, 2, line, curses.A_DIM)
        elif self.page == "mirrors":
            self.write(y, 2, "Источники обновления локальных баз ClamUI.", accent)
            self.write(y + 1, 2, "Системный freshclam не меняется. Новые адреса нужно сохранить.", curses.A_DIM)
        elif self.page == "mirror_catalog":
            self.write(y, 2, "Выберите сервер; затем назначьте основным или резервным.", accent)
            self.write(y + 1, 2, "Каталог источников от " + VERIFIED_DATE + "; доступность не проверена.", curses.A_DIM)
        elif self.page == "mirror_choice":
            self.write(y, 2, self.mirror_choice.name, accent)
            self.write(y + 1, 2, self.mirror_choice.url)
            self.write(y + 2, 2, self.mirror_choice.note, curses.A_DIM)
            self.write(y + 3, 2, "После выбора нажмите «Сохранить источники» или «Сохранить и обновить».", curses.A_DIM)
        elif self.page == "updates":
            state, lines, _ = self.updater.snapshot()
            mode = "только свои зеркала" if self.config.mode == "private_only" else "официальные серверы"
            self.write(y, 2, "Источники: " + mode, accent)
            self.write(y + 1, 2, "Каталог: " + str(self.store.data_dir), curses.A_DIM)
            self.write(y + 2, 2, {"idle": "Готово к обновлению", "running": "Обновление идёт…", "success": "Базы успешно обновлены", "failed": "Ошибка обновления — прежние базы сохранены", "cancelled": "Обновление отменено"}[state], accent)
            available = max(0, h - y - 7)
            for row, line in enumerate(lines[-available:] if available else [], y + 3):
                self.write(row, 2, line, curses.A_DIM)
        elif self.page == "browser":
            self.write(h - 4, 2, "Enter: открыть · Space: выбрать · F2: эта папка · .: скрытые", accent)
        elif self.page == "settings":
            self.write(y, 2, "Лимиты действуют для следующей проверки; Enter позволяет изменить МиБ.", curses.A_DIM)
        elif self.page == "history" and not self.rows:
            self.write(y, 2, "История пуста. Запустите первую проверку.", curses.A_DIM)
        elif self.page == "exit":
            self.write(y, 2, "Текущая операция будет остановлена; прежние базы сохранятся.")
        elif self.page == "scan_confirm":
            self.write(y, 2, "Остановить текущую проверку? Её неполный результат сохранится в истории.", accent)
        elif self.page == "detection_action":
            self.write(y, 2, "Выбранный файл: " + str(self.selected_detection), accent)
            self.write(y + 1, 2, "Перемещение начнётся только после отдельного подтверждения.", curses.A_DIM)
        elif self.page == "quarantine_confirm":
            self.write(y, 2, "Файл будет удалён из исходного места и сохранён в карантине ClamUI:", accent)
            self.write(y + 1, 2, str(self.selected_detection), curses.A_DIM)
        elif self.page == "delete_confirm":
            self.write(y, 2, "Файл будет удалён без возможности восстановления:", accent)
            self.write(y + 1, 2, str(self.selected_detection), curses.A_DIM)
        elif self.page == "ignore_confirm":
            self.write(y, 2, "Этот точный путь будет пропускаться в следующих проверках:", accent)
            self.write(y + 1, 2, str(self.selected_detection), curses.A_DIM)
        elif self.page == "ignore_remove_confirm":
            self.write(y, 2, "После удаления пути из белого списка файл будет проверяться снова:", accent)
            self.write(y + 1, 2, str(self.selected_ignored_path), curses.A_DIM)
        elif self.page == "quarantine_item" and self.selected_quarantine:
            self.write(y, 2, "Исходный путь: " + self.selected_quarantine.original, accent)
            self.write(y + 1, 2, "Восстановление не перезапишет существующий файл.", curses.A_DIM)
        elif self.page == "restore_confirm" and self.selected_quarantine:
            self.write(y, 2, "Восстановить файл по исходному пути?", accent)
            self.write(y + 1, 2, self.selected_quarantine.original, curses.A_DIM)
            self.write(y + 2, 2, "Если путь занят, операция завершится без перезаписи.", curses.A_DIM)
        elif self.page in {"help", "preview", "detail", "live", "update_log"}:
            lines = self.document()
            room = h - 10
            self.scroll = max(0, min(self.scroll, max(0, len(lines) - room)))
            for row, line in enumerate(lines[self.scroll:self.scroll + room], 5):
                self.write(row, 2, line)
            if len(lines) > room:
                self.write(h - 5, 2, f"Строки {self.scroll + 1}–{min(self.scroll + room, len(lines))} / {len(lines)}", curses.A_DIM)
        status = "Проверка идёт — можно переходить между экранами" if self.scanner.busy else ("Базы обновляются — можно переходить между экранами" if self.updater.busy else self.notice)
        if self.notice:
            status = self.notice
        self.write(h - 3, 2, status, accent)
        footer = ("↑↓ меню  PgUp/PgDn список угроз  Enter Открыть  Esc Назад  F1 Справка"
                  if self.page == "scan" else "↑↓ Выбор/прокрутка  Enter Открыть  Esc Назад  F1 Справка")
        if self.page == "scan":
            footer = "↑↓ меню  F5 Запуск  F6 Остановить  PgUp/PgDn список угроз  Esc назад"
        elif self.page == "engine_missing" and self.install_output:
            footer = "↑↓ выбор  Enter действие  PgUp/PgDn журнал установки  Esc выход"
        self.write(h - 2, 2, footer, curses.A_DIM)
        if self.edit:
            self.render_editor(h, w)
        self.win.refresh()

    @staticmethod
    def progress_label(progress):
        if progress["phase"] == "counting":
            return f"Составление списка… найдено файлов: {progress['total']}"
        if progress["phase"] == "loading":
            return f"Загрузка баз… 0% · 0/{progress['total']} файлов"
        if progress["percent"] is not None:
            return f"{progress['percent']}% · обработано {progress['completed']}/{progress['total']} файлов · находок {progress['found']}"
        return "Нет файлов для расчёта процента"

    def document(self):
        if self.page == "help":
            return ["ClamUI · прототип 0.2", "", "↑↓ или j/k — выбор; Enter — действие; Esc — назад.",
                    "Tab — следующий пункт. PgUp/PgDn — прокрутка результата.",
                    "На экране проверки F5 Запуск, F6 Остановить (с подтверждением).",
                    "Ctrl+C — запрос выхода с отменой активной проверки.", "",
                    "Путь: выбор из списка или ручной ввод с дополнением по Tab.",
                    "Меню истории хранит последние 100 записей (время UTC).",
                    "Подробный журнал хранит полный вывод ClamAV последней проверки.",
                    "Процент = обработанные файлы / первоначальный список файлов.",
                    f"Лимиты clamscan: файл {self.config.max_filesize_mib} МиБ; проверка {self.config.max_scansize_mib} МиБ.",
                    "Это не процент времени или байтов. Ошибки показаны отдельно.",
                    "Новые файлы после подсчёта в задание не добавляются.",
                    "Symlink и другие файловые системы не обходятся.",
                    "Нулевой код ClamAV не доказывает проверку всех файлов.", "",
                    "Зеркала: основной адрес, необязательный резервный адрес.",
                    "Сохранение задаёт источники кнопки «Обновить базы».",
                    "Предпросмотр — фрагмент, не готовый системный конфиг.",
                    "Обновление идёт в пользовательский каталог без root.",
                    "Сканирование затем использует успешно обновлённые базы.",
                    "Действия с находками доступны вручную: карантин, удаление или белый список.",
                    "Карантин обратим; удаление требует подтверждения. Белый список хранит точный путь.",
                    "",
                    "Настройки: " + str(self.store.config_path),
                    "История: " + str(self.store.db)]
        if self.page == "preview":
            try:
                return self.draft.preview().splitlines() + ["", "Используется при пользовательском обновлении.",
                    "Системная служба и /etc не изменяются."]
            except ValueError as exc:
                return ["Ошибка настроек:", str(exc), "", "Esc — вернуться и исправить"]
        if self.page == "update_log":
            return self.updater.snapshot()[1] or ["Обновление ещё не запускалось в этой сессии"]
        if self.page == "detail" and self.record:
            r = self.record
            return [STATUS.get(r["status"], r["status"]), r["path"], r["started"],
                    "Код ClamAV: " + str(r["code"]), ""] + r["output"].splitlines()
        status, lines, path, code = self.scanner.snapshot()
        return [STATUS.get(status, "Проверка ещё не запускалась"), self.progress_label(self.scanner.progress()), path,
                "Код ClamAV: " + str(code), ""] + lines

    def render_editor(self, h, w):
        field, label, value, cursor = self.edit
        y = h - 7
        self.write(y, 2, " " * (w - 4), curses.A_REVERSE)
        self.write(y, 3, label, curses.A_REVERSE)
        start = max(0, cursor - (w - 12) // 2)
        visible = clipped(value[start:], w - 8)
        self.write(y + 1, 2, " " * (w - 4))
        self.write(y + 1, 3, visible)
        hint = ("Enter — сохранить число МиБ · диапазон показан выше · Esc — отмена"
                if field in {"max_filesize_mib", "max_scansize_mib"}
                else "Enter — принять · Tab — дополнить путь · Ctrl+U — очистить")
        self.write(y + 2, 2, hint)
        try:
            curses.curs_set(1)
            offset = sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in value[start:cursor])
            self.win.move(y + 1, min(w - 3, 3 + offset))
        except curses.error:
            pass

    def edit_key(self, key):
        field, label, value, cursor = self.edit
        if key != "\t":
            self.completions = None
        if key == "\t" and field == "path":
            if self.completions:
                candidates, index = self.completions
                value = candidates[index % len(candidates)]
                self.completions = candidates, index + 1
            else:
                value, candidates = complete_path(value[:cursor])
                if len(candidates) > 1:
                    self.completions = candidates, 0
                    self.notice = "Ещё Tab — варианты: " + ", ".join(Path(c.rstrip("/")).name for c in candidates[:5])
                elif not candidates:
                    self.notice = "Совпадений нет"
            cursor = len(value)
        elif key == "\x1b":
            self.edit = None
        elif key in ("\n", "\r", curses.KEY_ENTER):
            if field == "path":
                self.target = value
            elif field in {"max_filesize_mib", "max_scansize_mib"}:
                try:
                    candidate = replace(self.config, **{field: int(value.strip())})
                    candidate.validate()
                    self.store.save(candidate)
                    self.config = candidate
                except (ValueError, sqlite3.Error) as exc:
                    self.notice = safe_text(exc)
                    return
            else:
                setattr(self.draft, field, value.strip())
            self.edit = None
        elif key == "\x15":
            value, cursor = "", 0
        elif key in (curses.KEY_BACKSPACE, "\x7f", "\b"):
            if cursor:
                value, cursor = value[:cursor - 1] + value[cursor:], cursor - 1
        elif key == curses.KEY_DC:
            value = value[:cursor] + value[cursor + 1:]
        elif key == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_RIGHT:
            cursor = min(len(value), cursor + 1)
        elif key in (curses.KEY_HOME, "\x01"):
            cursor = 0
        elif key in (curses.KEY_END, "\x05"):
            cursor = len(value)
        elif isinstance(key, str) and key.isprintable() and len(value) < 4096:
            value = value[:cursor] + key + value[cursor:]
            cursor += len(key)
        if self.edit:
            self.edit = field, label, value, cursor
        else:
            try:
                curses.curs_set(0)
            except curses.error:
                pass

    def begin_edit(self, field, label, value):
        self.edit = field, label, value, len(value)
        self.completions = None

    def activate(self, action):
        if self.page == "history" and action.isdigit():
            self.record = self.rows[int(action)]
            self.go("detail")
        elif self.page == "detections" and action.startswith("detection:"):
            paths = self.scanner.finding_paths_snapshot()
            self.selected_detection = paths[int(action.split(":", 1)[1])]
            self.selected_detection_identity = self.scanner.finding_identity(self.selected_detection)
            self.go("detection_action")
        elif self.page == "quarantine" and action.startswith("quarantine:"):
            self.selected_quarantine = self.quarantine_entries[int(action.split(":", 1)[1])]
            self.go("quarantine_item")
        elif self.page == "ignore_list" and action.startswith("ignored:"):
            self.selected_ignored_path = self.ignored_paths[int(action.split(":", 1)[1])]
            self.go("ignore_remove_confirm")
        elif action == "browse":
            path = Path(self.target).expanduser()
            self.browser.open(path if path.is_dir() else path.parent)
            self.go("browser")
        elif action == "parent":
            self.browser.open(self.browser.directory.parent)
            self.selected = 0
        elif action == "choose_dir":
            self.target = str(self.browser.directory)
            self.go("scan")
        elif action.startswith("entry:"):
            _, path, kind = self.browser.entries[int(action.split(":")[1])]
            if kind == "link":
                raise ValueError("Символьные ссылки не сканируются; выберите исходный файл")
            if kind == "dir":
                self.browser.open(path)
                self.selected = 0
            else:
                self.target = str(path)
                self.go("scan")
        elif action.startswith("preset:"):
            self.mirror_choice = MIRRORS[int(action.split(":")[1])]
            self.go("mirror_choice")
        elif action in {"preset_primary", "preset_backup", "preset_official"}:
            mirror = self.mirror_choice
            if action == "preset_official":
                self.draft.mode = "official"
            elif action == "preset_primary":
                self.draft.mode, self.draft.primary = "private_only", mirror.url
                if self.draft.backup == mirror.url:
                    self.draft.backup = ""
            else:
                if not self.draft.primary:
                    raise ValueError("Сначала выберите основное зеркало")
                if self.draft.primary == mirror.url:
                    raise ValueError("Это зеркало уже задано основным")
                self.draft.mode, self.draft.backup = "private_only", mirror.url
            self.go("mirrors")
            self.notice = "Выбор ещё не сохранён. Сохраните источники перед обновлением."
        elif action == "path":
            self.begin_edit("path", "Путь к файлу или папке", self.target)
        elif action in {"max_filesize_mib", "max_scansize_mib"}:
            label = ("Максимальный размер файла (МиБ, 1–2048)" if action == "max_filesize_mib"
                     else "Максимальный объём сканирования (МиБ, 1–4096)")
            self.begin_edit(action, label, str(getattr(self.config, action)))
        elif action in {"primary", "backup"}:
            self.begin_edit(action, "Адрес зеркала: https://сервер/путь", getattr(self.draft, action))
        elif action == "mode":
            self.draft.mode = "private_only" if self.draft.mode == "official" else "official"
        elif action in {"save_mirrors", "save_update"}:
            candidate = replace(self.config, mode=self.draft.mode, primary=self.draft.primary, backup=self.draft.backup)
            self.store.save(candidate)
            self.config = candidate
            self.notice = "Источники сохранены для обновления баз ClamUI."
            if action == "save_update":
                self.go("updates")
                self.updater.start(self.config)
        elif action in {"recursive", "color"}:
            if action == "recursive" and self.scanner.busy:
                raise ValueError("Параметры можно изменить после завершения проверки")
            candidate = replace(self.config, **{action: not getattr(self.config, action)})
            self.store.save(candidate)
            self.config = candidate
        elif action == "language":
            candidate = replace(self.config, language="ru" if self.config.language == "en" else "en")
            self.store.save(candidate)
            self.config = candidate
            self.notice = ("Язык интерфейса изменён на русский." if candidate.language == "ru"
                           else "Interface language changed to English.")
        elif action == "github":
            self.open_project_link()
        elif action == "confirm_quarantine":
            if not self.selected_detection:
                raise ValueError("Сначала выберите обнаруженный файл")
            quarantined = self.quarantine.quarantine(self.selected_detection, self.selected_detection_identity)
            self.scanner.remove_finding(self.selected_detection)
            self.selected_detection = None
            self.selected_detection_identity = None
            self.go("scan")
            self.notice = "Файл перемещён в карантин: " + quarantined.original
        elif action == "confirm_delete":
            if not self.selected_detection:
                raise ValueError("Сначала выберите обнаруженный файл")
            deleted = self.quarantine.delete(self.selected_detection, self.selected_detection_identity)
            self.scanner.remove_finding(self.selected_detection)
            self.selected_detection = None
            self.selected_detection_identity = None
            self.go("scan")
            self.notice = "Файл удалён: " + str(deleted)
        elif action == "confirm_ignore":
            if not self.selected_detection:
                raise ValueError("Сначала выберите обнаруженный файл")
            self.quarantine.verify_detection(self.selected_detection, self.selected_detection_identity)
            self.store.ignore_path(self.selected_detection)
            ignored = self.selected_detection
            self.scanner.remove_finding(ignored)
            self.selected_detection = None
            self.selected_detection_identity = None
            self.go("scan")
            self.notice = "Путь добавлен в белый список: " + ignored
        elif action == "confirm_restore":
            if not self.selected_quarantine:
                raise ValueError("Сначала выберите файл в карантине")
            restored = self.quarantine.restore(self.selected_quarantine.token)
            self.selected_quarantine = None
            self.go("quarantine")
            self.notice = "Файл восстановлен: " + str(restored)
        elif action == "confirm_unignore":
            if not self.selected_ignored_path:
                raise ValueError("Сначала выберите путь из белого списка")
            removed = self.selected_ignored_path
            self.store.unignore_path(removed)
            self.selected_ignored_path = None
            self.go("ignore_list")
            self.notice = "Путь удалён из белого списка: " + removed
        elif action == "start":
            if not self.target.strip():
                raise ValueError("Укажите путь")
            self.scan_list_scroll = 0
            self.scanner.start(self.target, self.config.recursive,
                               self.config.max_filesize_mib, self.config.max_scansize_mib)
            self.notice = ""
        elif action == "install_engine":
            self.install_engine()
        elif action == "start_update":
            self.updater.start(self.config)
            self.notice = ""
        elif action == "cancel_update":
            self.updater.cancel()
            self.notice = "Отменяем обновление…"
        elif action == "cancel":
            if self.scanner.busy:
                self.previous = self.page
                self.go("scan_confirm")
            else:
                self.notice = "Проверка уже завершена"
        elif action == "confirm_scan_cancel":
            self.scanner.cancel()
            self.go(self.previous if self.previous == "scan" else "scan")
            self.notice = "Запрошена остановка проверки…"
        elif action == "resume_scan":
            self.go(self.previous)
        elif action == "exit":
            if self.scanner.busy or self.updater.busy:
                self.previous = self.page
                self.go("exit")
            else:
                self.exit_requested = True
        elif action == "confirm_exit":
            self.updater.cancel()
            self.scanner.cancel()
            self.exit_requested = True
        elif action == "stay":
            self.go(self.previous)
        else:
            self.go(action)

    def install_engine(self):
        self.install_output = []
        self.scroll = 0
        self.install_follow = True
        missing_tools = missing_clamav_tools()
        if not missing_tools:
            self.go("home")
            self.notice = "Все обязательные исполняемые файлы ClamAV уже доступны."
            return
        manager = detect_package_manager()
        if manager is None:
            supported = ", ".join(candidate.label for candidate in PACKAGE_MANAGERS)
            self.notice = "Пакетный менеджер не распознан. Установите ClamAV вручную; поддерживаются: " + supported
            return
        termux = manager.key == "termux"
        is_root = os.geteuid() == 0
        sudo = None if is_root or termux else shutil.which("sudo")
        if not is_root and not termux and not sudo:
            command = manual_install_command(manager, sudo=False)
            self.notice = "Автоустановка требует sudo; запустите эту команду от root: " + command
            return
        result = None
        failure = ""
        authorization = None
        try:
            curses.def_prog_mode()
            curses.endwin()
            if sudo:
                authorization = subprocess.run([sudo, "-v"], check=False,
                                               env={**os.environ, "LC_ALL": "C"})
            else:
                authorization = subprocess.CompletedProcess([], 0)
        except KeyboardInterrupt:
            failure = "Запрос прав sudo прервали с клавиатуры."
        except (OSError, subprocess.SubprocessError, curses.error) as exc:
            failure = "Не удалось получить права для установки: " + safe_text(exc)
        finally:
            try:
                curses.reset_prog_mode()
                self.win.clear()
                self.win.refresh()
            except curses.error:
                pass
        if not failure and authorization is not None and authorization.returncode != 0:
            failure = f"Не удалось получить права sudo (код {authorization.returncode})."
        if not failure:
            try:
                result = self._run_installer(sudo, manager)
            except (OSError, subprocess.SubprocessError) as exc:
                failure = "Не удалось запустить установщик: " + safe_text(exc)
        missing = missing_clamav_tools()
        if result is not None and result != 0:
            failure = f"Процесс установки завершился с кодом {result}."
        if missing:
            names = ", ".join(missing)
            detail = "После попытки установки всё ещё не найдены: " + names
            self.notice = (failure + " " + detail).strip()
            return
        self.engine = "Системные базы · " + engine_status()
        self.go("home")
        self.notice = ("Компоненты ClamAV установлены и доступны."
                       if not failure else "Исполняемые файлы доступны, но " + failure)

    def _run_installer(self, sudo, manager):
        output_queue = queue.Queue()
        self.install_output = []
        self.scroll = 0
        self.install_follow = True
        command = manager.command()
        if sudo:
            command = [sudo, "-n", *command]
        env = {**os.environ, "LC_ALL": "C"}
        if manager.key == "apt":
            env["DEBIAN_FRONTEND"] = "noninteractive"
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            # Keep sudo attached to the same controlling TTY used by `sudo -v`.
            # A detached session can invalidate per-TTY sudo credentials.
            text=True, errors="replace", bufsize=1,
            env=env)

        def read_output():
            try:
                for line in process.stdout:
                    for part in line.replace("\r", "\n").splitlines():
                        if part:
                            output_queue.put(part)
            finally:
                output_queue.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        self.installing = True
        try:
            self.render()
            finished_reading = False
            while process.poll() is None or not finished_reading:
                try:
                    while True:
                        line = output_queue.get_nowait()
                        if line is None:
                            finished_reading = True
                            break
                        self.install_output.append(safe_text(line))
                        if len(self.install_output) > 500:
                            self.install_output = self.install_output[-500:]
                        if self.install_follow:
                            self.scroll = len(self.install_output)
                except queue.Empty:
                    pass
                self.render()
                try:
                    key = self.win.get_wch()
                except curses.error:
                    key = None
                if key in (curses.KEY_NPAGE, curses.KEY_PPAGE):
                    height = self.win.getmaxyx()[0]
                    y = 5 + min(len(self.menu()), min(8, height - 12)) + 1
                    page = max(1, height - 4 - (y + 6))
                    self.scroll += page if key == curses.KEY_NPAGE else -page
                    max_scroll = max(0, len(self.install_output) - page)
                    self.scroll = max(0, min(self.scroll, max_scroll))
                    self.install_follow = key == curses.KEY_NPAGE and self.scroll >= max_scroll
                elif key in ("\x03", "\x1b"):
                    self.notice = "Установка выполняется; дождитесь её завершения."
            return process.wait()
        finally:
            self.installing = False
            reader.join()
            process.stdout.close()

    def run(self):
        curses.set_escdelay(40)
        self.win.keypad(True)
        self.win.timeout(100)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_CYAN, -1)
                self.has_colors = True
            except curses.error:
                pass
        threading.Thread(target=self.set_engine, daemon=True).start()
        try:
            while not self.exit_requested:
                if self.update_was_busy and not self.updater.busy:
                    threading.Thread(target=self.set_engine, daemon=True).start()
                self.update_was_busy = self.updater.busy
                self.render()
                try:
                    key = self.win.get_wch()
                except curses.error:
                    continue
                except KeyboardInterrupt:
                    key = "\x03"
                try:
                    if key == "\x03":
                        self.edit = None
                        self.activate("exit")
                    elif self.edit:
                        self.edit_key(key)
                    elif self.page == "browser" and key in (" ", curses.KEY_F2, curses.KEY_BACKSPACE, "\x7f", "."):
                        if key == curses.KEY_F2:
                            self.activate("choose_dir")
                        elif key in (curses.KEY_BACKSPACE, "\x7f"):
                            self.activate("parent")
                        elif key == ".":
                            self.browser.show_hidden = not self.browser.show_hidden
                            self.browser.open(self.browser.directory)
                            self.selected = 0
                        elif self.selected < 2:
                            self.activate(self.menu()[self.selected][1])
                        else:
                            _, path, kind = self.browser.entries[self.selected - 2]
                            if kind == "link":
                                raise ValueError("Символьные ссылки не сканируются")
                            self.target = str(path)
                            self.go("scan")
                    elif key == curses.KEY_F1:
                        self.go("help")
                    elif key == curses.KEY_F5 and self.page == "scan":
                        if self.scanner.busy:
                            self.notice = "Проверка уже выполняется"
                        else:
                            self.activate("start")
                    elif key == curses.KEY_F6 and self.page != "scan_confirm":
                        if self.scanner.busy:
                            self.previous = self.page
                            self.go("scan_confirm")
                        else:
                            self.notice = "Активной проверки нет"
                    elif key == "\x1b":
                        if self.page == "home" or self.win.getmaxyx()[0] < 20 or self.win.getmaxyx()[1] < 70:
                            self.activate("exit")
                        else:
                            self.go({"preview": "mirrors", "detail": "history", "live": "scan",
                                     "scan_confirm": self.previous, "browser": "scan", "mirror_catalog": "mirrors",
                                     "mirror_choice": "mirror_catalog", "update_log": "updates", "exit": self.previous,
                                     "detections": "scan", "detection_action": "detections",
                                     "quarantine": "home", "quarantine_item": "quarantine",
                                     "quarantine_confirm": "detection_action",
                                     "restore_confirm": "quarantine_item", "delete_confirm": "detection_action",
                                     "ignore_confirm": "detection_action", "ignore_list": "home",
                                     "ignore_remove_confirm": "ignore_list"}.get(self.page, "home"))
                    elif key in (curses.KEY_DOWN, "j", "\t", curses.KEY_UP, "k", curses.KEY_BTAB):
                        delta = -1 if key in (curses.KEY_UP, "k", curses.KEY_BTAB) else 1
                        if self.menu():
                            self.selected = (self.selected + delta) % len(self.menu())
                        else:
                            self.scroll += delta
                    elif key in (curses.KEY_NPAGE, curses.KEY_PPAGE):
                        if self.page == "scan":
                            height = self.win.getmaxyx()[0]
                            items = self.menu()
                            y = 5 + min(len(items), min(8, height - 12)) + 1
                            page_size = max(1, height - 4 - (y + 5))
                            self.scan_list_scroll += page_size if key == curses.KEY_NPAGE else -page_size
                            self.scan_list_scroll = max(0, min(self.scan_list_scroll,
                                max(0, len(self.scanner.findings_snapshot()) - page_size)))
                        else:
                            self.scroll += 10 if key == curses.KEY_NPAGE else -10
                    elif key in ("\n", "\r", curses.KEY_ENTER) and self.menu():
                        self.activate(self.menu()[self.selected][1])
                except (ValueError, OSError, sqlite3.Error) as exc:
                    self.notice = safe_text(exc)
        finally:
            if self.updater.busy:
                self.updater.cancel()
            self.updater.join()
            if self.scanner.busy:
                self.scanner.cancel()
            self.scanner.join()


def run(store, config):
    curses.wrapper(lambda screen: TerminalUI(screen, store, config).run())
