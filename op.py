#!/usr/bin/env python3
"""
Nova - AI Assistant with Voice I/O, Online Search & Hindi Support
Features:
- Continuous voice conversation mode (natural flow like talking to a friend)
- Hindi & English language support
- Real-time online search (news, information)
- Google Custom Search or DuckDuckGo fallback
- Natural language responses
"""

import os
import sys
import threading
import subprocess
import time
import io
import json
import speech_recognition as sr
import sounddevice as sd
import scipy.io.wavfile as wavfile
import numpy as np
import requests
import urllib.parse
from dotenv import load_dotenv
from groq import Groq
import webbrowser
import re


def safe_search(pattern, string, flags=0):
    try:
        return re.search(pattern, string, flags=flags)
    except re.error as e:
        print(f"[REGEX ERROR] search pattern '{pattern}': {e}")
        return None


def safe_sub(pattern, repl, string, flags=0):
    try:
        return re.sub(pattern, repl, string, flags=flags)
    except re.error as e:
        print(f"[REGEX ERROR] sub pattern '{pattern}': {e}")
        return string
import tempfile
import shutil

# Optional Selenium for robust web automation
try:
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_SELENIUM = True
except Exception:
    HAS_SELENIUM = False
    webdriver = None

# Optional automation library for mouse/keyboard control
try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    HAS_PYAUTOGUI = False

# Optional window utilities for focusing windows
try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except Exception:
    HAS_PYGETWINDOW = False

# Optional Windows UI automation for reliable app control (Alarms, etc.)
try:
    from pywinauto import Application, Desktop
    HAS_PYWINAUTO = True
except Exception:
    HAS_PYWINAUTO = False

# Current UI/system context (last opened app key from app_mappings.json)
CURRENT_APP_CONTEXT = None
LAST_OPENED_TARGET = None
# Current UI/system context (last opened app key from app_mappings.json)
CURRENT_APP_CONTEXT = None
LAST_OPENED_TARGET = None

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()

# Default behavior: control-first unless user overrides
DEFAULT_MODE = os.getenv('DEFAULT_MODE', 'control')
# If SPEECH_ENABLED is false, Nova will not speak aloud (prints only)
SPEECH_ENABLED = os.getenv('SPEECH_ENABLED', 'false').lower() in ['1', 'true', 'yes']


def system_control_enabled():
    env = os.getenv('ENABLE_SYSTEM_CONTROL')
    if env is None:
        return True if DEFAULT_MODE == 'control' else False
    return env.lower() in ['1', 'true', 'yes']


def unattended_enabled():
    env = os.getenv('UNATTENDED_CONTROL')
    if env is None:
        return True if DEFAULT_MODE == 'control' else False
    return env.lower() in ['1', 'true', 'yes']

# Control preprompt sent to AI when system control is involved. Can be overridden in .env
CONTROL_PREPROMPT = os.getenv('CONTROL_PREPROMPT',
    "You are Nova's system-control planner. When given a user request, produce a short, numbered plan (3-6 steps) of concrete system actions to perform."
)

# Wake word configuration
WAKE_WORD_ENABLED = os.getenv('WAKE_WORD_ENABLED', 'true').lower() in ['1', 'true', 'yes']
WAKE_WORD = os.getenv('WAKE_WORD', 'nova').lower().strip()

# Memory configuration
MEMORY_SIZE = int(os.getenv('MEMORY_SIZE', '10'))
SAVE_MEMORY = os.getenv('SAVE_MEMORY', 'false').lower() in ['1', 'true', 'yes']
MEMORY_FILE = os.path.join(os.path.dirname(__file__), 'nova_memory.json')

# Action log for audit trail
ACTION_LOG_FILE = os.path.join(os.path.dirname(__file__), 'action_log.jsonl')

# Global flags
stop_speaking = False
is_speaking = False

def speak(text, language='en', rate=0, volume=100):
    """
    Text-to-speech using Windows PowerShell
    Supports English and Hindi
    """
    global stop_speaking, is_speaking
    stop_speaking = False
    is_speaking = True
    # If speech is disabled, only print the text and return
    if not SPEECH_ENABLED:
        print("\n[SPEAKING DISABLED] ", text, flush=True)
        is_speaking = False
        return
    
    try:
        # Split sentences for better control
        sentences = [s.strip() for s in text.replace('!', '.').split('.') if s.strip()]
        print("\n[SPEAKING]", flush=True)
        
        for sentence in sentences:
            if stop_speaking:
                print("[STOPPED]", flush=True)
                break
            
            if not sentence:
                continue
            
            safe_sentence = sentence.replace("'", "''")
            
            # PowerShell command for TTS
            # Optionally select a voice name from env: VOICE_NAME
            voice_name = os.getenv('VOICE_NAME', '').strip()
            select_voice = f"$speak.SelectVoice('{voice_name}')\n" if voice_name else ""
            # Use SpeakSsml for better control if needed; here we use Speak with choices
            ps_command = f"""
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Rate = {rate}
$speak.Volume = {volume}
{select_voice}$speak.Speak('{safe_sentence}')
"""
            
            try:
                process = subprocess.Popen(
                    ["powershell", "-Command", ps_command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
            
            time.sleep(0.1)
        
        is_speaking = False
    
    except Exception as e:
        is_speaking = False
        print(f"[SPEAK ERROR] {e}")

def search_duckduckgo(query):
    """
    Search using DuckDuckGo Instant Answer API
    Returns: List of results with title, snippet, and link
    """
    try:
        print("[SEARCHING] Finding information...", flush=True)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        
        # DuckDuckGo Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_redirect': 1,
            'no_html': 1
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            # Get abstract/summary
            if data.get('AbstractText'):
                results.append({
                    'title': data.get('Heading', 'Result'),
                    'snippet': data.get('AbstractText', ''),
                    'source': 'DuckDuckGo'
                })
            
            # Get related topics
            for topic in data.get('RelatedTopics', [])[:3]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append({
                        'title': topic.get('FirstURL', topic.get('Icon', {}).get('URL', 'Result')),
                        'snippet': topic.get('Text', '')[:150],
                        'source': 'DuckDuckGo'
                    })
            
            return results if results else None
    
    except Exception as e:
        print(f"[SEARCH ERROR] {e}", flush=True)
    
    return None

def search_google_custom(query):
    """
    Search using Google Custom Search API
    """
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not api_key or not search_engine_id:
            return None
        
        print("[SEARCHING] Using Google Custom Search...", flush=True)
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': query,
            'key': api_key,
            'cx': search_engine_id,
            'num': 3
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', '')[:150],
                    'link': item.get('link', ''),
                    'source': 'Google'
                })
            
            return results if results else None
    
    except Exception as e:
        print(f"[GOOGLE SEARCH ERROR] {e}", flush=True)
    
    return None

def do_search(query):
    """
    Perform online search - tries Google first, falls back to DuckDuckGo
    """
    # Try Google first if configured
    results = search_google_custom(query)
    
    # Fallback to DuckDuckGo
    if not results:
        results = search_duckduckgo(query)
    
    return results


def get_current_time(language='en'):
    """Return current local time as a short string, formatted per language."""
    from datetime import datetime
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    # Format HH:MM without leading zero
    hh = str(hour).lstrip('0') or '0'
    mm = f"{minute:02d}"
    if language == 'hi':
        # Simple Hindi phrasing (minimal words)
        return f"{hh}:{mm}"
    else:
        # English 24-hour numeric time (user wanted minimal response)
        return f"{hh}:{mm}"

