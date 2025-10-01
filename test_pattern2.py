#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

text = """
7
0 1
1
9 9 0 , 0 0 0
9 1 , 8 9 0
9 1 , 8 9 0
9 1 , 8 9 0
7
8
"""

print("方法: 行ごとに処理")
print("="*60)

amounts = []
for line in text.split('\n'):
    # カンマを含む行のみ
    if ',' in line:
        # 空白とカンマを除去
        cleaned = line.replace(',', '').replace(' ', '').replace('\u3000', '').strip()
        if cleaned.isdigit() and len(cleaned) >= 3:
            amount = int(cleaned)
            print(f"行: '{line.strip()}' → {amount:,}円")
            amounts.append(amount)

print(f"\n抽出された金額: {amounts}")
print(f"重複チェック:")
from collections import Counter
counter = Counter(amounts)
for amount, count in counter.most_common():
    print(f"  {amount:,}円: {count}回")

if amounts:
    most_common = counter.most_common(1)
    if most_common[0][1] >= 2:
        print(f"\n✓ 重複金額（納付税額）: {most_common[0][0]:,}円")
    else:
        print(f"\n✓ 最後の金額: {amounts[-1]:,}円")
