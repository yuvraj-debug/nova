# How Nova AI Now Understands Your Commands

## Examples: Before vs After

### Example 1: "Open Notepad"

#### BEFORE (❌ Broken)
```
User: "open notepad"
    ↓
Regex pattern match: "open X" 
    ↓
Problem: Could match as app opening OR search query
    ↓
Result: Might open Chrome and search for "notepad"
    ❌ WRONG BEHAVIOR
```

#### AFTER (✅ Fixed)
```
User: "open notepad"
    ↓
Sent to AI Plan with instruction:
    "Analyze what user wants and output ACTION lines"
    ↓
AI thinks:
    "notepad = local application
     User wants to open it
     ACTION: OPEN notepad"
    ↓
Nova executes:
    1. Check if "notepad" is local app → YES
    2. Call open_path("notepad")
    3. Opens Notepad.exe locally
    ✅ CORRECT BEHAVIOR
```

---

### Example 2: "Open ChatGPT"

#### BEFORE (❌ Inconsistent)
```
User: "open chatgpt"
    ↓
Regex checks... is it "open X"? Yes.
Is it "open X and search"? No.
Unclear what to do.
    ↓
Might treat as simple open command
    ↓
Result: Unpredictable behavior
```

#### AFTER (✅ Fixed)
```
User: "open chatgpt"
    ↓
Sent to AI Plan:
    "User said: open chatgpt"
    "Think step-by-step"
    ↓
AI thinks:
    "chatgpt = website (URL)
     User wants to open it
     ACTION: OPEN https://chatgpt.com"
    ↓
Nova executes:
    1. Check if "chatgpt.com" is URL → YES
    2. Open in browser using webbrowser.open()
    3. Opens ChatGPT in Chrome
    ✅ CORRECT BEHAVIOR
```

---

### Example 3: "Open ChatGPT and Click First Link"

#### BEFORE (❌ Not Supported)
```
User: "open chatgpt and click first link"
    ↓
Regex checks multiple patterns...
None of them match this exact compound command
    ↓
Falls back to conversational AI
    ↓
Result: Response like "I don't know how to do that"
    ❌ COMMAND IGNORED
```

#### AFTER (✅ Fixed)
```
User: "open chatgpt and click first link"
    ↓
Sent to AI Plan with examples:
    "OPEN <url>"
    "WAIT_FOR_PAGE"
    "CLICK <button>"
    ↓
AI thinks step-by-step:
    1. "User wants to open ChatGPT" → ACTION: OPEN https://chatgpt.com
    2. "Need to wait for page to load" → ACTION: WAIT_FOR_PAGE
    3. "Then click the first link" → ACTION: CLICK left
    ↓
Execution order:
    1. webbrowser.open("https://chatgpt.com")
    2. time.sleep(3)  # Wait for page
    3. pyautogui.click()  # Click mouse
    ✅ CORRECT MULTI-STEP BEHAVIOR
```

---

### Example 4: "Press Ctrl+C Then Alt+Tab Then Ctrl+V"

#### BEFORE (❌ Broken)
```
User: "press ctrl+c then alt+tab then ctrl+v"
    ↓
Press handler looks for "press X"
    ↓
Regex matches only first command: "press ctrl+c"
Rest is ignored
    ↓
Result: Only Ctrl+C is pressed
    ❌ INCOMPLETE EXECUTION
```

#### AFTER (✅ Fixed)
```
User: "press ctrl+c then alt+tab then ctrl+v"
    ↓
Sent to AI Plan:
    "User wants three keyboard actions"
    "Create ACTION line for each"
    ↓
AI thinks and outputs:
    ACTION: PRESS ctrl+c
    ACTION: PRESS alt+tab
    ACTION: PRESS ctrl+v
    ↓
Execution (step-by-step):
    1. pyautogui.hotkey('ctrl', 'c')     # Copy
    2. pyautogui.hotkey('alt', 'tab')    # Switch window
    3. pyautogui.hotkey('ctrl', 'v')     # Paste
    ✅ ALL THREE ACTIONS EXECUTE IN ORDER
```

---

### Example 5: "Open Notepad and Write a Letter"

#### BEFORE (❌ Not Supported)
```
User: "open notepad and write a letter"
    ↓
Regex patterns don't match this format
    ↓
Falls back to conversational AI
    ↓
Response: "I can't open applications and write content at the same time"
    ❌ COMMAND MISUNDERSTOOD
```

#### AFTER (✅ Fixed)
```
User: "open notepad and write a letter to editor"
    ↓
Sent to AI Plan with instruction:
    "Understand compound commands"
    "Generate content if needed"
    "Sequence the actions"
    ↓
AI thinks:
    1. "User wants to open notepad" → ACTION: OPEN notepad
    2. "Let it open" → ACTION: SLEEP 1
    3. "User wants content typed" → AI generates letter
    4. "Type the letter" → ACTION: TYPE [generated letter]
    ↓
Full output:
    ACTION: OPEN notepad
    ACTION: SLEEP 1
    ACTION: TYPE Dear Editor, I hope this letter finds you well...
              [AI generates 3-5 paragraph letter]
    ↓
Execution:
    1. subprocess.Popen(["notepad.exe"])  # Open app
    2. time.sleep(1)                       # Wait for app to load
    3. pyautogui.typewrite([letter])       # Type via clipboard
    ✅ COMPLETE WORKFLOW WITH AI-GENERATED CONTENT
```

---

## Key Differences in AI Understanding

### Smart Detection

#### Local Apps
```
AI recognizes:
- notepad, notepad.exe → Local app
- chrome, chromium → Browser app
- vs code, code → Editor
- cmd, powershell → Terminal

Behavior: Opens directly via open_path()
```