def get_voice_input(language='en', duration=10):
    """
    Capture voice input using sounddevice + Google Speech Recognition
    Supports English and Hindi
    """
    recognizer = sr.Recognizer()
    
    try:
        print("[LISTENING] Speak now...", flush=True)
        
        sample_rate = 16000
        
        # Record audio
        audio_data = sd.rec(int(sample_rate * duration), samplerate=sample_rate, channels=1, dtype='float32')
        sd.wait()
        
        # Convert to 16-bit PCM
        audio_data = (audio_data * 32767).astype(np.int16)
        audio = sr.AudioData(audio_data.tobytes(), sample_rate, 2)
        
        print("[PROCESSING] Converting speech to text...", flush=True)
        
        # Google Speech Recognition with language support
        if language == 'hi':
            text = recognizer.recognize_google(audio, language='hi-IN')
        else:
            text = recognizer.recognize_google(audio, language='en-US')
        
        print(f"[YOU] {text}", flush=True)
        return text
    
    except sr.UnknownValueError:
        print("[ERROR] Couldn't understand. Please speak again.", flush=True)
        return None
    except sr.RequestError as e:
        print(f"[ERROR] Speech service error: {e}", flush=True)
        return None
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        return None

def create_nova():
    """Initialize Groq client"""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")
    return Groq(api_key=api_key)

def get_ai_response(client, messages, language='en', preprompt=None):
    """
    Get response from Groq AI
    Automatically responds in the same language as input
    """
    model = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
    temperature = float(os.getenv('TEMPERATURE', '0.7'))
    max_tokens = int(os.getenv('MAX_TOKENS', '200'))
    top_p = float(os.getenv('TOP_P', '1'))
    
    # Build dynamic system prompt based on environment settings
    friendly = os.getenv('VOICE_FRIENDLY_TONE', 'true').lower() in ['1', 'true', 'yes']
    enable_reasoning = os.getenv('ENABLE_REASONING', 'false').lower() in ['1', 'true', 'yes']
    tone_instr = "Be casual, friendly, and talk like a helpful friend." if friendly else "Be professional and concise."
    # If reasoning is enabled, allow a single short 'Reason:' sentence. Otherwise explicitly forbid any chain-of-thought.
    if enable_reasoning:
        reasoning_instr = " After your short answer, include one brief sentence labeled 'Reason:' explaining your reasoning in one line. Do NOT reveal internal chain-of-thought beyond this." 
    else:
        reasoning_instr = " Do NOT provide chain-of-thought, internal reasoning, or 'Reason:' lines. Only provide the short final answer."

    system_content = (
        f"You are Nova, a helpful AI assistant. Keep responses SHORT (1-2 sentences). {tone_instr}{reasoning_instr} "
        f"Respond in {'Hindi' if language == 'hi' else 'English'}."
    )
    # If a preprompt is provided, include it before the system content to guide the model
    if preprompt:
        system_content = preprompt + "\n" + system_content

    system_prompt = {"role": "system", "content": system_content}

    # Build message list
    msg_list = [system_prompt]
    msg_list.extend(messages)
    
    completion = client.chat.completions.create(
        model=model,
        messages=msg_list,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        top_p=top_p,
        stream=True,
        stop=None
    )
    
    # Stream response
    full_response = ""
    print("[NOVA] ", end="", flush=True)
    
    for chunk in completion:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    
    print()
    return full_response


def generate_long_text(client, prompt_text, language='en'):
    """Generate longer-form content (stories, novels, essays) using the AI model.
    Respects environment variable LONG_MAX_TOKENS for size (default 800).
    """
    model = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
    temperature = float(os.getenv('TEMPERATURE', '0.7'))
    long_max = int(os.getenv('LONG_MAX_TOKENS', '800'))

    system_content = (
        f"You are Nova, a creative writing assistant. Produce a polished, multi-paragraph piece based on the user's request. "
        f"Keep content coherent and in the user's language ({'Hindi' if language=='hi' else 'English'}). Do NOT include meta commentary or 'Reason:' lines."
    )
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": prompt_text}
    ]

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=long_max,
        stream=False
    )

    # Non-streamed response
    text = ''
    try:
        text = completion.choices[0].message.content
    except Exception:
        # fallback: try streaming concatenation
        for chunk in completion:
            if chunk.choices[0].delta.content:
                text += chunk.choices[0].delta.content

    return text.strip()


