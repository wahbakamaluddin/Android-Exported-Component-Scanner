# Android Manifest Export Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free Python CLI that reports confirmed and potentially exported activities, services, and receivers from an Android manifest.

**Architecture:** `manifest_exports.py` will parse XML with `xml.etree.ElementTree`, convert matching application components into formatted report lines, and expose an `argparse` CLI for standard-output or file output. `tests/test_manifest_exports.py` will invoke the real CLI in temporary directories and assert its output, exit status, and error behavior.

**Tech Stack:** Python 3 standard library (`argparse`, `pathlib`, `xml.etree.ElementTree`, `unittest`, `subprocess`, `tempfile`)

**Spec:** `docs/superpowers/specs/2026-10-21-android-manifest-export-scanner-design.md`

## Global Constraints

- Require a manifest path and support optional `-o`/`--output`.
- Use only the Python 3 standard library.
- Report explicit `android:exported="true"` as `EXPORTED`.
- Report missing `android:exported` with a direct `intent-filter` child as `POTENTIALLY_EXPORTED`.
- Inspect only `activity`, `service`, and `receiver` elements beneath `application`.
- Preserve manifest order and omit all other components.
- Use `?` for a missing component name and `none` for a missing permission.
- Return zero on a successful scan and nonzero with a concise stderr message for input, XML, or output failures.

## Review Focus

- Android attributes are namespace-qualified by URI, regardless of the prefix used; Task 1 tests this through a normal `xmlns:android` manifest.
- A nested element containing an `intent-filter` must not make its enclosing component potential; Task 1 pins direct-child behavior.
- An empty result is a successful command with empty stdout; Task 1 tests this explicitly.
- A component outside `application` must not be reported; Task 1 includes one in the fixture.
- An unwritable output target, including a directory path, must fail cleanly without a traceback; Task 2 tests this boundary.

---

### Task 1: Component scanning and standard-output report

**Files:**
- Create: `manifest_exports.py`
- Create: `tests/test_manifest_exports.py`

**Interfaces:**
- Consumes: a manifest path supplied as the first CLI argument.
- Produces: `scan_manifest(root: xml.etree.ElementTree.Element) -> list[str]`, `format_component(status: str, component_type: str, element: Element) -> str`, and a CLI that prints result lines in manifest order.

- [ ] **Step 1: Write failing CLI tests for component classification and an empty result**

Add `ManifestExportsCliTests.test_reports_explicit_and_potential_components_in_manifest_order`. Run `python3 manifest_exports.py <fixture>` against a literal manifest containing all three supported types, explicit true/false values, an implicit component with a direct intent filter, a nested non-direct intent filter, missing name/permission values, and a component outside `application`. Assert exit code `0`, empty stderr, and these exact stdout lines:

```text
EXPORTED activity: com.example.MainActivity | permission: none
POTENTIALLY_EXPORTED service: com.example.SyncService | permission: com.example.BIND_SYNC
EXPORTED receiver: ? | permission: none
```

The production regression caught is reporting the wrong component/status, losing manifest order, mishandling Android namespaced attributes, or including an excluded element.

Also add `test_returns_success_with_empty_output_when_nothing_is_exported` using a manifest whose supported components are explicit false or have no export attribute and no direct intent filter. Assert code `0` and empty stdout/stderr. The regression caught is treating a valid empty report as an error or emitting excluded components.

- [ ] **Step 2: Run the classification test and verify RED**

Run: `python3 -m unittest tests.test_manifest_exports.ManifestExportsCliTests.test_reports_explicit_and_potential_components_in_manifest_order tests.test_manifest_exports.ManifestExportsCliTests.test_returns_success_with_empty_output_when_nothing_is_exported -v`

Expected: FAIL because `manifest_exports.py` does not exist.

- [ ] **Step 3: Implement the minimal scanner and stdout CLI**

Create `manifest_exports.py` with the signatures from the Interfaces block. Use `{http://schemas.android.com/apk/res/android}` attribute keys, direct-child lookup for `intent-filter`, and an `argparse` positional `manifest` argument. Limit traversal to the `application` element and the three specified component tags.

