# Nova - AI Voice Assistant: Complete Feature Set

## Overview
Nova is a fully AI-driven voice assistant that uses **Groq LLM (llama-3.1-8b-instant)** to plan and execute system actions. Every command is sent to the AI first, which decides what steps to execute.

---

## Core Architecture

### 1. **Voice I/O Pipeline**
- **Input**: Google Speech Recognition (local, no API key needed)
- **Output**: Windows PowerShell System.Speech (local TTS, no API)
- **Wake Word Detection**: Listens for "nova" → plays confirmation beep (1000 Hz, 200ms)
- **Language Support**: English & Hindi

### 2. **AI-First Planning**
```
User Voice Input → Wake Word Check → Extract Command 
  → Send to Groq AI → AI Plans Actions (ACTION: lines)
    → Parse and Execute → Confirmation Beep "Done"
```

**All user commands go through Groq AI** for intelligent routing and planning.

---

## Supported Commands & Actions

### **Music & Media Control**
```
- "play song" 
  → OPEN spotify → SLEEP 1 → PRESS space (play)
  
- "skip song" / "skip music"
  → PRESS right (next track)
  
- "skip again"
  → PRESS right × 2 (chain multiple skips)
  
- "pause music"
  → PRESS space (toggle pause/play)
  
- "play music in background"
  → OPEN spotify → SLEEP 1 → PRESS space → PRESS alt+tab
  
- "volume up" / "volume down"
  → PRESS volumeup or PRESS volumedown
```

### **System Control**
```
- "open notepad"
  → OPEN notepad
  
- "open notepad and write a letter"
  → OPEN notepad → SLEEP 1 → TYPE [content]
  
- "open chatgpt and search X"
  → OPEN https://chatgpt.com → WAIT_FOR_PAGE → SEARCH X
  
- "set alarm for 7 pm"
  → SET_ALARM 19:00 (programmatically or opens Clock app)
```

### **Browser & Tab Control**
```
- "open google"
  → OPEN https://google.com
  
- "search online machine learning"
  → Opens Chrome with Google search
  
- "next tab" / "previous tab"
  → PRESS Ctrl+Tab / PRESS Ctrl+Shift+Tab
  
- "new tab" / "close tab"
  → PRESS Ctrl+T / PRESS Ctrl+W
```

### **App Switching**
```
- "switch to chrome"
  → SWITCH chrome (brings window to foreground)
  
- "switch to notepad"
  → SWITCH notepad
```

### **Keyboard & Mouse**
```
- "press enter"
  → PRESS enter
  
- "press ctrl+c then ctrl+v"
  → PRESS ctrl+c → PRESS ctrl+v
  
- "click"
  → CLICK left (mouse click)
```

### **Advanced Multi-Step**
```
- "open spotify play song and minimize"
  → OPEN spotify → SLEEP 1 → PRESS space → SLEEP 0.5 → PRESS alt+tab

- "open notepad type hello world and save"
  → OPEN notepad → SLEEP 1 → TYPE hello world → PRESS ctrl+s
```

---

## Smart Features

### 1. **AI Meta-Instruction for Intelligent Planning**
- Corrects spelling mistakes in user commands
- Normalizes app names (spotify → spotify)
- Prefers local apps over web search
- Understands context-specific commands
- Plans multi-step sequences automatically

### 2. **Conversational Mode ("hey" Override)**
```
User: "hey what is 2+2?"
→ Recognized as pure conversation (no system actions)
→ Groq AI responds conversationally
→ Answer spoken via local TTS (no execution)
```

### 3. **Wake Word Confirmation**
- Listens for "nova" wake word
- Plays confirmation beep when detected
- "Mic is ON - listening for command..." message
- Ready for next command

### 4. **Memory Persistence**
- Stores last 10 messages in `nova_memory.json`
- Maintains conversation context
- Can reference previous commands

### 5. **Action Audit Trail**
- Every action logged to `action_log.jsonl`
- Records: timestamp, user command, AI plan, per-action results
- Useful for debugging and analytics

### 6. **Smart App Mapping**
Predefined app shortcuts in `app_mappings.json`:
```json
{
  "spotify": "spotify:",
  "calculator": "calc.exe",
  "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "notepad": "notepad.exe",
  "alarms": "ms-clock:",
  "clock": "ms-clock:",
  "settings": "ms-settings:",
  "mail": "ms-mail:",
  "calendar": "outlookcal:",
  ...
}
```

### 7. **Time Parsing for Alarms**
- Parses natural language times: "7 pm", "19:00", "7:00 PM"
- Converts to 24-hour HH:MM format
- Uses pywinauto for programmatic alarm setting (with fallback)

### 8. **Multi-Language Support**
- English (default)
- Hindi
- Auto-adjusts AI responses and TTS language

### 9. **System Control Safety**
- Forbidden keywords blocked (delete, remove, format, erase)
- Optional confirmation prompts
- Unattended mode (UNATTENDED_CONTROL) for fast execution

