# Quick Testing Guide for Nova

## Start Nova
```powershell
cd "C:\Users\ys880\OneDrive\Desktop\test\test area"
python op.py
```

## Key Features Now Working

### 1. Smart App Opening
- **Say**: "nova open notepad"
- **Result**: Opens Notepad.exe (NOT in Chrome)
- **Why**: AI recognizes "notepad" as a local application

### 2. Web URL Opening
- **Say**: "nova open chatgpt"
- **Result**: Opens https://chatgpt.com in Chrome
- **Why**: AI recognizes "chatgpt" as a web application

### 3. Click Actions
- **Say**: "nova open chatgpt and click first link"
- **Result**: Opens ChatGPT, waits for page, then clicks
- **Why**: AI creates step-by-step action sequence with WAIT_FOR_PAGE

### 4. Keyboard Sequences
- **Say**: "nova press ctrl+c"
- **Result**: Copies selected text
- **Say**: "nova press alt+tab"
- **Result**: Switches window
- **Say**: "nova press ctrl+c then alt+tab then ctrl+v"
- **Result**: All three commands execute in sequence

### 5. App + Content Generation
- **Say**: "nova open notepad and write a letter to editor"
- **Result**: 
  1. Opens Notepad
  2. AI generates a letter
  3. Automatically types it in Notepad
- **Why**: AI understands compound commands with content generation

### 6. Online Search
- **Say**: "nova search python tutorials"
- **Result**: Opens Google search in Chrome
- **Say**: "nova search online artificial intelligence"
- **Result**: Shows summary + detailed results

### 7. Wake Word (if enabled)
- Say "nova" first to activate
- Then say your command
- Nova only listens after hearing wake word

## Configuration Checks

### Verify System Control is Enabled
```
In .env file, ensure:
- ENABLE_SYSTEM_CONTROL=true
- UNATTENDED_CONTROL=true
- WAKE_WORD_ENABLED=true
- WAKE_WORD=nova
```

### Check Memory is Working
- Look for `nova_memory.json` in the same directory as `op.py`
- This file stores conversation history (loads automatically on restart)

### Verify Speech Output
- If audio doesn't play, check: `SPEECH_ENABLED=true` in .env
- If you want silent mode: `SPEECH_ENABLED=false` (will only print)

## Debugging Tips

### If Command Doesn't Execute
1. Check console output for `[AI PLAN]` section - shows what AI decided to do
2. Look for `[EXECUTED]` messages - shows what actually ran
3. Check `[ACTION ERROR]` for any failures
4. If AI plan is empty, it means AI didn't recognize command as actionable

### To Debug a Specific Command
- Open `.env` and set: `DEFAULT_MODE=control`
- This ensures system control is always attempted first
- Speech will still work but is optional

### If pyautogui not available
- The tool will warn with `[PRESS ERROR] pyautogui not available`
- Make sure requirements.txt is installed: `pip install -r requirements.txt`

## Example Command Sequences

### Write and Email
```
"nova open notepad and write a thank you email"
[waits for notepad]
[generates email text]
[types it in notepad]
```

### Search and Click
```
"nova open google and search for python"
[opens Google]
[searches Python]
[waits for results]
```

### File Operations
```
"nova open file C:\Users\ys880\Documents\report.txt"
[opens that specific file]
```

### Browser Tabs
```
"nova open new tab"
[opens new browser tab]

"nova next tab"
[goes to next tab]

"nova close tab"
[closes current tab]
```

## Advanced Features

### Multi-Step Commands (Automatic)
Nova now understands complex requests like:
- "open notepad and write a poem"
- "open chrome and search for X then click first link"
- "press ctrl+c then alt+tab then ctrl+v"

The AI automatically:
1. Identifies all the actions needed
2. Generates content if needed
3. Executes step-by-step
4. Waits between actions (SLEEP/WAIT)

### Memory Persistence
- Every conversation is saved to `nova_memory.json`
- Memory loads automatically on restart
- Last 10 conversations kept (configurable via MEMORY_SIZE)
- This allows Nova to remember context across sessions

### Wake Word
- Say "nova" to activate listening
- Then immediately say your command
- Example: "nova open notepad"
- Everything after "nova" is treated as the command

## Emergency Controls

- **Ctrl+C**: Stop Nova immediately
- **Stop**: Say "stop" to cancel current action
- **Quit/Exit/Bye**: Say any of these to end conversation

## Troubleshooting

### No sound output?
- Check: `SPEECH_ENABLED=true` in .env
- If .env says `false`, Nova only prints (silent mode)

### Commands not executing?
- Ensure: `ENABLE_SYSTEM_CONTROL=true`
- Ensure: `UNATTENDED_CONTROL=true` (no confirmation needed)
- Check console for `[AI PLAN]` - if empty, AI didn't understand

### App opens in wrong place?
- Nova now uses AI to decide: local app vs web URL
- If wrong, try being more specific: "open notepad application" or "search google for X"

### Keys not being pressed?
- Ensure `pyautogui` is installed: `pip install pyautogui`
- Check console for `[PRESS ERROR]` messages

## Next Steps

1. Run: `python op.py`
2. Wait for wake word prompt (if enabled) or start speaking
3. Try the examples above
4. Check console for `[AI PLAN]` and `[EXECUTED]` messages
5. Monitor `nova_memory.json` for saved conversations

Enjoy your new AI assistant!
