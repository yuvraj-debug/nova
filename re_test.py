import re
patterns = [r"^\s*type\s+code(?:\s+(.+))?$"]
strings = ['type code to reverse a list','type code','type code    foo','  type CODE bar']
for p in patterns:
    print('pattern:',p)
    for s in strings:
        m = re.match(p, s, flags=re.IGNORECASE)
        print('  ',repr(s),'->', bool(m), 'group1=', m.group(1) if m and m.group(1) else None)
