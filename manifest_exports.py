#!/usr/bin/env python3
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


ANDROID_ATTRIBUTE = "{{http://schemas.android.com/apk/res/android}}{}"
SUPPORTED_COMPONENTS = {"activity", "service", "receiver"}


def format_component(status: str, component_type: str, element: ET.Element) -> str:
    name = element.get(ANDROID_ATTRIBUTE.format("name"), "?")
    permission = element.get(ANDROID_ATTRIBUTE.format("permission"), "none")
    return f"{status} {component_type}: {name} | permission: {permission}"


def scan_manifest(root: ET.Element) -> list[str]:
    application = root.find("application")
    if application is None:
        return []

    results = []
    for element in application:
        component_type = element.tag
        if component_type not in SUPPORTED_COMPONENTS:
            continue

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

    try:
        root = ET.parse(arguments.manifest).getroot()
        lines = scan_manifest(root)
        report = "\n".join(lines) + ("\n" if lines else "")
        if arguments.output:
            Path(arguments.output).write_text(report, encoding="utf-8")
        else:
            print(report, end="")
    except (OSError, ET.ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
