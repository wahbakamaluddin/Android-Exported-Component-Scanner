import contextlib
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import manifest_exports


SCRIPT = Path(__file__).resolve().parents[1] / "manifest_exports.py"


class TerminalBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


def strip_ansi(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", value)


class ManifestExportsCliTests(unittest.TestCase):
    def run_cli_path(
        self, manifest_path: Path, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(manifest_path), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def run_cli(self, manifest: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "AndroidManifest.xml"
            manifest_path.write_text(manifest, encoding="utf-8")
            return self.run_cli_path(manifest_path)

    def test_reports_components_in_activity_receiver_service_order(self):
        manifest = """\
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <service android:name="com.example.Outside" android:exported="true" />
    <application>
        <activity android:name="com.example.MainActivity"
                  android:exported="true" />
        <activity android:name="com.example.PrivateActivity"
                  android:exported="false" />
        <service android:name="com.example.SyncService"
                 android:permission="com.example.BIND_SYNC">
            <intent-filter>
                <action android:name="com.example.SYNC" />
            </intent-filter>
        </service>
        <service android:name="com.example.NestedFilterService">
            <meta-data>
                <intent-filter />
            </meta-data>
        </service>
        <receiver android:exported="true" />
        <receiver android:name="com.example.PrivateReceiver"
                  android:exported="false" />
        <service android:name="com.example.LaterService"
                 android:exported="true" />
    </application>
</manifest>
"""

        result = self.run_cli(manifest)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.stdout,
            "EXPORTED activity: com.example.MainActivity | permission: none\n"
            "EXPORTED receiver: ? | permission: none\n"
            "POTENTIALLY_EXPORTED service: com.example.SyncService | permission: com.example.BIND_SYNC\n"
            "EXPORTED service: com.example.LaterService | permission: none\n",
        )

    def test_returns_success_with_empty_output_when_nothing_is_exported(self):
        manifest = """\
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application>
        <activity android:name="com.example.PrivateActivity"
                  android:exported="false" />
        <service android:name="com.example.InternalService" />
    </application>
</manifest>
"""

        result = self.run_cli(manifest)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_interactive_terminal_displays_banner_and_results_table(self):
        manifest = """\
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application>
        <activity android:name="com.example.MainActivity"
                  android:exported="true" />
        <service android:name="com.example.SyncService"
                 android:permission="com.example.BIND_SYNC">
            <intent-filter />
        </service>
    </application>
</manifest>
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "AndroidManifest.xml"
            manifest_path.write_text(manifest, encoding="utf-8")
            output = TerminalBuffer()

            with contextlib.redirect_stdout(output):
                return_code = manifest_exports.main([str(manifest_path)])

        self.assertEqual(return_code, 0)
        self.assertIn("\033[96m", output.getvalue())
        self.assertIn("/   |  / ____// ____// ___/", output.getvalue())
        self.assertIn("Android Exported Component Scanner", output.getvalue())
        self.assertNotIn("manifest exposure finder", output.getvalue())
        self.assertIn("v1.0.0 · by w4hb4", strip_ansi(output.getvalue()))
        self.assertTrue(
            strip_ansi(output.getvalue()).endswith(
                "  EXPORTED COMPONENTS\n\n"
                "  STATUS     TYPE      COMPONENT                       PERMISSION\n"
                "  ---------  --------  ------------------------------  ------------------\n"
                "  EXPORTED   activity  com.example.MainActivity        none\n"
                "  POTENTIAL  service   com.example.SyncService         com.example.BIND_SYNC\n\n"
                "  Summary: 2 components · 1 exported · 1 potentially exported\n"
            )
        )

    def test_interactive_terminal_displays_clean_empty_result(self):
        manifest = """\
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application>
        <service android:name="com.example.InternalService"
                 android:exported="false" />
    </application>
</manifest>
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "AndroidManifest.xml"
            manifest_path.write_text(manifest, encoding="utf-8")
            output = TerminalBuffer()

            with contextlib.redirect_stdout(output):
                return_code = manifest_exports.main([str(manifest_path)])

        self.assertEqual(return_code, 0)
        self.assertTrue(
            strip_ansi(output.getvalue()).endswith(
                "  No exported components found.\n"
            )
        )

    def test_terminal_table_aligns_permissions_after_long_component_names(self):
        output = TerminalBuffer()
        manifest_exports.print_terminal_report(
            [
                "EXPORTED activity: .Main | permission: com.example.ACCESS",
                "EXPORTED service: com.example.feature.background.VeryLongServiceName | permission: com.example.ACCESS",
            ],
            output,
        )

        rows = [
            line
            for line in strip_ansi(output.getvalue()).splitlines()
            if "com.example.ACCESS" in line
        ]
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            rows[0].index("com.example.ACCESS"),
            rows[1].index("com.example.ACCESS"),
        )

    def test_terminal_summary_uses_singular_component(self):
        output = TerminalBuffer()

        manifest_exports.print_terminal_report(
            ["EXPORTED receiver: com.example.Receiver | permission: none"],
            output,
        )

        self.assertIn(
            "Summary: 1 component · 1 exported · 0 potentially exported",
            strip_ansi(output.getvalue()),
        )

    def test_output_option_writes_report_to_file(self):
        manifest = """\
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application>
        <service android:name="com.example.SyncService"
                 android:exported="true" />
    </application>
</manifest>
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            manifest_path = directory / "AndroidManifest.xml"
            output_path = directory / "report.txt"
            manifest_path.write_text(manifest, encoding="utf-8")

            result = self.run_cli_path(
                manifest_path, "--output", str(output_path)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "EXPORTED service: com.example.SyncService | permission: none\n",
            )

    def test_missing_input_fails_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.xml"

            result = self.run_cli_path(missing_path)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_xml_fails_without_traceback(self):
        result = self.run_cli("<manifest>")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_output_directory_fails_without_traceback(self):
        manifest = """\
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application>
        <receiver android:name="com.example.Receiver"
                  android:exported="true" />
    </application>
</manifest>
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            manifest_path = directory / "AndroidManifest.xml"
            manifest_path.write_text(manifest, encoding="utf-8")

            result = self.run_cli_path(
                manifest_path, "--output", str(directory)
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_output_cannot_overwrite_input_manifest(self):
        manifest = """\
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application>
        <activity android:name="com.example.MainActivity"
                  android:exported="true" />
    </application>
</manifest>
"""
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "AndroidManifest.xml"
            manifest_path.write_text(manifest, encoding="utf-8")

            result = self.run_cli_path(
                manifest_path, "--output", str(manifest_path)
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(manifest_path.read_text(encoding="utf-8"), manifest)


if __name__ == "__main__":
    unittest.main()
