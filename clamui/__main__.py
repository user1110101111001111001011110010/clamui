from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sqlite3
import sys
import time

from .core import Scanner, STATUS, Store, engine_status, safe_text
from .updates import Updater


def main(argv=None):
    parser = argparse.ArgumentParser(description="ClamUI — терминальная оболочка ClamAV")
    parser.add_argument("--data-dir", type=Path, help="отдельный каталог настроек и истории")
    parser.add_argument("--scan", metavar="PATH", help="проверить путь без меню")
    parser.add_argument("--json", action="store_true", help="итог проверки или обновления в JSON")
    parser.add_argument("--update", action="store_true", help="обновить пользовательские базы ClamUI")
    parser.add_argument("--status", action="store_true", help="версия ClamAV и баз")
    parser.add_argument("--preview", action="store_true", help="источники пользовательского обновления")
    args = parser.parse_args(argv)
    if sum(bool(v) for v in (args.scan, args.update, args.status, args.preview)) > 1:
        parser.error("выберите одну операцию: --scan, --update, --status или --preview")
    if args.json and not (args.scan or args.update):
        parser.error("--json используется вместе с --scan или --update")
    if not any((args.scan, args.update, args.status, args.preview)) and not (sys.stdin.isatty() and sys.stdout.isatty()):
        parser.print_help()
        return 0
    store = None
    scanner = None
    old_handlers = {}
    try:
        store = Store(args.data_dir)
        if args.status:
            print(engine_status(store.active_database()))
            print("Базы: " + str(store.active_database() or "системные"))
            return 0
        if args.preview:
            print(store.load().preview(), end="")
            return 0
        store.acquire()
        config = store.load()
        if args.scan or args.update:
            scanner = Scanner(store) if args.scan else Updater(store)
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                old_handlers[sig] = signal.signal(sig, lambda *_: scanner.cancel())
            if args.scan:
                scanner.start(args.scan, config.recursive,
                              config.max_filesize_mib, config.max_scansize_mib)
            else:
                scanner.start(config)
            while scanner.busy:
                time.sleep(0.1)
            if args.update:
                status, lines, code = scanner.snapshot()
                if args.json:
                    print(json.dumps({"schema_version": 1, "status": status, "freshclam_exit_code": code, "output": lines}, ensure_ascii=True))
                else:
                    print("\n".join(lines))
                return {"success": 0, "cancelled": 130}.get(status, 2)
            status, lines, path, code = scanner.snapshot()
            result = {"schema_version": 1, "status": status, "path": path,
                      "clamscan_exit_code": code, "coverage": "not_verified", "progress": scanner.progress(),
                      "output": lines}
            if args.json:
                print(json.dumps(result, ensure_ascii=True))
            else:
                print(STATUS[status])
                print("\n".join(lines))
            return {"empty": 0, "clean": 0, "found": 1, "cancelled": 130}.get(status, 2)
        def interrupted(signum, frame):
            raise SystemExit(128 + signum)
        for sig in (signal.SIGTERM, signal.SIGHUP):
            old_handlers[sig] = signal.signal(sig, interrupted)
        from .tui import run
        run(store, config)
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print("ClamUI: " + safe_text(exc), file=sys.stderr)
        return 2
    finally:
        if scanner:
            if scanner.busy:
                scanner.cancel()
            scanner.join()
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        if store:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
