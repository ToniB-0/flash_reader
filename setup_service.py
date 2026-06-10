#!/usr/bin/env python3
"""
setup_service.py — automatically installs the Flash Reader macOS Quick Action.

Run once:
    python3 setup_service.py

This will:
  1. Find the absolute path of this project
  2. Build a .workflow bundle (Automator Quick Action)
  3. Install it to ~/Library/Services/
  4. Print next steps
"""

import os
import sys
import stat
import textwrap

HERE        = os.path.dirname(os.path.abspath(__file__))
PYTHON      = sys.executable
HANDLER     = os.path.join(HERE, "service_handler.py")
SERVICE_DIR = os.path.expanduser("~/Library/Services")
SERVICE_NAME = "Flash Reader"
WORKFLOW_DIR = os.path.join(SERVICE_DIR, f"{SERVICE_NAME}.workflow")
CONTENTS_DIR = os.path.join(WORKFLOW_DIR, "Contents")
DOCUMENT_XML = os.path.join(CONTENTS_DIR, "document.wflow")


# The Automator workflow plist — reads selected text and pipes to our script
WORKFLOW_XML = textwrap.dedent(f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AMApplicationBuild</key>
    <string>521</string>
    <key>AMApplicationVersion</key>
    <string>2.10</string>
    <key>AMDocumentVersion</key>
    <string>2</string>
    <key>actions</key>
    <array>
        <dict>
            <key>action</key>
            <dict>
                <key>AMAccepts</key>
                <dict>
                    <key>Container</key>
                    <string>List</string>
                    <key>Optional</key>
                    <true/>
                    <key>Types</key>
                    <array>
                        <string>com.apple.cocoa.string</string>
                    </array>
                </dict>
                <key>AMActionVersion</key>
                <string>2.0.3</string>
                <key>AMApplication</key>
                <array>
                    <string>Automator</string>
                </array>
                <key>AMParameterProperties</key>
                <dict>
                    <key>COMMAND_STRING</key>
                    <dict/>
                    <key>CheckedForUserDefaultShell</key>
                    <dict/>
                    <key>inputMethod</key>
                    <dict/>
                    <key>shell</key>
                    <dict/>
                    <key>source</key>
                    <dict/>
                </dict>
                <key>AMProvides</key>
                <dict>
                    <key>Container</key>
                    <string>List</string>
                    <key>Types</key>
                    <array>
                        <string>com.apple.cocoa.string</string>
                    </array>
                </dict>
                <key>ActionBundlePath</key>
                <string>/System/Library/Automator/Run Shell Script.action</string>
                <key>ActionName</key>
                <string>Run Shell Script</string>
                <key>ActionParameters</key>
                <dict>
                    <key>COMMAND_STRING</key>
                    <string>"{PYTHON}" "{HANDLER}"</string>
                    <key>CheckedForUserDefaultShell</key>
                    <true/>
                    <key>inputMethod</key>
                    <integer>0</integer>
                    <key>shell</key>
                    <string>/bin/bash</string>
                    <key>source</key>
                    <string></string>
                </dict>
                <key>BundleIdentifier</key>
                <string>com.apple.RunShellScript</string>
                <key>CFBundleVersion</key>
                <string>2.0.3</string>
                <key>CanShowSelectedItemsWhenRun</key>
                <false/>
                <key>CanShowWhenRun</key>
                <true/>
                <key>Category</key>
                <array>
                    <string>AMCategoryUtilities</string>
                </array>
                <key>Class Name</key>
                <string>RunShellScriptAction</string>
                <key>InputUUID</key>
                <string>E94C5B33-1B43-4C63-9E87-EA1B7CA4ECF7</string>
                <key>Keywords</key>
                <array>
                    <string>Shell</string>
                    <string>Script</string>
                    <string>Command</string>
                    <string>Run</string>
                    <string>Unix</string>
                </array>
                <key>OutputUUID</key>
                <string>96F91A6D-1073-4F9C-B8B5-B0B3A3E4BAA2</string>
                <key>UUID</key>
                <string>7D6A37E4-5F10-4A21-9A34-6B0E7C8D9F12</string>
                <key>UnlockTimeout</key>
                <integer>0</integer>
                <key>arguments</key>
                <dict/>
                <key>isViewVisible</key>
                <integer>1</integer>
                <key>location</key>
                <string>309.500000:253.000000</string>
                <key>nibPath</key>
                <string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/English.lproj/main.nib</string>
            </dict>
            <key>isViewVisible</key>
            <integer>1</integer>
        </dict>
    </array>
    <key>connectors</key>
    <dict/>
    <key>workflowMetaData</key>
    <dict>
        <key>applicationBundleIDsByPath</key>
        <dict/>
        <key>applicationPaths</key>
        <array/>
        <key>inputTypeIdentifier</key>
        <string>com.apple.Automator.text</string>
        <key>outputTypeIdentifier</key>
        <string>com.apple.Automator.nothing</string>
        <key>presentationMode</key>
        <integer>15</integer>
        <key>processesInput</key>
        <integer>0</integer>
        <key>serviceInputTypeIdentifier</key>
        <string>com.apple.Automator.text</string>
        <key>serviceOutputTypeIdentifier</key>
        <string>com.apple.Automator.nothing</string>
        <key>serviceProcessesInput</key>
        <integer>0</integer>
        <key>systemImageName</key>
        <string>NSActionTemplate</string>
        <key>use64BitEnvironment</key>
        <integer>1</integer>
        <key>workflowTypeIdentifier</key>
        <string>com.apple.Automator.servicesMenu</string>
    </dict>
</dict>
</plist>
""")


def main():
    print(f"Installing Flash Reader service…")
    print(f"  Project: {HERE}")
    print(f"  Python:  {PYTHON}")
    print(f"  Service: {WORKFLOW_DIR}")
    print()

    os.makedirs(CONTENTS_DIR, exist_ok=True)

    with open(DOCUMENT_XML, "w", encoding="utf-8") as f:
        f.write(WORKFLOW_XML)

    # Make service_handler.py executable
    st = os.stat(HANDLER)
    os.chmod(HANDLER, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print("✓ Workflow installed.")
    print()
    print("Next steps:")
    print("  1. Open System Settings → Privacy & Security → Extensions → Services")
    print("     (or just: right-click any selected text in any app and look for")
    print('      "Flash Reader" under the Services submenu)')
    print("  2. If it doesn\'t appear, open Automator, open the file at:")
    print(f"     {WORKFLOW_DIR}")
    print("     and press ⌘R to confirm it runs, then save.")
    print()
    print("Keyboard shortcuts in the widget:")
    print("  Space       Play / Pause")
    print("  R           Restart")
    print("  ← / →       Step backward / forward one word")
    print("  ↑ / ↓       Speed +25 / −25 wpm")
    print("  Escape      Close")
    print()
    print("Done! Select any text, right-click → Services → Flash Reader.")


if __name__ == "__main__":
    main()
