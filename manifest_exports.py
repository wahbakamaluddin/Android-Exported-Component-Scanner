#!/usr/bin/env python3
import argparse
import xml.etree.ElementTree as ET


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List exported components from an Android manifest."
    )
    parser.add_argument("manifest", help="path to AndroidManifest.xml")
    arguments = parser.parse_args()

    root = ET.parse(arguments.manifest).getroot()
    for line in scan_manifest(root):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
