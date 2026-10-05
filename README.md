# ClamUI

A terminal interface for ClamAV on Linux and compatible Unix systems. It requires
Python 3.11+ and has no third-party Python dependencies. Scanning requires
`clamscan`; database updates require `freshclam`.

ClamUI checks for both executables at startup. If either is missing, it can install
ClamAV through a detected package manager: APT, DNF/YUM, Zypper, Pacman, APK,
Termux `pkg` (without root), FreeBSD `pkg`, `pkgin`, OpenBSD `pkg_add`, or Gentoo
Portage. RPM-based systems use
DNF/YUM or Zypper; `rpm` itself does not resolve repository dependencies. The
installer output and errors appear in the ClamUI window. Installation requires
administrator privileges; ClamUI requests them through `sudo` or can be run as root.

## Run

```sh
python3 main.py
```

Run ClamUI in a regular terminal or the PyCharm terminal. `python3 -m clamui` also
works. A non-terminal Run prints help. Recommended terminal size is 80×24; minimum
size is 70×20. Use a UTF-8 locale.

## Menu

```text
ClamUI
├── Scan
│   ├── Select a file or folder → file browser
│   ├── Path → type a path with Tab completion
│   ├── Recursive directories: on / off
│   ├── Start / stop
│   ├── Short findings list → scroll at the bottom of the screen
│   └── Full ClamAV log
├── Update databases
│   ├── Start / cancel update
│   ├── Update log
│   └── Configure mirrors
├── History → scan → result
├── Databases and mirrors
│   ├── Mode: official / private mirrors only
│   ├── Known mirrors → Microsoft / TrueNetwork / clamav-mirror.ru / official
│   ├── Primary / backup mirror
│   ├── Preview freshclam sources
│   ├── Save sources
│   └── Save and update databases
├── Settings
│   ├── Recursive directories / color
│   ├── Interface language: English / Russian
│   ├── Maximum file size: 100 MiB (editable)
│   └── Maximum scan size: 400 MiB (editable)
├── Help
├── GitHub · clamui → open project page / copy URL if unavailable
└── Exit
```

Use ↑↓ or j/k to select, Enter to open, Esc to go back, and F1 for help. On the
scan screen, F5 starts a scan and F6 requests a stop confirmation. Stopping from
the menu also requires confirmation. PgUp/PgDn scroll the short findings list at
the bottom without moving the heading, counters, or menu. This list shows only
detections, like `clamscan -i`. The full log includes clean-file results and full
paths. Moving between screens does not cancel a running operation.

## Language

The interface defaults to English. Open **Settings → Interface language** to switch
between English and Russian. The choice is saved in ClamUI's TOML configuration.
Russian documentation is available in [README.ru.md](README.ru.md); Russian design
documents are provided alongside their English versions in `docs/`.

## Choosing paths

In the file browser:

- Enter opens a directory or selects a file.
- Space selects the highlighted file or directory without entering it.
- F2 or **Select this folder** selects the current directory.
- Backspace or `..` goes up one level; `.` shows hidden files.

In the path editor, Tab completes a path. If there are multiple matches, the first
Tab completes the common prefix and later presses cycle through matches. Spaces and
`~/` are supported; no shell is used. Ctrl+U clears the field, ←→ move the cursor,
and Esc cancels editing.

## Scan progress and limits

ClamUI creates a fixed list of regular files before scanning. One `clamscan` process
loads the databases and scans that list. Progress is
`received results / initial file count × 100`, rounded down. Starting a file and
duplicate detection lines do not increment the count. Database loading and file
inventory are separate phases.

Progress measures **files processed**, not bytes or time remaining. A large archive
can keep the value unchanged for a while. Errors and skipped files are shown
separately: 100% does not mean there were no errors or that every archive item was
fully analyzed. Missing results are not counted and progress is never artificially
raised to 100%. An empty directory displays “No files to scan”.

Files added after inventory are not included. The inventory records paths, not a
snapshot of file contents; files may change during the scan. Symlinks, special
files, and traversal onto other filesystems are excluded. Names containing newlines
or non-UTF-8 bytes are skipped because a file list cannot reliably pass and match
them. ClamUI's own configuration, history, and database directories are
automatically excluded. ClamUI does not delete or move scanned files.

