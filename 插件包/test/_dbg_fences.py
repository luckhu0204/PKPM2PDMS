# -*- coding: utf-8 -*-
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
doc = open('spec/CONTRACT.md', encoding='utf-8').read()
blocks = re.findall(r'```pml\r?\n(.*?)```', doc, re.S)
b = blocks[4]
for line in b.split('\n'):
    if 'define' in line or 'EXIST' in line or 'handle' in line or 'FAIL' in line:
        print(repr(line))
print('---')
print('sig in b:', 'define function !!pkpm2pdmsUniquename(!base is STRING) is STRING' in b)
print('has eq-op:', "if (!base eq '')" in b)
