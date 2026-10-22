# Android Exported Component Scanner

A small, dependency-free Python tool that scans an `AndroidManifest.xml` and lists the components an outside app could reach: exported activities, receivers and services.

Exported components are a common Android attack surface. This scanner gives you a quick first pass when reviewing an app.

## Requirements

- Python 3.9+
- No third-party packages

## Usage

```bash
python3 manifest_exports.py path/to/AndroidManifest.xml
python3 manifest_exports.py path/to/AndroidManifest.xml -o report.txt
```

| Option | Description |
| --- | --- |
| `manifest` | Path to a decoded (plain-text XML) `AndroidManifest.xml` |
| `-o`, `--output` | Write the plain report to a file instead of stdout |

The manifest must be decoded. If you start from an APK, decode it first, for example with `apktool d app.apk`.

## What gets flagged

| Status | Meaning |
| --- | --- |
| `EXPORTED` | The component sets `android:exported="true"` |
| `POTENTIALLY_EXPORTED` | `android:exported` is not set but the component has an `<intent-filter>`. Apps targeting Android 11 or lower treat this as exported; Android 12+ requires an explicit value |

Components with `android:exported="false"`, or with no intent filter and no explicit value, are not listed.

## Output

When run in a terminal, the tool prints a banner and a colored table with a summary. When piped or written with `-o`, it emits one plain line per component:

```
EXPORTED activity: com.example.app.MainActivity | permission: none
POTENTIALLY_EXPORTED service: com.example.app.SyncService | permission: com.example.PERMISSION
```

Each line has the status, component type, component name and the `android:permission` guarding it (`none` if unset). Entries are ordered activities, receivers, then services.

## Limitations

- Only `<activity>`, `<receiver>` and `<service>` are scanned. `<provider>` and `<activity-alias>` are not.
- It reads the manifest only and does not resolve manifest merging or the target SDK version.

## Tests

```bash
python3 -m unittest discover -s tests
```
