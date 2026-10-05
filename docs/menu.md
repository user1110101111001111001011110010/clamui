# Complete ClamUI menu tree

This is the target interface design. The prototype's current reduced menu is
described in the [README](../README.md). Per-user updates already work without
root; system changes through authorization in this tree belong to a future system
backend. The tree covers all planned architecture stages. `[later]` marks extra
stage-4 features; other items appear as stages 1–3 are implemented. `…` is a
selected list entry, not a hidden submenu. Esc goes back from every nested screen.

```text
ClamUI
├── Scan
│   ├── New scan
│   │   ├── Add file / folder: browser or path input
│   │   ├── Selected paths → remove from list / clear list
│   │   ├── Scan options
│   │   │   ├── Include subdirectories
│   │   │   ├── Exclusions: add / edit / remove
│   │   │   ├── Symlinks and other filesystems
│   │   │   ├── File and archive limits
│   │   │   └── Engine: clamscan / clamd [later]
│   │   └── Validate options and start
│   ├── Current scan
│   │   ├── Phase, elapsed time, counters, and available progress
│   │   ├── Findings in a short list at the bottom → scroll with PgUp/PgDn
│   │   ├── Full ClamAV log → raw output, including clean files
│   │   ├── Finding → entry → details
│   │   ├── Errors and skipped files → reason
│   │   └── Stop → confirmation
│   └── Schedule [later]
│       ├── Job list → create / edit / remove
│       └── Job → paths / options / time / enable or disable
├── Scan history
│   ├── Filters: period / result / detections
│   ├── Scan…
│   │   ├── Summary: engine, databases, coverage, duration
│   │   ├── Findings → file…
│   │   │   ├── Path, signature, file state
│   │   │   ├── Scan again
│   │   │   └── Quarantine → verify identity → confirm
│   │   ├── Errors, skipped files, and diagnostics
│   │   └── Repeat scan → review options → start
│   └── Clear history → choose period → confirm
├── Quarantine
│   ├── Filters: date / signature / operation state
│   ├── File…
│   │   ├── Details: original path, reason, date, hash
│   │   ├── Restore → original or other location → confirm
│   │   └── Delete permanently → confirm
│   └── Incomplete operations → details / retry safe restore
├── Databases and updates
│   ├── Status
│   │   ├── ClamAV and database versions, database date
│   │   ├── Update service and last update
│   │   └── Active profile and differences from draft
│   ├── Update now → progress → result
│   ├── Update sources
│   │   ├── Mode
│   │   │   ├── Official servers
│   │   │   └── Private mirrors only — official sources disabled
│   │   ├── Known mirrors → mirror…
│   │   │   ├── Microsoft → set as primary
│   │   │   ├── TrueNetwork → set as primary / backup
│   │   │   ├── clamav-mirror.ru → set as primary / backup
│   │   │   └── Official CDN → official mode
│   │   ├── Custom mirrors
│   │   │   ├── Add → name / address / enabled
│   │   │   └── Mirror…
│   │   │       ├── Edit name and address
│   │   │       ├── Enable / disable
│   │   │       ├── Check availability and redirects
│   │   │       └── Remove → confirm
│   │   └── Profiles
│   │       ├── Create / save draft
│   │       └── Profile… → open / rename / remove
│   ├── Update options
│   │   ├── Automatic updates: enable / disable
│   │   ├── Checks per day
│   │   └── Connection / read timeout
│   ├── Apply settings
│   │   ├── Validate profile and compatibility
│   │   ├── Review system changes and disabled sources
│   │   └── Apply → authorize → result
│   ├── Update log → operation… → sources / versions / errors
│   └── Restore settings
│       ├── View previous configuration
│       ├── Restore → review mode and changes → authorize
│       └── Reload current system settings
├── Settings
│   ├── Maximum file size: --max-filesize
│   ├── Maximum scan size: --max-scansize
│   ├── Default scan options
│   │   ├── Recursive directories
│   │   ├── Exclusions: add / edit / remove
│   │   ├── Symlinks and other filesystems
│   │   ├── File and archive limits
│   │   └── Engine: clamscan / clamd and local socket [later]
│   ├── Interface
│   │   ├── Language: English / Russian
│   │   ├── Palette: dark / light / no color
│   │   └── Characters: Unicode / ASCII
│   ├── History → retention period
│   └── Reset user settings → confirm
├── Help
│   ├── Keys and navigation
│   ├── Result meanings and scan limitations
│   ├── Mirror setup and disabling official sources
│   ├── CLI commands
│   ├── Diagnostics: dependencies / permissions / service status
│   └── About
└── Exit
    └── During a scan: stay / cancel scan and exit
```

Saving or opening a profile does not apply it to the system. Removing a saved
profile does not switch the active source. Resetting user settings does not change
system update configuration or enable official servers. Disabling automatic update
checks does not disable **Update now**.

`private_only` requires at least one enabled address. If all mirrors are unavailable,
the update fails and existing databases are preserved; there is no hidden fallback
to an official source. See [architecture.md](architecture.md) for network guarantee
limitations. Availability checks use only the entered address and do not follow
cross-domain redirects; they do not replace signature verification of downloaded
databases.

Options controlled by clamd configuration are read-only and include an explanation.
Unavailable actions explain whether a dependency or permission is missing.
Authorization is required for system changes, not for viewing screens or editing
drafts. A system helper completes configuration changes even if the TUI exits; a
later launch reads the result from its log. A started system update likewise does
not depend on the terminal staying open, unlike a per-user scan.

Keys: ↑↓ select, Enter open/run, Tab/Shift+Tab move between fields, Space toggle,
Esc back, F1 help, Ctrl+C cancel the current per-user operation. Ctrl+C does not
interrupt an atomic system-configuration change.
