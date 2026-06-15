#!/bin/bash

APP="$(dirname "$0")/Flash Reader.app"

echo "Removing quarantine..."
xattr -dr com.apple.quarantine "$APP" 2>/dev/null

echo "Opening Flash Reader..."
open "$APP"