def execute_via_ai_plan(client, user_command, language='en'):
    """
    Universal executor: Ask AI to plan and output executable actions for any user command.
    The AI will produce a structured plan that Nova then executes.
    Returns True if execution succeeded or was attempted.
    """
    global CURRENT_APP_CONTEXT, LAST_OPENED_TARGET

    if not system_control_enabled():
        return False

    try:
        # Build a meta-instruction for the AI: analyze the command and output executable actions
        meta_instruction = (
            f"You are Nova's AI action executor. Analyze the user's command and output a list of executable actions.\n"
            f"THINK STEP-BY-STEP: Break down complex commands into logical sub-actions.\n"
            f"\n"
            f"MUSIC & MEDIA EXAMPLES:\n"
            f"- 'play music' or 'play song' → OPEN spotify → SLEEP 1 → PRESS space (to play, stays visible)\n"
            f"- 'play music in background' → OPEN spotify → SLEEP 1 → PRESS space → PRESS alt+tab (to minimize/background)\n"
            f"- 'skip song' or 'skip music' → PRESS right (next track) or PRESS n (Spotify shortcut)\n"
            f"- 'pause music' → PRESS space (pause/play toggle)\n"
            f"- 'volume up' → PRESS volumeup\n"
            f"- 'volume down' → PRESS volumedown\n"
            f"\n"
            f"YOUTUBE & WEB EXAMPLES:\n"
            f"- 'play video on youtube' or 'youtube video':\n"
            f"ACTION: YOUTUBE_PLAY song name\n"
            f"\n"
            f"- 'youtube play in background':\n"
            f"ACTION: YOUTUBE_PLAY song name\n"
            f"ACTION: PRESS alt+tab\n"
            f"\n"
            f"OTHER EXAMPLES:\n"
            f"- 'open notepad and write' → OPEN notepad → SLEEP 1 → TYPE the content\n"
            f"- 'set alarm for 7 pm' → SET_ALARM 19:00\n"
            f"- 'open chatgpt and click' → OPEN https://chatgpt.com → WAIT_FOR_PAGE → CLICK left\n"
            f"\n"
            f"Format each action as a single line starting with ACTION: followed by the type and parameters.\n"
            f"\n"
            f"Valid action types:\n"
            f"  OPEN <path/url/app> - Opens a file, folder, URL, or application\n"
            f"  SEARCH <query> - Searches in current browser (opens Chrome if needed)\n"
            f"  TYPE <text> - Types text into currently focused window\n"
            f"  PRESS <keys> - Presses keyboard keys (space, enter, right, left, volumeup, volumedown, etc.)\n"
            f"    Media keys: 'space' (play/pause), 'right' or 'n' (next), 'left' or 'p' (previous)\n"
            f"    Volume: 'volumeup', 'volumedown'\n"
            f"    Combinations: 'ctrl+c', 'alt+tab', 'ctrl+v', etc.\n"
            f"  CLICK <button> - Clicks mouse button ('left', 'right', 'middle')\n"
            f"  SWITCH <app> - Switches to an open application\n"
            f"  NEXT_TAB - Ctrl+Tab to next browser tab\n"
            f"  PREV_TAB - Ctrl+Shift+Tab to previous browser tab\n"
            f"  NEW_TAB - Ctrl+T to open new browser tab\n"
            f"  CLOSE_TAB - Ctrl+W to close current browser tab\n"
            f"  SET_ALARM <HH:MM or time string> - Set an alarm (e.g., '19:00' or '7:00 PM')\n"
            f"  YOUTUBE_PLAY <video name/query> - Search YouTube and play first result (auto-plays instantly)\n"
            f"  SLEEP <seconds> - Wait/pause for specified seconds\n"
            f"  WAIT_FOR_PAGE - Wait 3 seconds for page to load\n"
            f"\n"
            f"OUTPUT RULES:\n"
            f"- MANDATORY: Output ONLY ACTION lines, NOTHING ELSE\n"
            f"- Do NOT include 'Reason:', explanations, reasoning, or any text after actions\n"
            f"- Do NOT output arrows (→), examples, or commentary\n"
            f"- EVERY action MUST be on a new line and start with 'ACTION:'\n"
            f"- ALWAYS add SLEEP or WAIT_FOR_PAGE after OPEN (use SLEEP 3 for web URLs, SLEEP 1 for apps)\n"
            f"- Add SLEEP 0.5 between TYPE and PRESS enter for page interaction\n"
            f"- For YouTube: After PRESS enter (search), add SLEEP 2, then CLICK left (first video), SLEEP 2, then CLICK left (play video)\n"
            f"- IMPORTANT: Only add PRESS alt+tab if user explicitly says 'background' or 'minimize'\n"
            f"- For media/music: assume the media player or Spotify is already focused when user says 'skip', 'pause', etc.\n"
            f"- If user says 'skip again' or 'skip more', chain multiple PRESS right actions\n"
        )

        # Encourage the AI to correct minor spelling mistakes, normalize app names,
        # and prefer local applications when appropriate (e.g., alarms -> Windows Alarms & Clock).
        # This makes the AI more robust to user typos and ambiguous phrases.
        # Also hint about common music commands and background operations.
        meta_instruction = (
            "Correct any minor spelling mistakes in the user's command, normalize app names, and prefer opening local applications when appropriate.\n"
            "For music commands (play, pause, stop, skip), use spotify: if available, else assume music player is open.\n"
            "For background operations, use PRESS alt+tab or PRESS alt+f9 (minimize) after the main action.\n"
            + meta_instruction
        )

        messages = [{"role": "user", "content": user_command}]
        plan_text = get_ai_response(client, messages, language, preprompt=meta_instruction)

        # Prepare audit log entry
        log_entry = {
            "timestamp": time.time(),
            "user_command": user_command,
            "plan": plan_text,
            "actions": []
        }

        # Parse and execute actions
        print(f"[AI PLAN]\n{plan_text}\n")
        actions_executed = 0
        for line in plan_text.splitlines():
            line = line.strip()
            if not line.lower().startswith('action:'):
                continue

            action_str = line[7:].strip()  # Remove 'ACTION:' prefix
            parts = action_str.split(None, 1)
            if not parts:
                continue

            action_type = parts[0].upper()
            action_param = parts[1] if len(parts) > 1 else ""

            # Execute the action
            try:
                if action_type == "OPEN":
                    # Parse URL or path from param
                    target = action_param.strip('"\'')
                    # Special-case: if user or AI referenced alarms/clock, open Windows Alarms & Clock
                    if target and any(k in target.lower() for k in ['alarm', 'alarms', 'clock']):
                        try:
                            # Use Windows URI to open Alarms & Clock
                            subprocess.Popen(['cmd', '/c', 'start', '', 'ms-clock:'], shell=True)
                            CURRENT_APP_CONTEXT = 'alarm'
                            LAST_OPENED_TARGET = 'ms-clock:'
                            actions_executed += 1
                            print(f"[EXECUTED] OPEN ms-clock:")
                            continue
                        except Exception as e:
                            print(f"[OPEN ALARM ERROR] {e}")
                            # fallthrough to other attempts
                    # Determine if it's a local app, path, or URL
                    is_url = is_likely_url(target)
                    is_local_app = target.lower() in ['notepad', 'notepad.exe', 'chrome', 'firefox', 'edge', 'vs code', 'code', 'explorer', 'cmd', 'powershell']
                    
                    if is_url or target.startswith('http'):
                        # It's a URL, open in Chrome
                        if HAS_SELENIUM and not target.endswith('.com'):
                            try:
                                options = webdriver.ChromeOptions()
                                options.add_argument('--new-window')
                                driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
                                driver.get(target)
                                CURRENT_APP_CONTEXT = 'chrome'
                                actions_executed += 1
                                print(f"[EXECUTED] OPEN {target}")
                            except Exception as e:
                                # Fallback to webbrowser
                                webbrowser.open(target)
                                CURRENT_APP_CONTEXT = 'chrome'
                                actions_executed += 1
                                print(f"[EXECUTED] OPEN {target}")
                        else:
                            webbrowser.open(target)
                            CURRENT_APP_CONTEXT = 'chrome'
                            actions_executed += 1
                            log_entry['actions'].append({
                                'action': 'OPEN', 'target': target, 'result': 'opened_in_browser'
                            })
                            print(f"[EXECUTED] OPEN {target}")
                    elif is_local_app or os.path.exists(target):
                        # It's a local application or file/folder
                        open_path(target)
                        LAST_OPENED_TARGET = target
                        CURRENT_APP_CONTEXT = target.split('\\')[-1].lower() if '\\' in target else target.lower()
                        actions_executed += 1
                        log_entry['actions'].append({
                            'action': 'OPEN', 'target': target, 'result': 'opened_local'
                        })
                        print(f"[EXECUTED] OPEN {target}")
                    else:
                        # Try as a local app/path anyway
                        open_path(target)
                        LAST_OPENED_TARGET = target
                        CURRENT_APP_CONTEXT = target.lower()
                        actions_executed += 1
                        log_entry['actions'].append({
                            'action': 'OPEN', 'target': target, 'result': 'opened_fallback'
                        })
                        print(f"[EXECUTED] OPEN {target}")

                elif action_type == "SET_ALARM":
                    # action_param expected like '19:00' or '7 pm' or '07:00 PM'
                    raw = action_param.strip('"\'')
                    normalized = parse_time_string(raw)
                    if normalized:
                        res = set_windows_alarm(normalized)
                        actions_executed += 1 if res else 0
                        log_entry['actions'].append({'action': 'SET_ALARM', 'time': normalized, 'result': 'ok' if res else 'partial'})
                        print(f"[EXECUTED] SET_ALARM {normalized} -> {'ok' if res else 'partial'}")
                    else:
                        print(f"[SET_ALARM] Could not parse time: {raw}")
                        log_entry['actions'].append({'action': 'SET_ALARM', 'time_raw': raw, 'result': 'failed_parse'})
                        # Try to open the Clock app so user can complete manually
                        try:
                            subprocess.Popen(['cmd', '/c', 'start', '', 'ms-clock:'], shell=True)
                            actions_executed += 1
                            log_entry['actions'].append({'action': 'OPEN', 'target': 'ms-clock:', 'result': 'opened_for_manual'})
                        except Exception as e:
                            print(f"[SET_ALARM] fallback open error: {e}")

                elif action_type == "SEARCH":
                    query = action_param.strip('"\'')
                    # Detect if browser is open, otherwise use Chrome
                    if not CURRENT_APP_CONTEXT or CURRENT_APP_CONTEXT not in ['chrome', 'browser']:
                        detect_and_set_browser_context()
                    if not CURRENT_APP_CONTEXT or CURRENT_APP_CONTEXT not in ['chrome', 'browser']:
                        # Open Chrome first if no browser detected
                        webbrowser.open('about:blank')
                        CURRENT_APP_CONTEXT = 'chrome'
                    
                    q = urllib.parse.quote_plus(query)
                    search_url = f"https://www.google.com/search?q={q}"
                    webbrowser.open(search_url)
                    actions_executed += 1
                    log_entry['actions'].append({
                        'action': 'SEARCH', 'query': query, 'result': 'opened_search'
                    })
                    print(f"[EXECUTED] SEARCH {query}")

                elif action_type == "TYPE":
                    text = action_param.strip('"\'')
                    set_clipboard_and_paste(text)
                    actions_executed += 1
                    log_entry['actions'].append({
                        'action': 'TYPE', 'text': text[:200]
                    })
                    print(f"[EXECUTED] TYPE {text[:50]}...")

                elif action_type == "PRESS":
                    keys = action_param.strip('"\'').lower()
                    # Convert common key names
                    key_map = {
                        'enter': 'enter',
                        'return': 'enter',
                        'space': 'space',
                        'tab': 'tab',
                        'escape': 'esc',
                        'esc': 'esc',
                        'backspace': 'backspace',
                        'delete': 'delete',
                        'insert': 'insert',
                        'home': 'home',
                        'end': 'end',
                        'pageup': 'pageup',
                        'pagedown': 'pagedown',
                        'up': 'up',
                        'down': 'down',
                        'left': 'left',
                        'right': 'right',
                        'volumeup': 'volumeup',
                        'volumedown': 'volumedown',
                        'n': 'n',  # Spotify next shortcut
                        'p': 'p',  # Spotify previous shortcut
                        'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4', 'f5': 'f5',
                        'f6': 'f6', 'f7': 'f7', 'f8': 'f8', 'f9': 'f9', 'f10': 'f10',
                    }
                    
                    # Handle key combinations (ctrl+c, alt+tab, etc.)
                    if '+' in keys:
                        key_parts = [k.strip() for k in keys.split('+')]
                        if HAS_PYAUTOGUI:
                            pyautogui.hotkey(*key_parts)
                            actions_executed += 1
                            log_entry['actions'].append({
                                'action': 'PRESS', 'keys': keys, 'result': 'hotkey_executed'
                            })
                            print(f"[EXECUTED] PRESS {keys}")
                        else:
                            print(f"[PRESS ERROR] pyautogui not available for key combination: {keys}")
                    else:
                        # Single key press (including media keys like volumeup, volumedown)
                        mapped_key = key_map.get(keys, keys)
                        if HAS_PYAUTOGUI:
                            pyautogui.press(mapped_key)
                            actions_executed += 1
                            log_entry['actions'].append({
                                'action': 'PRESS', 'keys': mapped_key, 'result': 'pressed'
                            })
                            print(f"[EXECUTED] PRESS {keys}")
                        else:
                            print(f"[PRESS ERROR] pyautogui not available for key: {keys}")

                elif action_type == "CLICK":
                    button = action_param.strip('"\'').lower() or 'left'
                    if HAS_PYAUTOGUI:
                        click_mouse(button)
                        actions_executed += 1
                        log_entry['actions'].append({
                            'action': 'CLICK', 'button': button, 'result': 'clicked'
                        })
                        print(f"[EXECUTED] CLICK {button}")
                    else:
                        print(f"[CLICK ERROR] pyautogui not available")

                elif action_type == "SWITCH":
                    app = action_param.strip('"\'')
                    switch_to_app(app)
                    CURRENT_APP_CONTEXT = app.lower()
                    actions_executed += 1
                    log_entry['actions'].append({
                        'action': 'SWITCH', 'app': app, 'result': 'switched'
                    })
                    print(f"[EXECUTED] SWITCH {app}")

                elif action_type == "NEXT_TAB":
                    if HAS_PYAUTOGUI:
                        browser_tab_action('next')
                        actions_executed += 1
                        log_entry['actions'].append({'action': 'NEXT_TAB', 'result': 'done'})
                        print(f"[EXECUTED] NEXT_TAB")

                elif action_type == "PREV_TAB":
                    if HAS_PYAUTOGUI:
                        browser_tab_action('previous')
                        actions_executed += 1
                        log_entry['actions'].append({'action': 'PREV_TAB', 'result': 'done'})
                        print(f"[EXECUTED] PREV_TAB")

                elif action_type == "NEW_TAB":
                    if HAS_PYAUTOGUI:
                        browser_tab_action('new')
                        actions_executed += 1
                        log_entry['actions'].append({'action': 'NEW_TAB', 'result': 'done'})
                        print(f"[EXECUTED] NEW_TAB")

                elif action_type == "CLOSE_TAB":
                    if HAS_PYAUTOGUI:
                        browser_tab_action('close')
                        actions_executed += 1
                        log_entry['actions'].append({'action': 'CLOSE_TAB', 'result': 'done'})
                        print(f"[EXECUTED] CLOSE_TAB")

                elif action_type == "SLEEP":
                    seconds = float(action_param) if action_param else 1
                    time.sleep(seconds)
                    actions_executed += 1
                    log_entry['actions'].append({'action': 'SLEEP', 'seconds': seconds})
                    print(f"[EXECUTED] SLEEP {seconds}s")

                elif action_type == "WAIT_FOR_PAGE":
                    # Simple wait for page to load
                    time.sleep(3)
                    actions_executed += 1
                    log_entry['actions'].append({'action': 'WAIT_FOR_PAGE', 'result': 'waited'})
                    print(f"[EXECUTED] WAIT_FOR_PAGE")

                elif action_type == "YOUTUBE_PLAY":
                    video_query = action_param.strip('"\'')
                    if play_youtube(video_query):
                        actions_executed += 1
                        CURRENT_APP_CONTEXT = 'youtube'
                        log_entry['actions'].append({
                            'action': 'YOUTUBE_PLAY', 'query': video_query, 'result': 'playing'
                        })
                        print(f"[EXECUTED] YOUTUBE_PLAY {video_query}")
                    else:
                        print(f"[YOUTUBE_PLAY ERROR] Could not find or play video: {video_query}")
                        log_entry['actions'].append({
                            'action': 'YOUTUBE_PLAY', 'query': video_query, 'result': 'failed'
                        })

            except Exception as e:
                print(f"[ACTION ERROR] {action_type}: {e}")
                continue

        if actions_executed > 0:
            print(f"[SUCCESS] Executed {actions_executed} action(s)")
            try:
                # Speak a short 'Done' confirmation after executing actions
                speak('Done', language)
            except Exception:
                pass
            # write audit log line
            try:
                with open(ACTION_LOG_FILE, 'a', encoding='utf-8') as lf:
                    lf.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            except Exception as e:
                print(f"[LOG ERROR] Could not write action log: {e}")
            return True
        else:
            # Silent fail if no valid actions found (AI will try again or speak response)
            return False

    except Exception as e:
        print(f"[EXECUTE VIA AI ERROR] {e}")
        return False


