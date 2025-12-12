import op


def demo_plan_execution():
    plan_text = '''ACTION: YOUTUBE_PLAY Saurav Joshi new blog
ACTION: SLEEP 2
ACTION: PRESS enter
ACTION: SLEEP 2
ACTION: CLICK left
ACTION: SLEEP 2
ACTION: CLICK left
'''
    plan_lines = [l.strip() for l in plan_text.splitlines() if l.strip()]
    i = 0
    executed = []
    while i < len(plan_lines):
        line = plan_lines[i]
        i += 1
        if not line.lower().startswith('action:'):
            continue
        action_str = line[7:].strip()
        parts = action_str.split(None, 1)
        action_type = parts[0].upper()
        action_param = parts[1] if len(parts) > 1 else ''
        if action_type == 'YOUTUBE_PLAY':
            status = op.play_youtube(action_param)
            executed.append(('YOUTUBE_PLAY', status, action_param))
            if status == 'playing':
                # skip followup UI steps
                while i < len(plan_lines):
                    nxt = plan_lines[i].lower()
                    if nxt.startswith('action: sleep') or nxt.startswith('action: press') or nxt.startswith('action: click') or nxt.startswith('action: wait_for_page'):
                        i += 1
                        continue
                    break
        else:
            executed.append((action_type, action_param))
    print('Executed actions:')
    for e in executed:
        print(e)


def test_resolve_instagram_inbox():
    kind, val = op.resolve_open_target(None, 'instagram chats')
    print('\nresolve_open_target for "instagram chats" ->', kind, val)
    assert kind == 'url' and 'direct/inbox' in val


if __name__ == '__main__':
    demo_plan_execution()
    test_resolve_instagram_inbox()
    print('All tests passed.')
