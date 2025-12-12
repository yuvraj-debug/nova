from unittest import mock
import op
fake = 'def foo():\n    return True'
with mock.patch('op.generate_long_text', return_value=fake):
    res = op.execute_via_ai_plan(object(), 'type code to reverse a list')
    print('result:', res)
    
print('done')