- [ ] **Step 4: Run the classification test and verify GREEN**

Run: `python3 -m unittest tests.test_manifest_exports.ManifestExportsCliTests.test_reports_explicit_and_potential_components_in_manifest_order tests.test_manifest_exports.ManifestExportsCliTests.test_returns_success_with_empty_output_when_nothing_is_exported -v`

Expected: PASS.

- [ ] **Step 5: Run the Task 1 tests**

Run: `python3 -m unittest tests.test_manifest_exports -v`

Expected: both tests PASS.

- [ ] **Step 6: Commit Task 1**

```bash
git add manifest_exports.py tests/test_manifest_exports.py
git commit -m "feat: scan exported Android components"
```

### Task 2: Output-file and failure handling

**Files:**
- Modify: `manifest_exports.py`
- Modify: `tests/test_manifest_exports.py`

**Interfaces:**
- Consumes: Task 1's report lines and CLI; optional `-o PATH`/`--output PATH`.
- Produces: `main(argv: list[str] | None = None) -> int`, file output with empty stdout, and concise nonzero failures for unreadable input, malformed XML, and output-write errors.

- [ ] **Step 1: Write failing output-file test**

Add `test_output_option_writes_report_to_file` with one explicit exported service. Invoke the CLI with `--output <temporary path>` and assert code `0`, empty stdout/stderr, and this exact file content including its final newline:

```text
EXPORTED service: com.example.SyncService | permission: none
```

The production regression caught is ignoring the output option, duplicating output to stdout, or omitting the final newline.

- [ ] **Step 2: Run the output-file test and verify RED**

Run: `python3 -m unittest tests.test_manifest_exports.ManifestExportsCliTests.test_output_option_writes_report_to_file -v`

Expected: FAIL because `--output` is not accepted.

- [ ] **Step 3: Implement optional file output**

Extend the argument parser with `-o`/`--output` and write the same assembled report to that path instead of stdout. Empty reports produce an empty file; nonempty reports end with one newline.

- [ ] **Step 4: Run the output-file test and verify GREEN**

Run: `python3 -m unittest tests.test_manifest_exports.ManifestExportsCliTests.test_output_option_writes_report_to_file -v`

Expected: PASS.

- [ ] **Step 5: Write failing tests for the three error classes**

Add these real CLI tests with literal assertions:

- `test_missing_input_fails_without_traceback`: missing path returns nonzero; stderr contains `error:` and no `Traceback`.
- `test_invalid_xml_fails_without_traceback`: malformed manifest returns nonzero; stderr contains `error:` and no `Traceback`.
- `test_output_directory_fails_without_traceback`: pass a directory to `--output`; return nonzero, stderr contains `error:` and no `Traceback`.

The production regressions caught are uncaught input, parse, and output exceptions.

- [ ] **Step 6: Run the error tests and verify RED**

Run: `python3 -m unittest tests.test_manifest_exports.ManifestExportsCliTests.test_missing_input_fails_without_traceback tests.test_manifest_exports.ManifestExportsCliTests.test_invalid_xml_fails_without_traceback tests.test_manifest_exports.ManifestExportsCliTests.test_output_directory_fails_without_traceback -v`

Expected: FAIL because at least one case emits a traceback or does not return a controlled error.

- [ ] **Step 7: Implement controlled errors in `main`**

Catch `OSError` around reads/writes and `xml.etree.ElementTree.ParseError` around parsing. Print `error: <concise detail>` to stderr and return `1`; invoke the entry point with `raise SystemExit(main())`.

- [ ] **Step 8: Run the full suite**

Run: `python3 -m unittest discover -v`

Expected: all tests PASS with no warnings or tracebacks.

- [ ] **Step 9: Exercise CLI help**

Run: `python3 manifest_exports.py --help`

Expected: exit code `0`; usage names the required manifest argument and optional `-o/--output` argument.

- [ ] **Step 10: Commit Task 2**

```bash
git add manifest_exports.py tests/test_manifest_exports.py
git commit -m "feat: add manifest scanner output and error handling"
```
