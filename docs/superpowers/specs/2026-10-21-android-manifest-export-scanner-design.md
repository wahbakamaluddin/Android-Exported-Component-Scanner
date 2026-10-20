# Android Manifest Export Scanner Design

## Purpose

Create a small command-line tool that combines the supplied activity, service,
and broadcast-receiver checks. It will identify confirmed and potentially
exported Android components without external dependencies.

## Interface

The tool will be invoked with Python 3:

```bash
python3 manifest_exports.py AndroidManifest_reversed.xml
python3 manifest_exports.py AndroidManifest_reversed.xml --output output.txt
```

The manifest path is required. Output defaults to standard output. The optional
`-o`/`--output` argument writes the same report to a file.

## Analysis Rules

The scanner will inspect `activity`, `service`, and `receiver` elements beneath
the manifest's `application` element.

- `android:exported="true"` is reported with status `EXPORTED`.
- A missing `android:exported` attribute combined with at least one
  `intent-filter` is reported with status `POTENTIALLY_EXPORTED`. This status
  calls attention to legacy, target-SDK-dependent behavior without asserting
  that the component is definitely exported.
- Components explicitly marked `android:exported="false"` are omitted.
- Components with neither an explicit true value nor an intent filter are
  omitted.
- Each result includes the component type, Android name, and component-level
  permission. A missing name is displayed as `?`; a missing permission as
  `none`.

The implementation will use Python's standard-library XML parser rather than
regular expressions so that namespaced attributes, multiline elements, and
self-closing elements are handled correctly.

## Output

Each matching component will occupy one line in manifest order:

```text
EXPORTED activity: com.example.MainActivity | permission: none
POTENTIALLY_EXPORTED receiver: com.example.LegacyReceiver | permission: com.example.SEND
```

If there are no matching components, the command succeeds and emits no result
lines.

## Error Handling

Missing/unreadable files, invalid XML, and output-write failures will produce a
concise message on standard error and a nonzero exit status. Successful scans
return zero.

## Testing

Automated tests will exercise the real command-line interface and cover:

- all three supported component types;
- explicit, implicit/potential, false, and non-exported cases;
- permission and missing-permission output;
- output-file behavior;
- invalid XML and missing input errors.

Implementation will follow test-driven development: establish failing CLI tests,
then add the minimum scanner implementation needed to pass them.
