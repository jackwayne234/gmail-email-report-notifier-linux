#!/usr/bin/env bash
set -euo pipefail
APP_NAME="Gmail Email Report / Notifier"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$APP_DIR/setup-prerequisites.log"
exec > >(tee -a "$LOG_FILE") 2>&1

ask_yes_no() {
  local question="$1"
  if command -v zenity >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    zenity --question --title="$APP_NAME setup" --text="$question" && return 0 || return 1
  fi
  printf '%s [y/N]: ' "$question"
  read -r ans || return 1
  case "$ans" in y|Y|yes|YES) return 0;; *) return 1;; esac
}

install_system_packages() {
  local packages=("$@")
  if [ "${#packages[@]}" -eq 0 ]; then return 0; fi
  echo "Need system packages: ${packages[*]}"
  if ! ask_yes_no "Install missing system packages for $APP_NAME?"; then exit 1; fi
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y "${packages[@]}"
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y "${packages[@]}"
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --needed --noconfirm "${packages[@]}"
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y "${packages[@]}"
  else
    echo "Unsupported package manager. Please install manually: ${packages[*]}"
    exit 1
  fi
}

missing=()
command -v python3 >/dev/null 2>&1 || missing+=(python3)
command -v notify-send >/dev/null 2>&1 || missing+=(libnotify-bin)
command -v sudo >/dev/null 2>&1 || { echo "sudo is missing. Please install prerequisites manually."; exit 1; }
install_system_packages "${missing[@]}"

if ! command -v himalaya >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/himalaya" ]; then
  echo "Himalaya email CLI was not found."
  echo "This app needs Himalaya configured with your Gmail/IMAP account before it can read headers."
  echo "Install/setup Himalaya from: https://github.com/pimalaya/himalaya"
  if command -v zenity >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    zenity --info --title="$APP_NAME setup" --text="Python/notifications are ready, but Himalaya was not found. Install and configure Himalaya before using this tool." || true
  fi
else
  echo "Himalaya found. Setup complete."
fi
