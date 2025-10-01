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

print("テキスト:")
print(text)
print("\n" + "="*60)

# パターン1: 現在のパターン
pattern1 = r'([\d\s]+,[\d\s,]+)'
matches1 = re.findall(pattern1, text)
print(f"\nパターン1: {pattern1}")
print(f"マッチ: {matches1}")

# パターン2: 数字と空白とカンマの組み合わせ（より緩い）
pattern2 = r'([\d\s,]+)'
matches2 = re.findall(pattern2, text)
print(f"\nパターン2: {pattern2}")
print(f"マッチ数: {len(matches2)}")
for i, m in enumerate(matches2[:10]):
    cleaned = m.replace(',', '').replace(' ', '').replace('\n', '').replace('\u3000', '')
    if cleaned and len(cleaned) >= 3:
        print(f"  {i+1}. '{m.strip()}' → {cleaned}")

# パターン3: 連続する数字（空白区切り）+ カンマ
pattern3 = r'[\d\s]+,[\d\s,]+'
matches3 = re.findall(pattern3, text)
print(f"\nパターン3: {pattern3}")
print(f"マッチ: {matches3}")
for m in matches3:
    cleaned = m.replace(',', '').replace(' ', '').replace('\u3000', '')
    print(f"  '{m}' → {cleaned}")
