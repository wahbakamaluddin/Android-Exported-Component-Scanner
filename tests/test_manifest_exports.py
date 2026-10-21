import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "manifest_exports.py"


class ManifestExportsCliTests(unittest.TestCase):
    def run_cli(self, manifest: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            manifest_path = Path(temporary_directory) / "AndroidManifest.xml"
            manifest_path.write_text(manifest, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(manifest_path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_reports_explicit_and_potential_components_in_manifest_order(self):
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
    </application>
</manifest>
"""

        result = self.run_cli(manifest)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.stdout,
            "EXPORTED activity: com.example.MainActivity | permission: none\n"
            "POTENTIALLY_EXPORTED service: com.example.SyncService | permission: com.example.BIND_SYNC\n"
            "EXPORTED receiver: ? | permission: none\n",
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


if __name__ == "__main__":
    unittest.main()
