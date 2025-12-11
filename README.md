# Nova - AI-Powered PC Control Assistant

Nova is an intelligent voice/text-controlled PC automation assistant powered by Groq's Llama AI. It listens to your commands and uses AI reasoning to execute complex system actions on your computer.

## Quick Start

### 1. Install Dependencies

```powershell
pip install -r .\requirements.txt
```

### 2. Run Nova

```powershell
python .\op.py
```

## How It Works

Nova operates in **Control-First Mode** by default:

1. **Listen for Commands** - Nova listens to voice input (or reads text input)
2. **AI Planning** - The command is sent to the AI with a **system control preprompt** that instructs it to analyze the command and produce a structured action plan
3. **Execute Actions** - Nova parses and executes the AI-generated actions:
   - `ACTION: OPEN <path/url>` - Opens an app or URL
   - `ACTION: SEARCH <query>` - Performs a search
   - `ACTION: TYPE <text>` - Types text (via clipboard paste)
   - `ACTION: PRESS <keys>` - Presses keyboard shortcuts (e.g., `ctrl+s`)
   - `ACTION: CLICK <button>` - Clicks the mouse
   - `ACTION: SWITCH <app>` - Switches to an app window
   - `ACTION: NEXT_TAB / PREV_TAB / NEW_TAB / CLOSE_TAB` - Browser tab control
   - `ACTION: SLEEP <seconds>` - Waits (for pages to load)

## Example Commands

```
"open notepad" → AI decides to open Notepad, not Chrome
"open instagram and search for reel" → Opens Instagram, navigates to reel page
"switch to chrome" → Brings Chrome window to focus
"type hello world" → Types text via clipboard paste
"play lo-fi beats on youtube" → Opens Chrome, searches YouTube, opens first result
```

## Configuration

Edit `.env` to customize behavior:

### Control-First Silent Mode (Recommended)
```
DEFAULT_MODE=control
SPEECH_ENABLED=false
ENABLE_SYSTEM_CONTROL=true
UNATTENDED_CONTROL=true
```

### With Voice Feedback
```
SPEECH_ENABLED=true
UNATTENDED_CONTROL=false  # Asks for confirmation on actions
```

### Custom AI Preprompt
Edit `CONTROL_PREPROMPT` in `.env` to change how the AI reasons about commands.

## Features

- **AI-Driven Automation**: Commands are analyzed by AI; no hardcoded rules
- **Multi-App Control**: Switch between apps, control tabs, type in focused windows
- **Smart URL Detection**: Recognizes spoken punctuation ("dot", "slash") and URLs
- **Silent Operation**: Runs without speaking (set `SPEECH_ENABLED=true` for voice feedback)
- **Memory**: Remembers last 10 commands for context
- **Unattended Mode**: Fully automatic execution (be careful with this!)
- **Fallback Support**: Uses Selenium (if installed) for robust web automation, falls back to keyboard shortcuts

## Safety Notes

- **`UNATTENDED_CONTROL=true`**: Nova executes actions without asking. Use only on trusted systems.
- **File Deletion Blocked**: Commands containing "delete", "remove", "erase" are always refused.
- **System Control**: Only works when `ENABLE_SYSTEM_CONTROL=true`.

## Troubleshooting

### Missing Dependencies
If you see import errors, install dependencies:
```powershell
pip install -r .\requirements.txt
```

### Window Switching Not Working
Install `pygetwindow` for better window detection:
```powershell
pip install pygetwindow
```

### Selenium Web Automation
For reliable Chrome/web automation, install:
```powershell
pip install selenium webdriver-manager
```

### Action Not Executing
- Check `.env` settings: `ENABLE_SYSTEM_CONTROL=true` and `UNATTENDED_CONTROL=true` (or set `UNATTENDED_CONTROL=false` to see confirmations)
- Run Nova and check the `[AI PLAN]` output to see what actions the AI suggested
- If actions show `[ACTION ERROR]`, check if the app is running or if the syntax is correct

## Files

- `op.py` - Main Nova assistant script
- `.env` - Configuration (API keys, behavior flags)
- `requirements.txt` - Python dependencies
- `app_mappings.json` - Maps app names to paths/URLs
- `nova_memory.json` - Optional persistent memory (auto-created)

## Commands & Shortcuts

- `stop` - Interrupt Nova (stop speaking)
- `quit` / `exit` - End Nova
- `switch to hindi` - Change language
- `switch to english` - Change language
- Ctrl+B - (future) Toggle between voice and chat mode

## Advanced: Customizing AI Behavior

### Change Model
Edit `.env`:
```
GROQ_MODEL=llama-3.1-70b-versatile  # Larger, slower, more capable
```

### Adjust Planning Detail
Edit `CONTROL_PREPROMPT` in `.env` to ask for more detailed plans or different action formats.

### Enable Logging
Add this to your `.env`:
```
ENABLE_ACTION_LOG=true
```
(Recommended for debugging unattended execution.)

## Legal & Ethical Notes

- Use Nova only on computers you own or have permission to control.
- Nova can execute commands that affect your system; use `UNATTENDED_CONTROL` cautiously.
- Respect privacy: Nova's AI processes your spoken/typed commands via Groq; review Groq's privacy policy.

---

**Nova** - Your intelligent PC assistant. Happy automation!
