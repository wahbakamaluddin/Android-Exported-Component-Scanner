#!/usr/bin/env python3
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


ANDROID_ATTRIBUTE = "{{http://schemas.android.com/apk/res/android}}{}"
COMPONENT_ORDER = ("activity", "receiver", "service")
VERSION = "1.0.0"
AUTHOR = "w4hb4"
BANNER = r"""       ___    ______ ______ _____
      /   |  / ____// ____// ___/
     / /| | / __/  / /     \__ \
    / ___ |/ /___ / /___  ___/ /
   /_/  |_/_____/ \____/ /____/"""


def print_banner(stream) -> None:
    print(f"\033[96m{BANNER}\033[0m", file=stream)
    print(file=stream)
    print("      \033[92mAndroid Exported Component Scanner\033[0m", file=stream)
    print(
        f"              \033[96mv{VERSION}\033[0m \033[90m· by\033[0m "
        f"\033[92m{AUTHOR}\033[0m",
        file=stream,
    )
    print(file=stream)


def print_terminal_report(lines: list[str], stream) -> None:
    if not lines:
        print("  \033[92mNo exported components found.\033[0m", file=stream)
        return

    rows = []
    for line in lines:
        status, remainder = line.split(" ", 1)
        component_type, remainder = remainder.split(": ", 1)
        name, permission = remainder.rsplit(" | permission: ", 1)
        display_status = "POTENTIAL" if status == "POTENTIALLY_EXPORTED" else status
        rows.append((display_status, component_type, name, permission))

    component_width = max(30, *(len(name) for _, _, name, _ in rows))
    print("  \033[1;96mEXPORTED COMPONENTS\033[0m", file=stream)
    print(file=stream)
    print(
        f"  STATUS     TYPE      {'COMPONENT':<{component_width}}  PERMISSION",
        file=stream,
    )
    print(
        f"  ---------  --------  {'-' * component_width}  ------------------",
        file=stream,
    )
    for status, component_type, name, permission in rows:
        color = "\033[92m" if status == "EXPORTED" else "\033[93m"
        padded_status = f"{status:<9}"
        print(
            f"  {color}{padded_status}\033[0m  {component_type:<8}  "
            f"{name:<{component_width}}  {permission}",
            file=stream,
        )

    exported_count = sum(status == "EXPORTED" for status, *_ in rows)
    potential_count = len(rows) - exported_count
    component_label = "component" if len(rows) == 1 else "components"
    print(file=stream)
    print(
        f"  \033[96mSummary:\033[0m {len(rows)} {component_label} · "
        f"{exported_count} exported · {potential_count} potentially exported",
        file=stream,
    )


def format_component(status: str, component_type: str, element: ET.Element) -> str:
    name = element.get(ANDROID_ATTRIBUTE.format("name"), "?")
    permission = element.get(ANDROID_ATTRIBUTE.format("permission"), "none")
    return f"{status} {component_type}: {name} | permission: {permission}"


def scan_manifest(root: ET.Element) -> list[str]:
    application = root.find("application")
    if application is None:
        return []

    results = []
    for component_type in COMPONENT_ORDER:
        for element in application.findall(component_type):
            exported = element.get(ANDROID_ATTRIBUTE.format("exported"))
            if exported == "true":
                status = "EXPORTED"
            elif exported is None and element.find("intent-filter") is not None:
                status = "POTENTIALLY_EXPORTED"
            else:
                continue

            results.append(format_component(status, component_type, element))
    return results


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="List exported components from an Android manifest."
    )
    parser.add_argument("manifest", help="path to AndroidManifest.xml")
    parser.add_argument("-o", "--output", help="write the report to this file")
    arguments = parser.parse_args(argv)

    interactive_output = sys.stdout.isatty()
    if interactive_output:
        print_banner(sys.stdout)

    try:
        manifest_path = Path(arguments.manifest)
        root = ET.parse(manifest_path).getroot()
        output_path = Path(arguments.output) if arguments.output else None
        if output_path and output_path.resolve() == manifest_path.resolve():
            print("error: output path must differ from the manifest path", file=sys.stderr)
            return 1

        lines = scan_manifest(root)
        report = "\n".join(lines) + ("\n" if lines else "")
        if output_path:
            output_path.write_text(report, encoding="utf-8")
        elif interactive_output:
            print_terminal_report(lines, sys.stdout)
        else:
            print(report, end="")
    except (OSError, ET.ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
