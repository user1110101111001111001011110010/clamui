# Known ClamAV database sources

The built-in source catalog is maintained in `clamui/mirrors.py`. It provides
choices when starting a manual update and does not check network availability in
real time. Operator pages were last checked on 2026-10-05.

| Name | Catalog address | ClamUI mode | Basis |
|---|---|---|---|
| Microsoft | `https://packages.microsoft.com/clamav` | `PrivateMirror` | [Microsoft catalog](https://packages.microsoft.com/clamav/) lists `main.cvd`, `daily.cvd`, `bytecode.cvd`, and FILE_MANIFEST |
| TrueNetwork, Russia | `https://mirror.truenetwork.ru/clamav` | `PrivateMirror` | [Mirror page](https://mirror.truenetwork.ru/clamav/) identifies the ClamAV mirror and TrueNetwork as its operator |
| clamav-mirror.ru, Russia | `https://clamav-mirror.ru` | `PrivateMirror` | [Operator page](https://clamav-mirror.ru/) publishes PrivateMirror configuration and reports hourly updates |
| Official ClamAV CDN | `database.clamav.net` | Official mode | Recommended `DatabaseMirror` in the [ClamAV documentation](https://docs.clamav.net/manual/Usage/Configuration.html) |

`mirror.truenetwork.ru` and `clamav-mirror.ru` are operated by TrueNetwork. They
provide different access addresses, but are not independent operators for backup
purposes. Microsoft is a separate operator. ClamAV normalizes a trailing `/` when
parsing `PrivateMirror`; the catalog stores addresses without a trailing slash.

The official CDN selects ClamAV's distributed infrastructure; it is not a third-party
private mirror. Choosing it enables official mode and the standard DNS check.
`private_only` never falls back to the official CDN.

FreshClam downloads signed databases, and ClamUI keeps `TestDatabases yes` enabled.
A public catalog does not guarantee that a server is reachable from a particular
network, current, or able to serve future requests correctly. On failure, FreshClam
reports the source and ClamUI keeps the previously active databases. The **Check
mirror** action does not perform a separate network test yet; availability is tested
when **Update databases** runs.