Settings let you change the maximum individual file size (`--max-filesize`, default
100 MiB, range 1–2048) and maximum scan size (`--max-scansize`, default 400 MiB,
range 1–4096). Values are stored in TOML and passed to ClamAV in MiB. Files or
archives beyond these limits may be skipped. The scan-size limit includes archive
and container contents. `--alert-exceeds-max=yes` asks ClamAV to report limit
exceeded results.

## Updates and mirrors

**Update databases → Start update** runs `freshclam` as the current user. Databases
are stored in `$XDG_DATA_HOME/clamui` (default `~/.local/share/clamui`). Configure
mirrors in **Databases and mirrors** and save them; **Save and update** does both.

The built-in mirror list is documented in the [mirror catalog](docs/mirrors.md).
A public catalog does not guarantee availability from your network. TrueNetwork
and clamav-mirror.ru have the same operator, so they are not independent backup
providers. A configured address can be assigned as the primary or backup mirror.

- **Private mirrors only** uses `PrivateMirror`, with no official fallback or
  official DNS version check. A primary address is required; backup is optional.
- Signature checks and `TestDatabases` remain enabled.
- Downloads go to a separate directory. Only a complete successful set becomes
  active; failure or cancellation preserves the previous set. FreshClam retry
  intervals survive failed attempts.
- After the first successful update, scans explicitly use ClamUI's local databases.
  Before that, available system databases are used. The selected source appears in
  the header and scan result.
- Scanning and updating cannot run at the same time. Updates need extra disk space
  for a copy of the databases. The first update downloads a full set.

Database updates do not require administrator privileges. `/etc/clamav`, the system
freshclam service, clamd, and other applications are not modified or switched to
ClamUI's databases. Temporary freshclam configuration and databases are created in
a private directory under `/tmp` on Mint, where AppArmor allows freshclam to use it.
Termux and systems where `/tmp` is unavailable use a private temporary directory
under ClamUI's state directory. After a
successful verification, database files are copied into `$XDG_DATA_HOME/clamui` and
activated atomically. `/tmp` needs room for roughly one extra copy of the databases
during an update. A running system freshclam may still contact its own sources;
ClamUI mirror settings are not a system-wide network block. The latest update
result is stored in `last-update.json` beside the history database.

Quarantine, scheduling, clamd support, multiple selected targets, and system
service management are planned for later stages.

## CLI

```sh
python3 main.py --status
python3 main.py --scan ~/Downloads --json
python3 main.py --update
python3 main.py --update --json
python3 main.py --preview
python3 main.py --data-dir /tmp/clamui-demo
```

`--data-dir` isolates settings, history, and databases. Otherwise, configuration
is stored in `$XDG_CONFIG_HOME/clamui/config.toml` and history in
`$XDG_STATE_HOME/clamui/history.sqlite3`. Missing XDG variables use standard
directories under HOME. History shows the latest 100 jobs; full ClamAV output is
stored for each. Detailed lines for successful individual files are replaced by
counters.

Scan exit codes: 0 means no detections or no files; 1 means detections or warnings;
2 means an error or incomplete results; 130 means cancelled. For updates, 0 means
success, 2 means failure, and 130 means cancelled. With `--json`, the result object
goes to stdout and launch errors go to stderr. `coverage: not_verified` means the
progress percentage is not a guarantee of complete antivirus coverage.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Modules: `core.py` handles settings, history, and scanning; `paths.py` handles the
file inventory and path completion; `package_managers.py` selects system installers;
`updates.py` handles per-user updates; `process.py` handles cancellable processes;
`tui.py` implements curses; `__main__.py` implements the CLI. Test processes emulate
errors, cancellation, incomplete output, and updates. Fixture databases do not
replace testing with a real ClamAV installation.

Design documents: [architecture](docs/architecture.md), [full menu](docs/menu.md).
The Russian README and design documents are available in `README.ru.md` and
`docs/*.ru.md`.
