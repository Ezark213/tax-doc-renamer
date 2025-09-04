#!/usr/bin/env python3
"""
Path compatibility helper for v5.3 hotfix
"""

def get_source_path(doc) -> str:
    """
    v5.3で origin_path に寄せたが、旧版が source_path を参照しているため互換アクセサを用意。
    どれも無い場合は AttributeError を投げる（Fail-softは呼び出し側で）。
    """
    for attr in ("origin_path", "source_path", "path", "temp_path"):
        if hasattr(doc, attr):
            val = getattr(doc, attr)
            if val:
                return val
    
    # 最後の手段：display_nameから推測
    if hasattr(doc, 'display_name') and doc.display_name:
        return doc.display_name
        
    raise AttributeError("No viable source path on document.")