### --- System control helpers ---
def confirm_and_execute(action_desc, func, language='en', *args, **kwargs):
    """Ask for voice confirmation then execute the function if confirmed."""
    global stop_speaking
    # Check system control enable
    if not system_control_enabled():
        msg = "System control is disabled. To enable, set ENABLE_SYSTEM_CONTROL=true in .env"
        print(f"[SYSTEM] {msg}")
        speak(msg, language)
        return False

    # Prevent any delete/remove commands regardless of unattended setting
    forbidden_keywords = ['delete', 'remove', 'rm ', 'rmdir', 'del ', 'erase', 'format']
    if any(k in action_desc.lower() for k in forbidden_keywords):
        msg = "Refusing to perform file deletion or destructive operations. This action is blocked."
        print(f"[SYSTEM] {msg}")
        speak(msg, language)
        return False

    unattended = unattended_enabled()

    if unattended:
        # Execute immediately without asking
        try:
            func(*args, **kwargs)
            speak("Done", language)
            return True
        except Exception as e:
            err = f"Failed to perform action: {e}"
            print(f"[SYSTEM ERROR] {err}")
            speak(err, language)
            return False

    # Default: ask for confirmation
    confirm_msg = f"I will {action_desc}. Say 'yes' to confirm or 'no' to cancel."
    print(f"[CONFIRM] {confirm_msg}")
    speak(confirm_msg, language)
    # short listen
    resp = get_voice_input(language, duration=5)
    if not resp:
        speak("No confirmation received. Cancelled.", language)
        return False
    if resp.lower() in ['yes', 'yeah', 'yup', 'sure', 'please do', 'haan', 'haan']:
        try:
            func(*args, **kwargs)
            speak("Done", language)
            return True
        except Exception as e:
            err = f"Failed to perform action: {e}"
            print(f"[SYSTEM ERROR] {err}")
            speak(err, language)
            return False
    else:
        speak("Cancelled.", language)
        return False


