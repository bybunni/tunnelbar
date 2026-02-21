.PHONY: install plist unplist app icns clean-app

PLIST_NAME := com.tunnelbar.agent
PLIST_DIR  := $(HOME)/Library/LaunchAgents
PLIST_FILE := $(PLIST_DIR)/$(PLIST_NAME).plist
PROJECT_DIR := $(shell pwd)
TUNNELBAR  := $(PROJECT_DIR)/.venv/bin/tunnelbar

install:
	uv sync

define PLIST_CONTENT
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$(PLIST_NAME)</string>
  <key>ProgramArguments</key>
  <array>
    <string>$(TUNNELBAR)</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StandardOutPath</key>
  <string>/tmp/tunnelbar.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/tunnelbar.err</string>
</dict>
</plist>
endef

export PLIST_CONTENT
plist: install
	@mkdir -p $(PLIST_DIR)
	@echo "$$PLIST_CONTENT" > $(PLIST_FILE)
	launchctl load $(PLIST_FILE)
	@echo "Tunnelbar plist installed and loaded."

unplist:
	-launchctl unload $(PLIST_FILE)
	-rm -f $(PLIST_FILE)
	@echo "Tunnelbar plist removed."

icns:
	bash scripts/make_icns.sh

app: icns
	uv sync --extra dev
	$(PROJECT_DIR)/.venv/bin/python setup.py py2app
	@echo "Built dist/Tunnelbar.app"

clean-app:
	-xattr -rc dist/ 2>/dev/null
	rm -rf build/ dist/ .eggs/