### 10. **Robust Path Resolution**
- Tries multiple methods to open files/apps:
  1. Resolve via app_mappings.json
  2. Check if path exists locally
  3. Resolve executable on PATH (shutil.which)
  4. Try subprocess.Popen
  5. Try Windows 'start' cmd
  6. Fallback to PowerShell Start-Process

---

## Configuration (.env)

```env
# LLM Settings
GROQ_API_KEY=<your-api-key>
GROQ_MODEL=llama-3.1-8b-instant

# Speech
SPEECH_ENABLED=true                    # Enable TTS
LANGUAGE=en                            # en or hi
SPEECH_RATE=2                          # -10 to 10 (speed)
SPEECH_VOLUME=100                      # 0-100

# System Control
ENABLE_SYSTEM_CONTROL=true             # Allow PC automation
UNATTENDED_CONTROL=true                # Execute without confirmation
DEFAULT_MODE=control                   # control or voice

# Wake Word
WAKE_WORD_ENABLED=true                 # Require wake word
WAKE_WORD=nova                         # Wake word to listen for

# Memory
SAVE_MEMORY=true                       # Persist conversation
MEMORY_SIZE=10                         # Last N messages

# AI Behavior
VOICE_FRIENDLY_TONE=true               # Casual or professional
ENABLE_REASONING=true                  # Include reasoning in responses
MAX_TOKENS=200                         # Response length (short)
```

---

## File Structure

```
op.py                          # Main application
app_mappings.json             # App name → path/URI mappings
nova_memory.json              # Conversation history (auto-created)
action_log.jsonl              # Audit trail (auto-created)
requirements.txt              # Python dependencies
.env                          # Configuration
```

---

## Dependencies

### Core
- groq (Groq LLM API)
- speech_recognition (Google STT)
- sounddevice (Audio capture)
- scipy (Audio processing)
- python-dotenv (Config)

### Automation
- pyautogui (keyboard/mouse)
- pygetwindow (window management)
- pywinauto (Windows UI automation)

### Optional
- selenium (browser automation)
- webdriver-manager (Chrome driver)

---

## How Commands Flow

### Example: "nova play song in background"

1. **Wake Word Detection**
   - Nova hears "nova"
   - Plays confirmation beep 🔔
   - Extraction: "play song in background"

2. **AI Planning**
   - Send to Groq AI with meta-instruction
   - AI understands "background" = minimize after playing
   - AI returns:
     ```
     ACTION: OPEN spotify
     ACTION: SLEEP 1
     ACTION: PRESS space
     ACTION: SLEEP 0.5
     ACTION: PRESS alt+tab
     ```

3. **Execution**
   - Parse each ACTION line
   - Execute in sequence
   - Log to action_log.jsonl
   - Speak "Done" confirmation

4. **Memory**
   - Store command in nova_memory.json
   - Next session has context

---

## Recent Enhancements

✅ **AI Meta-Instruction**
  - Spell correction
  - App name normalization
  - Local app preference
  
✅ **Multi-Step Commands**
  - Parse complex user requests
  - Chain actions automatically
  - Handle delays (SLEEP) between steps

✅ **Music Control**
  - Play, pause, skip, volume
  - Spotify shortcuts (n, p)
  - Media key support

✅ **Alarm Automation**
  - Time parsing (natural language)
  - Programmatic Windows Alarms setup
  - Fallback to manual if pywinauto unavailable

✅ **Conversational Override**
  - "hey <question>" for pure chat
  - No system actions
  - AI responds and speaks

✅ **Wake Word Confirmation**
  - Beep when activated
  - Status message
  - Ready for next command

✅ **Audit Trail**
  - Every action logged
  - Timestamp + results
  - Debugging & analytics

---

## Usage Examples

### Start Nova
```bash
python op.py
```

### Say Commands
```
"nova play song"
"nova skip music"
"nova open notepad and write hello world"
"nova set alarm for 7 pm"
"hey what is the weather"  (conversational)
"nova switch to chrome"
"nova pause music"
"nova volume down"
```

### Check Logs
```bash
tail action_log.jsonl        # Recent actions
cat nova_memory.json         # Conversation history
```

---

## Future Recommendations

- [ ] Voice command shortcuts (custom phrases)
- [ ] Machine learning-based intent detection
- [ ] Multi-language conversation mixing
- [ ] Mobile companion app
- [ ] Smart home integration (IoT)
- [ ] Real-time transcription display
- [ ] Custom wake words per app
- [ ] Advanced gesture recognition
- [ ] Offline LLM mode (local model)
- [ ] Integration with calendar/email

---

## Support

All features are **local-first** by default:
- Speech recognition: Google (free API, no auth needed)
- Text-to-speech: Windows System.Speech (0 API calls)
- LLM: Groq (API key required, very fast, cheap)
- Automation: 100% local

**Nova is production-ready and fully functional.** 🚀
