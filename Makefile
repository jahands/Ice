# Makefile for Ice macOS project

# Default target - show available targets
.DEFAULT_GOAL := help

# Variables for build paths
DERIVED_DATA_DIR := $(shell find ~/Library/Developer/Xcode/DerivedData -name "Ice-*" -type d | head -1)
DEBUG_APP := $(DERIVED_DATA_DIR)/Build/Products/Debug/Ice.app
RELEASE_APP := $(DERIVED_DATA_DIR)/Build/Products/Release/Ice.app
SOURCES := $(shell find Ice -name "*.swift" 2>/dev/null)

# Phony targets (commands that don't create files with matching names)
.PHONY: help run clean lint xcode show-build-dir install dev

# Show available targets
help:
	@echo "Available targets:"
	@echo "  build         - Build the project in debug configuration"
	@echo "  build-release - Build the project in release configuration"
	@echo "  run           - Build and launch the Ice.app"
	@echo "  clean         - Clean build artifacts"
	@echo "  lint          - Run SwiftLint on the project"
	@echo "  xcode         - Open the project in Xcode"
	@echo "  show-build-dir - Display the DerivedData build directory"
	@echo "  install       - Build release version and install to /Applications"
	@echo "  dev           - Development cycle (clean, build, run)"

# Build the debug app (real target with dependencies)
$(DEBUG_APP): $(SOURCES) Ice.xcodeproj/project.pbxproj
	xcodebuild -project Ice.xcodeproj -scheme Ice -configuration Debug build

# Build the release app (real target with dependencies)
$(RELEASE_APP): $(SOURCES) Ice.xcodeproj/project.pbxproj
	xcodebuild -project Ice.xcodeproj -scheme Ice -configuration Release build

# Convenience targets
build: $(DEBUG_APP)

build-release: $(RELEASE_APP)

# Run the application
run: $(DEBUG_APP)
	@echo "Launching Ice.app..."
	@if [ -f "$(DEBUG_APP)/Contents/MacOS/Ice" ]; then \
		echo "✅ Launching Ice.app"; \
		open "$(DEBUG_APP)"; \
	else \
		echo "❌ Executable missing at: $(DEBUG_APP)/Contents/MacOS/Ice"; \
		ls -la "$(DEBUG_APP)/Contents/MacOS/" 2>/dev/null || echo "MacOS directory missing"; \
	fi

# Clean build artifacts
clean:
	xcodebuild -project Ice.xcodeproj -scheme Ice clean
	@echo "Build artifacts cleaned"

# Run SwiftLint on the project
lint:
	@if command -v swiftlint >/dev/null 2>&1; then \
		echo "Running SwiftLint..."; \
		swiftlint; \
	else \
		echo "SwiftLint not installed. Install with: brew install swiftlint"; \
	fi

# Open the project in Xcode
xcode:
	open Ice.xcodeproj

# Show build products directory
show-build-dir:
	@find ~/Library/Developer/Xcode/DerivedData -name "Ice-*" -type d | head -1

# Install the app to /Applications (builds release version first)
install: $(RELEASE_APP)
	@echo "Installing Ice.app to /Applications..."
	@if [ -d "/Applications/Ice.app" ]; then \
		echo "Removing existing Ice.app..."; \
		sudo rm -rf "/Applications/Ice.app"; \
	fi
	@sudo ditto "$(RELEASE_APP)" "/Applications/Ice.app"
	@echo "✅ Ice.app installed successfully"
	@echo "You can now launch Ice from Applications or Spotlight"

# Quick development cycle: clean, build, and run
dev: clean build run