#### Web Apps/URLs
```
AI recognizes:
- chatgpt, chatgpt.com → Web URL
- google, google.com → Search engine
- instagram, instagram.com → Social media
- github.com/user/repo → Code repo

Behavior: Opens in browser via webbrowser.open()
```

#### Keyboard Actions
```
AI recognizes:
- Single keys: enter, tab, escape, backspace
- Modifiers: ctrl+, alt+, shift+
- Combinations: ctrl+c, alt+tab, ctrl+shift+n
- Sequences: ctrl+c then alt+tab then ctrl+v

Behavior: Uses pyautogui.hotkey() for combos
```

---

## AI Decision Tree

```
User Command: "..."
    ↓
Is it a meta command? (quit, language, time)
    ├─ YES → Handle immediately
    └─ NO → Continue
    ↓
Is it "search online"?
    ├─ YES → Search and show results
    └─ NO → Continue
    ↓
System control enabled?
    ├─ NO → Conversational AI only
    └─ YES → Try AI Plan Executor
    ↓
Send to AI with instruction:
    "Analyze this command and output ACTION lines"
    "Valid actions: OPEN, SEARCH, TYPE, PRESS, CLICK, etc."
    ↓
AI analyzes and outputs:
    ACTION: OPEN <target>
    ACTION: WAIT_FOR_PAGE
    ACTION: TYPE <text>
    ACTION: PRESS <keys>
    ACTION: CLICK <button>
    ↓
Nova parses each line and executes
    ↓
Success?
    ├─ YES → Done, skip conversational AI
    └─ NO → Fall back to conversational response
```

---

## How AI Planning Works

### The Instruction Nova Sends to AI

```python
"You are Nova's AI action executor. 
 Analyze the user's command and output a list of executable actions.
 Think step-by-step about what the user wants.

 Valid action types:
   OPEN <path/url/app> - Opens a file, folder, URL, or application
   SEARCH <query> - Searches in current browser (opens Chrome if needed)
   TYPE <text> - Types text into currently focused window
   PRESS <keys> - Presses keyboard keys (e.g., 'enter', 'ctrl+c', 'alt+tab')
   CLICK <button> - Clicks mouse button ('left', 'right', 'middle')
   SWITCH <app> - Switches to an open application
   SLEEP <seconds> - Wait/pause for specified seconds
   WAIT_FOR_PAGE - Wait 3 seconds for page to load

 Examples:
   User: 'open notepad'
   ACTION: OPEN notepad

   User: 'open chatgpt and click first link'
   ACTION: OPEN https://chatgpt.com
   ACTION: WAIT_FOR_PAGE
   ACTION: CLICK left

   User: 'press ctrl+c then alt+tab then ctrl+v'
   ACTION: PRESS ctrl+c
   ACTION: PRESS alt+tab
   ACTION: PRESS ctrl+v

 Output ONLY actions, one per line. No extra commentary."
```

### AI Response Format

AI learns to output only ACTION lines:

```
ACTION: OPEN notepad
ACTION: SLEEP 1
ACTION: TYPE Dear Friend, This is an automated letter...
```

Each line is parsed and executed independently.

---

## Execution Examples

### Example Execution: Open App + Type Content

```
Command: "nova open notepad and write a letter to my friend"

AI Plan Output:
    ACTION: OPEN notepad
    ACTION: SLEEP 1
    ACTION: TYPE Dear Friend, I hope this message finds you...
    [AI generates full letter]

Nova Execution:
    1. [EXECUTED] OPEN notepad
       → os.startfile("notepad.exe") / subprocess.Popen(["notepad"])
    
    2. [EXECUTED] SLEEP 1
       → time.sleep(1)
    
    3. [EXECUTED] TYPE Dear Friend, I hope...
       → Clipboard content: [letter]
       → PowerShell: Set-Clipboard
       → pyautogui.hotkey('ctrl', 'v')
    
Result: Notepad opens, letter is typed automatically
```

### Example Execution: Web Search + Click

```
Command: "nova open google and search for python and click first link"

AI Plan Output:
    ACTION: OPEN https://www.google.com
    ACTION: SLEEP 3
    ACTION: SEARCH python
    ACTION: WAIT_FOR_PAGE
    ACTION: CLICK left

Nova Execution:
    1. [EXECUTED] OPEN https://www.google.com
       → webbrowser.open("https://www.google.com")
    
    2. [EXECUTED] SLEEP 3
       → time.sleep(3)
    
    3. [EXECUTED] SEARCH python
       → webbrowser.open("https://www.google.com/search?q=python")
    
    4. [EXECUTED] WAIT_FOR_PAGE
       → time.sleep(3)
    
    5. [EXECUTED] CLICK left
       → pyautogui.click()

Result: Google opens, searches python, waits, clicks first result
```

---

## Memory Across Sessions

### Session 1
```
User: "nova open notepad"
Nova: Opens Notepad
Nova remembers: "User recently opened notepad"
Saved to nova_memory.json

User: "nova open chrome"
Nova: Opens Chrome
Nova remembers: "User opened notepad, then chrome"
Saved to nova_memory.json

User: "quit"
```

### Session 2 (Next Day)
```
Nova starts...
Loads nova_memory.json
Remembers previous session:
    - User opened notepad
    - Then opened chrome
    - Used for context

User: "nova open notepad"
Nova remembers context and opens notepad
Updated nova_memory.json
```

---

## Conclusion

The new Nova architecture is:

✅ **Intelligent** - AI makes decisions, not regex patterns  
✅ **Flexible** - Handles any command structure  
✅ **Reliable** - Step-by-step execution  
✅ **Powerful** - Complex workflows supported  
✅ **Maintainable** - Single AI decision point  
✅ **Extensible** - Easy to add new actions  

Commands work reliably because **AI understands intent**, not pattern matching!
