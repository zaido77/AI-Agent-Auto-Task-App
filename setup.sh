#!/bin/bash
apt-get update && apt-get install -y chromium-browser

pip install playwright
playwright install

export PLAYWRIGHT_BROWSERS_PATH=0