def open_path(path):
    """Open a file or folder or URL using system default"""
    # Try to resolve common app names via app_mappings.json
    try:
        mappings_file = os.path.join(os.path.dirname(__file__), 'app_mappings.json')
        if os.path.exists(mappings_file):
            try:
                with open(mappings_file, 'r', encoding='utf-8') as mf:
                    app_map = json.load(mf)
            except Exception:
                app_map = {}
        else:
            app_map = {}
    except Exception:
        app_map = {}

    global CURRENT_APP_CONTEXT, LAST_OPENED_TARGET

    key = path.strip().lower()
    if key in app_map:
        mapped = app_map[key]
        # replace path with mapping target
        path = mapped
        # Set context to the friendly name the user used
        CURRENT_APP_CONTEXT = key
        LAST_OPENED_TARGET = path

    # If it's a URL, open in browser
    if isinstance(path, str) and path.lower().startswith('http'):
        try:
            webbrowser.open(path)
            return True
        finally:
            # keep context as-is for follow-up actions
            pass

    # If path exists as given, open it
    if os.path.exists(path):
        try:
            os.startfile(path)
            # set last opened
            LAST_OPENED_TARGET = path
            return True
        except Exception:
            pass

    # Try to resolve executable on PATH (e.g., 'chrome', 'whatsapp' if in PATH)
    try:
        import shutil
        exe_path = shutil.which(path)
        if exe_path:
            try:
                subprocess.Popen([exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                LAST_OPENED_TARGET = exe_path
                return True
            except Exception:
                pass
    except Exception:
        pass

    # Try to start directly (may work if given a program name)
    try:
        subprocess.Popen([path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        LAST_OPENED_TARGET = path
        return True
    except Exception:
        pass

    # Try Windows 'start' via cmd; this often handles program names and file associations
    try:
        subprocess.Popen(['cmd', '/c', 'start', '', path], shell=True)
        LAST_OPENED_TARGET = path
        return True
    except Exception:
        pass

    # Fallback to PowerShell Start-Process
    try:
        subprocess.Popen(["powershell", "-Command", f"Start-Process '{path}'"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        LAST_OPENED_TARGET = path
        return True
    except Exception as e:
        print(f"[OPEN ERROR] Could not open {path}: {e}")
        return False


def type_text(text):
    if not HAS_PYAUTOGUI:
        raise RuntimeError('pyautogui not available')
    pyautogui.typewrite(text)


def set_clipboard_and_paste(text):
    """Set Windows clipboard to `text` using PowerShell and paste with pyautogui if available."""
    try:
        # Write text to temporary file to avoid PowerShell quoting issues
        fd, tmp_path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(text)

        # Use PowerShell to set clipboard from file content
        ps_cmd = f"Get-Content -Raw -Encoding UTF8 '{tmp_path}' | Set-Clipboard"
        subprocess.run(["powershell", "-Command", ps_cmd], check=False)

        # Try to paste
        if HAS_PYAUTOGUI:
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'v')
            # small pause after paste
            time.sleep(0.2)
            return True
        else:
            print('[CLIPBOARD] Text copied to clipboard. Please paste manually (Ctrl+V).')
            return True
    except Exception as e:
        print(f"[CLIP ERROR] {e}")
        return False
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def press_keys(key_sequence):
    if not HAS_PYAUTOGUI:
        raise RuntimeError('pyautogui not available')
    # key_sequence example: 'ctrl+s' or 'enter'
    parts = key_sequence.lower().split('+')
    if len(parts) > 1:
        pyautogui.hotkey(*parts)
    else:
        pyautogui.press(parts[0])


def move_mouse(x, y):
    if not HAS_PYAUTOGUI:
        raise RuntimeError('pyautogui not available')
    pyautogui.moveTo(int(x), int(y))


def click_mouse(button='left'):
    if not HAS_PYAUTOGUI:
        raise RuntimeError('pyautogui not available')
    pyautogui.click(button=button)


def open_notepad():
    """Open Windows Notepad"""
    try:
        subprocess.Popen(["notepad.exe"])
    except Exception:
        # fallback
        subprocess.Popen(["powershell", "-Command", "Start-Process notepad.exe"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def switch_to_app(app_key):
    """Bring an application window to the foreground by app key or name (best-effort).
    Uses pygetwindow if available, otherwise falls back to alt-tab cycling or opens the app.
    """
    try:
        mappings_file = os.path.join(os.path.dirname(__file__), 'app_mappings.json')
        app_map = {}
        if os.path.exists(mappings_file):
            try:
                with open(mappings_file, 'r', encoding='utf-8') as mf:
                    app_map = json.load(mf)
            except Exception:
                app_map = {}

        target = app_map.get(app_key.lower()) or app_key

        # Try to find window with pygetwindow
        if HAS_PYGETWINDOW:
            try:
                # Try matching windows whose title contains the app_key or known target basename
                candidates = []
                for title in gw.getAllTitles():
                    if not title:
                        continue
                    if app_key.lower() in title.lower():
                        candidates.append(title)
                    else:
                        # also match target executable name
                        if isinstance(target, str) and os.path.basename(str(target)).lower().split('.')[0] in title.lower():
                            candidates.append(title)

                if candidates:
                    # Activate first candidate
                    win = gw.getWindowsWithTitle(candidates[0])[0]
                    try:
                        win.activate()
                        return True
                    except Exception:
                        try:
                            win.minimize()
                            win.restore()
                            win.activate()
                            return True
                        except Exception:
                            pass
            except Exception as e:
                print(f"[SWITCH WINDOW ERROR] {e}")

        # Fallback: try to open the app if cannot find an existing window
        if isinstance(target, str) and os.path.exists(str(target)):
            try:
                subprocess.Popen([str(target)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return True
            except Exception:
                pass

        # Last resort: alt-tab a few times (best-effort)
        if HAS_PYAUTOGUI:
            for _ in range(8):
                pyautogui.keyDown('alt')
                pyautogui.press('tab')
                pyautogui.keyUp('alt')
                time.sleep(0.2)
                # If pygetwindow available, check active window title for a match
                if HAS_PYGETWINDOW:
                    try:
                        active = gw.getActiveWindow()
                        if active and app_key.lower() in (active.title or '').lower():
                            return True
                    except Exception:
                        pass
            return False

        # If nothing worked, try open_path as a fallback
        try:
            return open_path(target)
        except Exception:
            return False
    except Exception as e:
        print(f"[SWITCH ERROR] {e}")
        return False


def browser_tab_action(action, index=None):
    """Perform browser tab actions using keyboard shortcuts (best-effort).
    action: 'next', 'previous', 'new', 'close', 'number'
    index: 1-9 for 'number' actions
    """
    if not HAS_PYAUTOGUI:
        print('[BROWSER ACTION] pyautogui not available')
        return False
    try:
        if action == 'next':
            pyautogui.hotkey('ctrl', 'tab')
            return True
        if action == 'previous':
            pyautogui.hotkey('ctrl', 'shift', 'tab')
            return True
        if action == 'new':
            pyautogui.hotkey('ctrl', 't')
            return True
        if action == 'close':
            pyautogui.hotkey('ctrl', 'w')
            return True
        if action == 'number' and index:
            # Ctrl+1..9 jumps to tab 1..9
            key = str(index)
            pyautogui.hotkey('ctrl', key)
            return True
        return False
    except Exception as e:
        print(f"[BROWSER ACTION ERROR] {e}")
        return False


def detect_and_set_browser_context():
    """Detect if a browser (Chrome) window is open and set CURRENT_APP_CONTEXT accordingly."""
    global CURRENT_APP_CONTEXT, LAST_OPENED_TARGET
    try:
        if HAS_PYGETWINDOW:
            for title in gw.getAllTitles():
                if not title:
                    continue
                lt = title.lower()
                if 'chrome' in lt or 'google chrome' in lt:
                    CURRENT_APP_CONTEXT = 'chrome'
                    # If the title mentions instagram, set last opened target
                    if 'instagram' in lt:
                        LAST_OPENED_TARGET = 'https://www.instagram.com/'
                    return True
        return False
    except Exception as e:
        print(f"[DETECT BROWSER ERROR] {e}")
        return False


def check_wake_word(text):
    """
    Check if the wake word is present in the text.
    If wake word is not enabled, always return True.
    Otherwise, return True if wake word is found, and extract the command after it.
    Returns: (should_process, command_text)
    """
    if not WAKE_WORD_ENABLED:
        return True, text

    text_lower = text.lower().strip()
    if WAKE_WORD in text_lower:
        # Extract the part after the wake word
        idx = text_lower.find(WAKE_WORD)
        # Get the part after the wake word
        remaining = text[idx + len(WAKE_WORD):].strip()
        return True, remaining if remaining else text
    else:
        print(f"[LISTENING] Waiting for wake word '{WAKE_WORD}'...")
        return False, ""


def play_youtube(query):
    """Search YouTube and open first video result in browser."""
    try:
        q = requests.utils.requote_uri(query)
        search_url = f"https://www.youtube.com/results?search_query={q}"
        resp = requests.get(search_url, timeout=10)
        if resp.status_code == 200:
            # find first watch?v= id
            m = re.search(r"/watch\?v=([\w-]{11})", resp.text)
            if m:
                vid = m.group(1)
                watch_url = f"https://www.youtube.com/watch?v={vid}"
                webbrowser.open(watch_url)
                return True
        # fallback: open search page
        webbrowser.open(search_url)
        return True
    except Exception as e:
        print(f"[YT ERROR] {e}")
        return False


def parse_time_string(s: str):
    """Try to parse a human time string into 24-hour HH:MM format. Best-effort."""
    if not s:
        return None
    s = s.strip().lower().replace('.', '').replace('\t', ' ')
    # remove words like 'for', 'at'
    s = re.sub(r"\b(at|for)\b", '', s).strip()
    # common formats to try
    from datetime import datetime
    candidates = ["%I:%M %p", "%I %p", "%H:%M", "%H%M", "%I:%M%p", "%I%p"]
    for fmt in candidates:
        try:
            dt = datetime.strptime(s.upper(), fmt)
            return f"{dt.hour:02d}:{dt.minute:02d}"
        except Exception:
            pass

    # Try to pull numbers like '7 pm' or '7pm' manually
    m = re.search(r"(\d{1,2})(?:[:\.]?(\d{2}))?\s*(am|pm)?", s, flags=re.IGNORECASE)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        ampm = (m.group(3) or '').lower()
        if ampm == 'pm' and hour < 12:
            hour += 12
        if ampm == 'am' and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"

    return None


def set_windows_alarm(time_hhmm: str, label: str = None, enabled: bool = True, sound: str = None):
    """Best-effort: Open Windows Alarms & Clock and create a new alarm at `HH:MM` (24-hour).
    Uses pywinauto when available. Returns True on likely success, False otherwise.
    """
    if not time_hhmm:
        print("[SET_ALARM] No time provided")
        return False

    # Ensure format HH:MM
    if not re.match(r"^\d{2}:\d{2}$", time_hhmm):
        print(f"[SET_ALARM] Time not normalized: {time_hhmm}")
        return False

    # Open the Alarms & Clock app
    try:
        subprocess.Popen(['cmd', '/c', 'start', '', 'ms-clock:'], shell=True)
    except Exception as e:
        print(f"[SET_ALARM] Could not open ms-clock: {e}")

    # If pywinauto is not available, we at least opened the app; return False to indicate not fully automated
    if not HAS_PYWINAUTO:
        print('[SET_ALARM] pywinauto not available; opened Alarms app for manual setup')
        return False

    try:
        # Give the app some time to start
        time.sleep(1.5)
        desktop = Desktop(backend='uia')

        # Try to find the Alarms window
        dlg = None
        try:
            dlg = desktop.window(title_re='.*Alarms.*|.*Alarms & Clock.*')
            dlg.wait('visible', timeout=8)
        except Exception:
            # try alternative title
            try:
                dlg = desktop.window(best_match='Alarms & Clock')
                dlg.wait('visible', timeout=6)
            except Exception:
                dlg = None

        if not dlg:
            print('[SET_ALARM] Could not find Alarms window controls')
            return False

        # Click the 'Add alarm' / 'New' button
        try:
            add_btn = dlg.child_window(title_re='Add alarm|New alarm|New', control_type='Button')
            if add_btn and add_btn.exists(timeout=2):
                add_btn.invoke()
            else:
                # fallback: try generic button
                for b in dlg.descendants(control_type='Button'):
                    t = (b.element_info.name or '').lower()
                    if 'add' in t or 'new' in t:
                        b.invoke()
                        break
        except Exception as e:
            print(f"[SET_ALARM] Could not click Add button: {e}")

        time.sleep(0.6)

        # Attempt to type the time using UI automation: focus the hour/minute fields or use keyboard entry
        try:
            # Many Windows versions use toggle buttons; using keyboard is often most compatible
            if HAS_PYAUTOGUI:
                # Focus: ensure window is active
                try:
                    dlg.set_focus()
                except Exception:
                    pass
                # Try to input the time via keyboard: clear then type HH:MM
                hh, mm = time_hhmm.split(':')
                # Some UI's accept typing like '7:00 PM' — we send numeric then tab
                pyautogui.press('tab')
                time.sleep(0.1)
                pyautogui.typewrite(hh)
                pyautogui.press('tab')
                pyautogui.typewrite(mm)
                # Optionally set AM/PM if UI uses it
                time.sleep(0.2)
                # Save/Done button
                pyautogui.press('tab')
                pyautogui.press('enter')
                return True
            else:
                print('[SET_ALARM] pyautogui not available to complete UI inputs')
                return False
        except Exception as e:
            print(f"[SET_ALARM] UI input error: {e}")
            return False

    except Exception as e:
        print(f"[SET_ALARM ERROR] {e}")
        return False


def confirmation_beep(frequency=1000, duration=200):
    """Play a confirmation beep sound using PowerShell when wake word is detected.
    frequency: Hz (default 1000 = mid-tone)
    duration: milliseconds (default 200)
    """
    try:
        ps_cmd = f"""
[System.Console]::Beep({frequency}, {duration})
"""
        subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True,
            timeout=5
        )
    except Exception as e:
        print(f"[BEEP ERROR] {e}")


def normalize_spoken_text(text: str) -> str:
    """Normalize common spoken tokens to punctuation/symbols.
    Examples: 'instagram dot com slash reel' -> 'instagram.com/reel'
    """
    if not text:
        return text
    s = text.lower()
    # common phrase replacements first
    replacements = [
        (r'http[s]?\s*colon\s*slash\s*slash', 'https://'),
        (r'http\s*colon\s*slash\s*slash', 'http://'),
        (r'forward\s*slash', '/'),
        (r'back\s*slash', '\\'),
        (r'\s?dot\s?com\b', '.com'),
        (r'\s?dot\s?org\b', '.org'),
        (r'\s?dot\s?in\b', '.in'),
        (r'\s?dot\s?net\b', '.net'),
        (r'\s?dot\s?io\b', '.io'),
        (r'\s?dot\s?edu\b', '.edu'),
        (r'\s?dot\s?gov\b', '.gov'),
        (r'\s?slash\s?', '/'),
        (r'\s?underscore\s?', '_'),
        (r'\s?dash\s?', '-'),
        (r'\s?hyphen\s?', '-'),
        (r'\s?space\s?', ' '),
        (r'\s?colon\s?', ':'),
        (r'\s?period\s?', '.'),
        (r'\s?comma\s?', ','),
    ]

    for pat, rep in replacements:
        s = safe_sub(pat, rep, s)

    # Replace remaining single-word tokens like 'dot' -> '.'
    s = safe_sub(r'\bdot\b', '.', s)

    # Remove duplicated spaces
    s = safe_sub(r'\s+', ' ', s).strip()

    # Remove spaces around slashes and dots
    s = safe_sub(r"\s*/\s*", '/', s)
    s = safe_sub(r"\s*\.\s*", '.', s)

    return s


def is_likely_url(s: str) -> bool:
    if not s:
        return False
    s = s.strip()
    if s.startswith('http://') or s.startswith('https://'):
        return True
    if s.startswith('www.'):
        return True
    # contains domain-like pattern with dot and no leading spaces
    if '/' in s:
        # has path, treat as url if there's a dot before first slash
        parts = s.split('/', 1)
        if '.' in parts[0]:
            return True
    if '.' in s and ' ' not in s:
        return True
    return False


def plan_and_execute(client, app_key, action, query, language='en'):
    """Ask the AI to produce a short plan for the requested action, speak the plan, then execute a best-effort automation."""
    try:
        # Ask the AI to produce a concise ordered plan (numbered steps)
        prompt = (
            f"You are an assistant that writes short, numbered step plans.\n"
            f"Task: perform '{action}' for '{query}' in app '{app_key}'.\n"
            f"Return 3-6 short numbered steps (like '1. Open Chrome', '2. Focus search box', '3. Type query and press Enter')."
        )
        messages = [{"role": "user", "content": prompt}]
        plan_text = get_ai_response(client, messages, language, preprompt=CONTROL_PREPROMPT if system_control_enabled() else None)
        # Speak a one-line summary: what we'll do
        summary = plan_text.splitlines()[0] if plan_text else f"I'll try to {action} {query} in {app_key}."
        print(f"[PLAN]\n{plan_text}")
        speak(summary, language)

        # Execute best-effort action (we don't strictly parse every AI step; we use our deterministic handlers)
        ok = perform_contextual_action(client, app_key, action, query, language)
        return ok
    except Exception as e:
        print(f"[PLAN ERROR] {e}")
        return False


def perform_contextual_action(client, app_key, action, query, language='en'):
    """Perform an action (search, type, open) within the context of `app_key`.
    Returns True on success (best-effort).
    """
    global CURRENT_APP_CONTEXT, LAST_OPENED_TARGET
    try:
        # Load mappings to find exact targets
        mappings_file = os.path.join(os.path.dirname(__file__), 'app_mappings.json')
        app_map = {}
        if os.path.exists(mappings_file):
            try:
                with open(mappings_file, 'r', encoding='utf-8') as mf:
                    app_map = json.load(mf)
            except Exception:
                app_map = {}

        target = app_map.get(app_key, LAST_OPENED_TARGET)

        # Normalize spoken query and detect URLs
        q_norm = normalize_spoken_text(str(query or ''))
        is_url = is_likely_url(q_norm)

        # CHROME: prefer opening a search URL directly using the chrome executable if available
        if app_key in ['chrome', 'browser'] or (isinstance(target, str) and target.lower().endswith('chrome.exe')):
            # Use chrome if we have path, otherwise use default browser
            import urllib.parse
            # If the normalized query looks like a URL, open it directly
            if is_url:
                url = q_norm
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = 'https://' + url
                # Use Selenium if available for deterministic navigation
                if HAS_SELENIUM:
                    try:
                        options = webdriver.ChromeOptions()
                        options.add_argument('--new-window')
                        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
                        driver.get(url)
                        CURRENT_APP_CONTEXT = 'chrome'
                        return True
                    except Exception as e:
                        print(f"[SELENIUM CHROME ERROR] {e}")
                if target and os.path.exists(target):
                    try:
                        subprocess.Popen([target, url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        CURRENT_APP_CONTEXT = 'chrome'
                        return True
                    except Exception:
                        pass
                webbrowser.open(url)
                CURRENT_APP_CONTEXT = 'chrome'
                return True

            # Otherwise perform a search
            q = urllib.parse.quote_plus(q_norm or str(query))
            search_url = f"https://www.google.com/search?q={q}"
            # Prefer Selenium if available for more deterministic control
            if HAS_SELENIUM:
                try:
                    options = webdriver.ChromeOptions()
                    options.add_argument('--new-window')
                    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
                    driver.get(search_url)
                    CURRENT_APP_CONTEXT = 'chrome'
                    return True
                except Exception as e:
                    print(f"[SELENIUM CHROME ERROR] {e}")
                    # fallback to launching via exe or browser
            if target and os.path.exists(target):
                try:
                    subprocess.Popen([target, search_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    CURRENT_APP_CONTEXT = 'chrome'
                    return True
                except Exception:
                    pass
            webbrowser.open(search_url)
            CURRENT_APP_CONTEXT = 'chrome'
            return True

        # WHATSAPP: open WhatsApp Web and attempt to focus search box then type the query (best-effort)
        if app_key in ['whatsapp'] or (isinstance(target, str) and 'whatsapp' in str(target).lower()):
            url = target or 'https://web.whatsapp.com/'
            # Prefer Selenium for interacting with WhatsApp Web
            if HAS_SELENIUM:
                try:
                    options = webdriver.ChromeOptions()
                    options.add_argument('--new-window')
                    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
                    driver.get(url)
                    CURRENT_APP_CONTEXT = 'whatsapp'
                    # Wait for page to load and try to find the search box
                    time.sleep(5)
                    try:
                        # WhatsApp Web search box has aria-label 'Search or start new chat' or input with title
                        el = None
                        for selector in ["//div[@contenteditable='true']", "//input[@title='Search or start new chat']"]:
                            try:
                                el = driver.find_element(By.XPATH, selector)
                                if el:
                                    break
                            except Exception:
                                el = None
                        if el:
                            el.click()
                            el.send_keys(q_norm)
                            el.send_keys(Keys.ENTER)
                            return True
                    except Exception as e:
                        print(f"[SELENIUM WHATSAPP SEARCH ERROR] {e}")
                except Exception as e:
                    print(f"[SELENIUM WHATSAPP ERROR] {e}")

            # Fallback to open in browser and try pyautogui
            webbrowser.open(url)
            CURRENT_APP_CONTEXT = 'whatsapp'
            time.sleep(5)
            if HAS_PYAUTOGUI:
                try:
                    pyautogui.hotkey('ctrl', 'f')
                    time.sleep(0.3)
                    pyautogui.typewrite(q_norm)
                    pyautogui.press('enter')
                    return True
                except Exception as e:
                    print(f"[WHATSAPP-AUTO ERROR] {e}")
                    return False
            else:
                print('[WHATSAPP] pyautogui not available; opened WhatsApp Web. Use manual search.')
                return True

        # FALLBACK: open a web search (use default browser)
        import urllib.parse
        q = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={q}"
        webbrowser.open(search_url)
        return True

    except Exception as e:
        print(f"[CONTEXT ACTION ERROR] {e}")
        return False


def main():
    """Main conversation loop"""
    print("=" * 60)
    print("NOVA - AI Assistant")
    print("=" * 60)
    print("\n[STARTED] Listening in voice mode...")
    print("[COMMANDS]")
    print("  'search online <query>' - Search the internet")
    print("  'stop' or Ctrl+C - Stop current action")
    print("  'quit' or 'exit' - End conversation")
    print("  'switch to hindi' - Change to Hindi")
    print("  'switch to english' - Change to English\n")
    
    # Initialize
    client = create_nova()
    conversation_history = []

    # Load persistent memory if enabled
    if SAVE_MEMORY and os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    conversation_history = loaded[-MEMORY_SIZE:]
                    print(f"[MEMORY] Loaded {len(conversation_history)} messages from memory.")
        except Exception as e:
            print(f"[MEMORY ERROR] Failed to load memory: {e}")
    language = os.getenv('LANGUAGE', 'en')
    speech_rate = int(os.getenv('SPEECH_RATE', '0'))
    speech_volume = int(os.getenv('SPEECH_VOLUME', '100'))
    
    print(f"[LANGUAGE] {language.upper()}\n")
    # Read reasoning flag so we can optionally strip reasoning sentences
    ENABLE_REASONING_FLAG = os.getenv('ENABLE_REASONING', 'false').lower() in ['1', 'true', 'yes']
    
    # Continuous conversation loop
    while True:
        try:
            # If wake word is enabled, listen for wake word first
            if WAKE_WORD_ENABLED:
                print(f"[WAKE WORD LISTENING] Say '{WAKE_WORD}' to activate...", flush=True)
                while True:
                    wake_input = get_voice_input(language)
                    if not wake_input:
                        continue
                    if WAKE_WORD in wake_input.lower():
                        # Wake word detected
                        # extract command if present
                        user_input = wake_input[wake_input.lower().find(WAKE_WORD) + len(WAKE_WORD):].strip()
                        print(f"[WAKE WORD DETECTED] Ready for command...", flush=True)
                        break
                    # Wake word not found, go back to listening
                    continue
            else:
                # Wake word disabled, listen normally
                user_input = get_voice_input(language)
            
            if not user_input:
                continue
            
            # Check commands
            lower_input = user_input.lower()
            
            if lower_input in ['quit', 'exit', 'bye']:
                print("[NOVA] Goodbye! Talk soon!")
                speak("Goodbye! Talk soon!", language, speech_rate, speech_volume)
                break
            
            if lower_input == 'stop':
                stop_speaking = True
                print("[STOPPED]")
                continue
            
            if 'switch to hindi' in lower_input:
                language = 'hi'
                print("[LANGUAGE] Switched to Hindi")
                speak("Language changed to Hindi", 'en', speech_rate, speech_volume)
                continue
            
            if 'switch to english' in lower_input:
                language = 'en'
                print("[LANGUAGE] Switched to English")
                speak("Language changed to English", language, speech_rate, speech_volume)
                continue
            
            # Handle search
            # Time-only queries (very short direct answers)
            if any(kw in lower_input for kw in ['what time', 'what is the time', "time is it", 'current time', 'what time is it', 'time today', 'what time is today']):
                t = get_current_time(language)
                print(f"[NOVA] {t}")
                speak(t, language, speech_rate, speech_volume)
                continue

            # Handle 'search online' explicitly
            if 'search online' in lower_input:
                query = user_input.replace('search online', '').replace('Search online', '').strip()
                if not query:
                    query = "latest news"

                search_results = do_search(query)

                if search_results:
                    first = search_results[0]
                    short_summary = first.get('snippet') or first.get('title') or f"Results for {query}"
                    short_summary = short_summary.strip()
                    if len(short_summary) > 140:
                        short_summary = short_summary[:137].rsplit(' ', 1)[0] + '...'

                    details = []
                    for i, result in enumerate(search_results, 1):
                        title = result.get('title', '')
                        snippet = result.get('snippet', '')
                        link = result.get('link', '')
                        line = f"{i}. {title}: {snippet}"
                        if link:
                            line += f" (link: {link})"
                        details.append(line)

                    print(f"[NOVA SUMMARY] {short_summary}")
                    speak(short_summary, language, speech_rate, speech_volume)
                    time.sleep(0.3)
                    details_text = "\n".join(details)
                    print(f"[NOVA DETAILS]\n{details_text}")
                    speak(details_text, language, speech_rate, speech_volume)
                else:
                    msg = "Sorry, couldn't find results. Try another search."
                    print(f"[NOVA] {msg}")
                    speak(msg, language, speech_rate, speech_volume)

                continue
            
            # PRIMARY: Try AI-driven universal executor for system control commands
            # This handles: open notepad, search X, type X, press keys, click, write a letter, etc.
            # If user prefixed with 'hey', treat as a conversational query and do NOT execute system actions
            if lower_input.startswith('hey '):
                conv_text = user_input[len('hey '):].strip()
                if not conv_text:
                    continue
                # send directly to AI for a conversational response
                conversation_history.append({"role": "user", "content": conv_text})
                response = get_ai_response(client, conversation_history, language, preprompt=None)
                conversation_history.append({"role": "assistant", "content": response})
                # Persist memory if enabled
                if SAVE_MEMORY:
                    try:
                        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                            json.dump(conversation_history[-MEMORY_SIZE:], f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"[MEMORY ERROR] Failed to save memory: {e}")
                # Speak the conversational response
                speak_thread = threading.Thread(
                    target=speak,
                    args=(response, language, speech_rate, speech_volume),
                    daemon=True
                )
                speak_thread.start()
                speak_thread.join(timeout=60)
                continue

            if system_control_enabled():
                executed = execute_via_ai_plan(client, user_input, language)
                if executed:
                    # Successfully executed via AI plan, skip conversational AI
                    continue
            
            # If not system control or execution failed, fall back to conversational AI

            # Add to conversation history
            conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Get AI response
            response = get_ai_response(client, conversation_history, language, preprompt=CONTROL_PREPROMPT if system_control_enabled() else None)

            # If reasoning is disabled, remove short 'Reason:' lines from the response
            if not ENABLE_REASONING_FLAG:
                filtered_lines = []
                for line in response.splitlines():
                    l = line.strip()
                    # remove lines that start with 'reason' (case-insensitive)
                    if l.lower().startswith('reason'):
                        continue
                    # also remove lines that start with 'because' if they are just short reasoning
                    if l.lower().startswith('because') and len(l.split()) < 20:
                        continue
                    filtered_lines.append(line)
                new_response = "\n".join(filtered_lines).strip()
                if new_response:
                    response = new_response
            
            # Add to history
            conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            # Keep conversation history short according to MEMORY_SIZE
            if len(conversation_history) > MEMORY_SIZE:
                conversation_history = conversation_history[-MEMORY_SIZE:]

            # Persist memory if enabled
            if SAVE_MEMORY:
                try:
                    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                        json.dump(conversation_history[-MEMORY_SIZE:], f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"[MEMORY ERROR] Failed to save memory: {e}")
            
            # Speak response
            speak_thread = threading.Thread(
                target=speak,
                args=(response, language, speech_rate, speech_volume),
                daemon=True
            )
            speak_thread.start()
            speak_thread.join(timeout=60)
        
        except KeyboardInterrupt:
            print("\n[STOPPED] Goodbye!")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            continue

if __name__ == "__main__":
    main()
