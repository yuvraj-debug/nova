import unittest
from unittest import mock
import webbrowser
import requests

import op

class TestCore(unittest.TestCase):
    def test_resolve_instagram_inbox_mapping(self):
        kind, val = op.resolve_open_target(None, 'instagram', 'open my instagram chats')
        self.assertEqual(kind, 'url')
        self.assertIn('direct/inbox', val)

    def test_resolve_gmail_inbox_mapping(self):
        kind, val = op.resolve_open_target(None, 'gmail', 'open my gmail inbox')
        self.assertEqual(kind, 'url')
        self.assertIn('mail.google.com', val)

    def test_resolve_twitter_messages(self):
        kind, val = op.resolve_open_target(None, 'twitter', 'open twitter messages')
        self.assertEqual(kind, 'url')
        self.assertIn('twitter.com/messages', val)

    def test_resolve_brave_mapping(self):
        kind, val = op.resolve_open_target(None, 'brave', 'open brave')
        # Mapping should resolve to a local path (brave executable)
        self.assertEqual(kind, 'path')
        self.assertIn('brave', val.lower())

    def test_fuzzy_match_slack(self):
        kind, val = op.resolve_open_target(None, 'slak', 'open slack dms')
        # fuzzy match should resolve to slack
        self.assertIn(kind, ('url', 'app', 'path'))

    @mock.patch('webbrowser.open')
    @mock.patch('requests.get')
    def test_play_youtube_finds_first_video(self, mock_get, mock_open):
        # Mock requests response containing a watch URL
        class FakeResp:
            status_code = 200
            text = '.../watch?v=ABCDEFGHIJK...'
        mock_get.return_value = FakeResp()

        status = op.play_youtube('test video')
        self.assertEqual(status, 'playing')
        mock_open.assert_called()
        called_url = mock_open.call_args[0][0]
        self.assertIn('watch?v=', called_url)
        self.assertIn('autoplay=1', called_url)

    @mock.patch('webbrowser.open')
    @mock.patch('requests.get')
    def test_play_youtube_no_result_opens_search(self, mock_get, mock_open):
        class FakeResp:
            status_code = 200
            text = 'no results here'
        mock_get.return_value = FakeResp()

        status = op.play_youtube('unlikely query 12345')
        self.assertEqual(status, 'search_opened')
        mock_open.assert_called()
        called_url = mock_open.call_args[0][0]
        self.assertIn('results?search_query=', called_url)

    @mock.patch('op.time.sleep')
    @mock.patch('op.open_path')
    def test_execute_spotify_auto_sleep(self, mock_open_path, mock_sleep):
        # Simulate AI plan that opens spotify then immediately presses space
        mock_open_path.return_value = True
        # Patch get_ai_response to return actions
        with mock.patch('op.get_ai_response', return_value="ACTION: OPEN spotify\nACTION: PRESS space"):
            res = op.execute_via_ai_plan(None, 'play song on spotify')
            self.assertTrue(res)
            # Ensure we auto-slept to allow Spotify to start
            mock_sleep.assert_called()

    @mock.patch.dict('os.environ', {'SPOTIFY_STARTUP_SLEEP': '2.5', 'POST_SPACE_DELAY': '1.0'})
    @mock.patch('op.time.sleep')
    @mock.patch('op.open_path')
    def test_execute_spotify_custom_sleep_env(self, mock_open_path, mock_sleep):
        mock_open_path.return_value = True
        with mock.patch('op.get_ai_response', return_value="ACTION: OPEN spotify\nACTION: PRESS space\nACTION: PRESS alt+tab"):
            res = op.execute_via_ai_plan(None, 'play song')
            self.assertTrue(res)
            called_args = [c[0] for c in mock_sleep.call_args_list]
            self.assertTrue(any(len(a) and abs(a[0] - 2.5) < 1e-6 for a in called_args))
            self.assertTrue(any(len(a) and abs(a[0] - 1.0) < 1e-6 for a in called_args))

    @mock.patch('op.set_clipboard_and_paste')
    @mock.patch('op.open_path')
    def test_write_essay_opens_notepad_and_writes(self, mock_open_path, mock_set_clip):
        # Simulate AI client and generated content
        fake_content = 'LONG ESSAY CONTENT'
        with mock.patch('op.generate_long_text', return_value=fake_content) as gen:
            res = op.execute_via_ai_plan(object(), 'write essay on testing')
            self.assertTrue(res)
            mock_open_path.assert_called_with('notepad')
            mock_set_clip.assert_called_with(fake_content)

    @mock.patch('op.set_clipboard_and_paste')
    @mock.patch('op.open_path')
    def test_write_generic_opens_notepad_and_writes(self, mock_open_path, mock_set_clip):
        fake_content = 'GENERIC WRITE CONTENT'
        with mock.patch('op.generate_long_text', return_value=fake_content) as gen:
            res = op.execute_via_ai_plan(object(), 'write a short note about testing')
            self.assertTrue(res)
            mock_open_path.assert_called_with('notepad')
            mock_set_clip.assert_called_with(fake_content)

    @mock.patch('op.set_clipboard_and_paste')
    def test_type_esaay_direct_typing(self, mock_set_clip):
        fake_content = 'LONG ESSAY CONTENT'
        with mock.patch('op.generate_long_text', return_value=fake_content) as gen:
            res = op.execute_via_ai_plan(object(), 'type esaay on testing')
            self.assertTrue(res)
            # Should not open notepad, only paste into current focus
            mock_set_clip.assert_called_with(fake_content)

    @mock.patch('op.set_clipboard_and_paste')
    def test_type_code_direct_typing(self, mock_set_clip):
        fake_content = 'def foo():\n    return True'
        with mock.patch('op.generate_long_text', return_value=fake_content) as gen:
            # Provide a simple fake client with a 'chat' attribute to avoid attribute errors
            class FakeClient:
                pass
            fake_client = FakeClient()
            fake_client.chat = mock.MagicMock()
            res = op.execute_via_ai_plan(fake_client, 'type code to reverse a list')
            self.assertTrue(res)
            mock_set_clip.assert_called_with(fake_content)

    @mock.patch('op.set_clipboard_and_paste')
    def test_type_a_topic_code_pure(self, mock_set_clip):
        # Simulate AI returning comments, markdown fences and code; we expect only pure code pasted
        raw = '```python\n# This is a comment\ndef rev(l):\n    return l[::-1]\n```\n// end'
        with mock.patch('op.generate_long_text', return_value=raw) as gen:
            class FakeClient:
                pass
            fake_client = FakeClient()
            fake_client.chat = mock.MagicMock()
            res = op.execute_via_ai_plan(fake_client, 'type a reverse list code')
            self.assertTrue(res)
            # Ensure pasted content contains only the function and no comment lines or fences
            called_arg = mock_set_clip.call_args[0][0]
            self.assertIn('def rev', called_arg)
            self.assertNotIn('# This is a comment', called_arg)
            self.assertNotIn('```', called_arg)

    def test_start_floating_window_without_tk(self):
        # Ensure start_floating_window returns False when tkinter unavailable
        with mock.patch('op.HAS_TK', False):
            res = op.start_floating_window()
            self.assertFalse(res)

    @mock.patch('op.tk')
    def test_start_and_stop_floating_window(self, mock_tk):
        # Mock Tk so no real window opens
        fake_root = mock.MagicMock()
        mock_tk.Tk.return_value = fake_root
        with mock.patch('op.HAS_TK', True):
            res = op.start_floating_window(title='Test', width=100, height=30)
        self.assertTrue(res)
        # stopping should destroy the root
        stopped = op.stop_floating_window()
        self.assertTrue(stopped)
        fake_root.destroy.assert_called()

    @mock.patch('op.tk')
    def test_floating_window_resizable_and_enter_binding(self, mock_tk):
        # Ensure the floating window allows resizing and entry binds Enter to submit
        fake_root = mock.MagicMock()
        fake_entry = mock.MagicMock()
        mock_tk.Tk.return_value = fake_root
        mock_tk.Entry.return_value = fake_entry
        with mock.patch('op.HAS_TK', True):
            res = op.start_floating_window(title='TestResizable', width=200, height=50)
        self.assertTrue(res)
        # resizable should be set to allow resizing
        fake_root.resizable.assert_called_with(True, True)
        # entry should have bind called for Enter
        fake_entry.bind.assert_any_call('<Return>', mock.ANY)

    def test_send_prompt_shows_typing_and_clears_and_refocuses(self):
        # Setup fake root.after to call immediately
        class FakeRoot:
            def after(self, ms, func):
                func()

        fake_entry = mock.MagicMock()
        op.FLOATING_ROOT = FakeRoot()
        op.FLOATING_ENTRY = fake_entry

        # Ensure execute_via_ai_plan returns True when called
        with mock.patch('op.execute_via_ai_plan', return_value=True) as mock_exec:
            res = op.send_prompt_from_ui('do something', run_in_thread=False)
            self.assertTrue(res)
            # Entry should have been set to 'Typing...' and disabled, then cleared and focused
            fake_entry.delete.assert_any_call(0, mock.ANY)
            fake_entry.insert.assert_any_call(0, 'Typing...')
            fake_entry.config.assert_any_call(state='disabled')
            fake_entry.config.assert_any_call(state='normal')
            fake_entry.focus_set.assert_called()

    def test_execute_via_ai_plan_focuses_entry_after_actions(self):
        # Fake root.after to call immediately
        class FakeRoot:
            def after(self, ms, func):
                func()

        fake_entry = mock.MagicMock()
        op.FLOATING_ROOT = FakeRoot()
        op.FLOATING_ENTRY = fake_entry

        with mock.patch('op.get_ai_response', return_value='ACTION: SLEEP 0'):
            res = op.execute_via_ai_plan(None, 'do a short sleep')
            self.assertTrue(res)
            fake_entry.focus_set.assert_called()

    def test_main_starts_floating_window_by_default(self):
        # Ensure main() attempts to start the floating window when FLOATING_WINDOW not set
        with mock.patch.dict('os.environ', {}, clear=True):
            with mock.patch('op.start_floating_window', return_value=True) as mock_start:
                # Patch create_nova and get_voice_input to force main() to exit quickly
                with mock.patch('op.create_nova', return_value=object()):
                    with mock.patch('op.get_voice_input', side_effect=KeyboardInterrupt):
                        try:
                            op.main()
                        except SystemExit:
                            pass
                mock_start.assert_called()

    def test_toggle_listening_via_helper(self):
        # default True -> toggle off -> on
        op.WAKE_WORD_ENABLED = True
        res = op.toggle_listening()
        self.assertFalse(res)
        self.assertFalse(op.WAKE_WORD_ENABLED)
        res = op.toggle_listening()
        self.assertTrue(res)
        self.assertTrue(op.WAKE_WORD_ENABLED)

    def test_set_floating_status_updates_label(self):
        # Simulate a root with after that immediately calls the callback
        class FakeRoot:
            def after(self, ms, func):
                func()

        fake_label = mock.MagicMock()
        op.FLOATING_ROOT = FakeRoot()
        op.FLOATING_STATUS_LABEL = fake_label
        res = op.set_floating_status('Listening...')
        self.assertTrue(res)
        fake_label.config.assert_called_with(text='Listening...')

    def test_send_prompt_calls_executor(self):
        # Ensure send_prompt_from_ui calls execute_via_ai_plan when run synchronously
        with mock.patch('op.execute_via_ai_plan', return_value=True) as mock_exec:
            with mock.patch('op.create_nova', return_value=object()) as mock_create:
                res = op.send_prompt_from_ui('open notepad and write hello', run_in_thread=False)
                self.assertTrue(res)
                mock_exec.assert_called()

    def test_generate_long_text_stream_progress(self):
        # Simulate a streaming client that yields small chunks
        class Delta:
            def __init__(self, content):
                self.content = content

        class Choice:
            def __init__(self, content):
                self.delta = Delta(content)

        class Chunk:
            def __init__(self, content):
                self.choices = [Choice(content)]

        class FakeClient:
            class chat:
                @staticmethod
                def completions_create(**kwargs):
                    # Not used
                    return None

            def __init__(self):
                pass

            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        # Return an iterable of chunks
                        for text in ['abc'*20, 'def'*20, 'ghi'*20]:
                            yield Chunk(text)

        client = FakeClient()
        # Capture stdout
        import io, sys
        old = sys.stdout
        sys.stdout = io.StringIO()
        res = op.generate_long_text(client, 'test prompt', language='en', progress=True, progress_step_chars=50)
        out = sys.stdout.getvalue()
        sys.stdout = old
        self.assertIn('[PROGRESS]', out)
        self.assertTrue(len(res) > 0)

    @mock.patch('op.time.sleep')
    @mock.patch('op.open_path')
    def test_execute_spotify_space_then_alt_tab(self, mock_open_path, mock_sleep):
        # Plan: OPEN spotify, PRESS space, PRESS alt+tab
        mock_open_path.return_value = True
        with mock.patch('op.get_ai_response', return_value="ACTION: OPEN spotify\nACTION: PRESS space\nACTION: PRESS alt+tab"):
            res = op.execute_via_ai_plan(None, 'play song')
            self.assertTrue(res)
            # Ensure sleep was called for startup and for post-space delay
            # Look for 1.2 and 0.6 sleeps in call args
            called_args = [c[0] for c in mock_sleep.call_args_list]
            self.assertTrue(any(len(a) and abs(a[0] - 1.2) < 1e-6 for a in called_args))
            self.assertTrue(any(len(a) and abs(a[0] - 0.6) < 1e-6 for a in called_args))

        @mock.patch.dict('os.environ', {'AUTO_ALT_TAB_AFTER_OPEN': 'true'})
        @mock.patch('op.subprocess.Popen')
        def test_auto_alt_tab_after_open_when_enabled(self, mock_popen):
            # Ensure that after successful open, alt+tab is invoked when enabled
            with mock.patch('op.HAS_PYAUTOGUI', True):
                with mock.patch('op.press_keys') as mock_press:
                    res = op.open_path('someapp')
                    # open_path will try subprocess and should return True (we mocked Popen)
                    self.assertTrue(res)
                    mock_press.assert_called_with('alt+tab')

        @mock.patch.dict('os.environ', {'AUTO_ALT_TAB_AFTER_OPEN': 'false'})
        @mock.patch('op.subprocess.Popen')
        def test_no_auto_alt_tab_when_disabled(self, mock_popen):
            with mock.patch('op.HAS_PYAUTOGUI', True):
                with mock.patch('op.press_keys') as mock_press:
                    res = op.open_path('someapp')
                    self.assertTrue(res)
                    mock_press.assert_not_called()

        @mock.patch.dict('os.environ', {'AUTO_RETURN_FOCUS_AFTER_OPEN': 'true'})
        @mock.patch('op.subprocess.Popen')
        def test_return_focus_after_open_when_enabled(self, mock_popen):
            # If return-focus is enabled, the floating root should be scheduled to be brought forward
            fake_root = mock.MagicMock()
            op.FLOATING_ROOT = fake_root
            op.FLOATING_ENTRY = mock.MagicMock()
            with mock.patch('op.HAS_PYAUTOGUI', False):
                res = op.open_path('someapp')
                self.assertTrue(res)
                # after() should be called to schedule bringing the window forward
                fake_root.after.assert_called()

if __name__ == '__main__':
    unittest.main()
