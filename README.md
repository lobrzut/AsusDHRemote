# ASUS Digital Home (DH) Remote — Windows 10 / 11

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue.svg)](#installation--setup)
[![Python](https://img.shields.io/badge/python-3.10%2B-green.svg)](#installation--setup)

[PL] Polski opis instalacji jest poniżej.

Lightweight background service that revives the legacy **ASUS Digital Home Remote Control** (XP/Vista era) on modern Windows. It maps remote buttons to media keys and custom commands, shows a system-tray icon, and ships a local web configurator that mirrors the physical remote layout.

**Hardware:** USB IR receiver `VID_1130` / `PID_CC00` (ASUS Digital Home).

---

## Features

- **Auto-connect** — reconnects when the USB IR receiver is plugged in
- **Debounce** — 250 ms filter; volume hold repeats at 150 ms
- **Global media keys** — Play/Pause, Prev/Next, Volume via scan codes (works with Jellyfin, Spotify, Chrome, etc.)
- **Web GUI** — local dashboard on `http://127.0.0.1:5555` matching the silver/amber remote
- **System tray** — open settings, toggle **Start with Windows**, view log, reload config, quit
- **Autostart** — enable/disable from the web GUI, tray menu, or the install/uninstall `.bat` helpers

---

## Installation & Setup

1. Install **Python 3.10+** (check **Add Python to PATH**).
2. In this folder:
   ```bash
   pip install -r requirements.txt
   ```
3. Optional autostart (any of these):
   - In the web GUI: toggle **Start with Windows**
   - Tray icon: check **Start with Windows**
   - Or double-click **`install_autostart.bat`** / **`uninstall_autostart.bat`**
4. Double-click **`open_gui.bat`** — starts the service, tray icon, and browser GUI.

First run creates a local `config.json` from `config.example.json` (your mappings stay on your machine and are gitignored).

### Console / debug

```bash
python asus_dh_service.py --console --gui
```

---

## File Structure

| File | Role |
|------|------|
| `asus_dh_service.py` | HID listener, local HTTP API, tray |
| `index.html` | Web configurator |
| `config.example.json` | Safe default mappings (committed) |
| `config.json` | Your local mappings (not committed) |
| `start_hidden.vbs` | Invisible background launcher |
| `open_gui.bat` | Start service + open GUI |
| `install_autostart.bat` / `uninstall_autostart.bat` | Startup registration |

---

## Button map (default)

| Code | Physical button | Default action |
|------|-----------------|----------------|
| `0x01` | Power | Show/Hide Desktop |
| `0x02` | Quick Power | Lock PC |
| `0x03` | Noise Off | Mute |
| `0x04` | WiFi | Open URL (Google) |
| `0x05` | AP Launch | Calculator |
| `0x06` | Maximize | Maximize/Restore window |
| `0x07` / `0x0B` | Vol + / − | Volume up / down |
| `0x08` / `0x0A` | Prev / Next | Media tracks |
| `0x09` | Play/Pause | Media play/pause |

---

## Security notes

- HTTP API binds to **127.0.0.1 only** (not exposed on the LAN).
- `run_command` actions execute locally as your user — only map programs you trust.
- Do not commit personal `config.json` paths or secrets.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: hid` | Use the same Python you installed deps into; `open_gui.bat` probes PATH for a working interpreter |
| Receiver not detected | Confirm Device Manager shows HID `VID_1130&PID_CC00`; try another USB port |
| Media keys do nothing | Focus a media app; some UWP players ignore global keys |
| Port 5555 in use | Close the other process or change the port in `asus_dh_service.py` |
| Autostart toggle fails / 404 | The web UI can refresh while an **old** service process is still running. Exit via tray → **Exit**, then run `open_gui.bat` again |
| Autostart not running | Enable **Start with Windows** in the GUI/tray, or re-run `install_autostart.bat`; check `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` |

---

## License

MIT — see [LICENSE](LICENSE). ASUS and Digital Home are trademarks of their respective owners; this is an unofficial community tool.

---

## [PL] Instrukcja

Narzędzie przywraca klasycznego pilota **ASUS Digital Home** na Windows 10/11: mapowanie przycisków, multimedia, własne komendy, ikona w zasobniku i panel WWW.

### Instalacja

1. Sklonuj repozytorium.
2. Zainstaluj **Python 3.10+** (zaznacz **Add Python to PATH**).
3. W folderze projektu:
   ```bash
   pip install -r requirements.txt
   ```
4. Opcjonalnie włącz autostart: przełącznik **Start with Windows** w GUI / tray, albo `install_autostart.bat`.
5. Uruchom **`open_gui.bat`** — usługa + przeglądarka na `http://127.0.0.1:5555`.

Przy pierwszym starcie powstanie lokalny `config.json` (nie jest commitowany). Naciśnij przycisk na pilocie — podświetli się na makiecie i przewinie listę mapowań.
