# Justfile for Ice macOS project
# https://github.com/casey/just

# Default recipe to display available commands
default:
    @just --list

# Build the project in debug configuration
build:
    xcodebuild -project Ice.xcodeproj -scheme Ice -configuration Debug build

# Build the project in release configuration
build-release:
    xcodebuild -project Ice.xcodeproj -scheme Ice -configuration Release build

# Run the application
run:
    #!/bin/bash
    echo "Launching Ice.app..."
    DERIVED_DATA_PATH=$(just show-build-dir)
    APP_PATH="$DERIVED_DATA_PATH/Build/Products/Debug/Ice.app"
    if [ -d "$APP_PATH" ]; then
        if [ -f "$APP_PATH/Contents/MacOS/Ice" ]; then
            echo "✅ Launching Ice.app"
            open "$APP_PATH"
        else
            echo "❌ Executable missing at: $APP_PATH/Contents/MacOS/Ice"
            ls -la "$APP_PATH/Contents/MacOS/" 2>/dev/null || echo "MacOS directory missing"
        fi
    else
        echo "❌ App bundle not found at: $APP_PATH"
    fi

# Clean build artifacts
clean:
    xcodebuild -project Ice.xcodeproj -scheme Ice clean
    @echo "Build artifacts cleaned"

# Run SwiftLint on the project
lint:
    #!/bin/bash
    if command -v swiftlint >/dev/null 2>&1; then
        echo "Running SwiftLint..."
        swiftlint
    else
        echo "SwiftLint not installed. Install with: brew install swiftlint"
    fi

# Open the project in Xcode
xcode:
    open Ice.xcodeproj

# Show build products directory
show-build-dir:
    @find ~/Library/Developer/Xcode/DerivedData -name "Ice-*" -type d | head -1

# Install the app to /Applications (builds release version first)
install: build-release
    #!/bin/bash
    DERIVED_DATA_PATH=$(just show-build-dir)
    APP_PATH="$DERIVED_DATA_PATH/Build/Products/Release/Ice.app"
    if [ -d "$APP_PATH" ]; then
        echo "Installing Ice.app to /Applications..."
        sudo cp -R "$APP_PATH" /Applications/
        echo "✅ Ice.app installed successfully"
        echo "You can now launch Ice from Applications or Spotlight"
    else
        echo "❌ Release build not found at: $APP_PATH"
        echo "Make sure the release build completed successfully"
    fi

# Quick development cycle: clean, build, and run
dev: clean build run
