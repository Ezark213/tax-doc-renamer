#!/usr/bin/env python3
"""
Robust UI YYMM extraction and policy enforcement
堅牢なUI YYMM取得とポリシー強制 - v5.3.5-ui-robust HOTFIX
"""
# -*- coding: utf-8 -*-
import re
import unicodedata
import logging
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)

# GUI必須コード（UI強制コード）- v5.3.5仕様維持
FORCE_UI_YYMM_CODES = {"6001", "6002", "6003", "0000"}  # 固定資産台帳、一括償却資産、少額減価償却資産、納付税額一覧表
ALWAYS_USE_UI_YYMM = True  # 🔧 Hotfix: 全書類でUI値を最優先（検出は使わない）

# UI YYMMの検索対象キー（優先度順）
_UI_YYMM_KEYS = [
    "yymm", "ui_yymm", "manual_yymm", "manual_input_yymm",
    "input_yymm", "yy_mm", "year_month_yymm", "period_yymm"
]


def _as_dict(obj: Any) -> Dict[str, Any]:
    """オブジェクトを辞書に変換（階層対応）"""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        result = obj.copy()
    else:
        # dataclass, SimpleNamespace等対応
        result = {}
        if hasattr(obj, '__dict__'):
            result.update(obj.__dict__)
        
        # 属性ベースアクセス
        for attr in dir(obj):
            if not attr.startswith('_') and not callable(getattr(obj, attr, None)):
                try:
                    result[attr] = getattr(obj, attr)
                except:
                    pass
    
    # ui サブツリーを平坦化
    ui_data = result.get("ui") or {}
    if isinstance(ui_data, dict):
        for k, v in ui_data.items():
            result[f"ui.{k}"] = v
    elif hasattr(ui_data, '__dict__'):
        for k, v in ui_data.__dict__.items():
            result[f"ui.{k}"] = v
    
    return result


def _norm(v):
    """YYMM正規化（シンプル版 - Hotfix）"""
    if v is None:
        return None
    s = unicodedata.normalize("NFKC", str(v)).strip()
    if re.fullmatch(r"\d{4}", s):          # 2508
        return s
    m = re.match(r"^(\d{2})[^\d]?(\d{2})$", s)  # 25/08, 25-08 等
    if m: 
        return m.group(1) + m.group(2)
    m = re.match(r"^(\d{4})[^\d]?(\d{2})$", s)  # 2025-08 → 2508
    if m: 
        return s[2:4] + s[-2:]
    return None

def _normalize_yymm(val: Any) -> Optional[str]:
    """YYMM正規化（後方互換用）"""
    return _norm(val)

def _extract_run_config(settings: Any, ctx: Any):
    """RunConfigを抽出（優先度順）"""
    # 1) RunConfigオブジェクトを直接検出
    if hasattr(settings, '__class__') and 'RunConfig' in str(type(settings)):
        return settings
    
    # 2) ctxからRunConfigを検出
    if isinstance(ctx, dict) and 'run_config' in ctx:
        return ctx['run_config']
    elif hasattr(ctx, 'run_config'):
        return ctx.run_config
    
    # 3) settingsからRunConfigを検出
    if isinstance(settings, dict) and 'run_config' in settings:
        return settings['run_config']
    elif hasattr(settings, 'run_config'):
        return settings.run_config
    
    # RunConfigが見つからない
    return None

def _get_ui_yymm(settings):
    """UI YYMM値を取得（RunConfig対応版 - Hotfix）"""
    v = None
    if isinstance(settings, dict):
        v = settings.get("yymm") or (settings.get("ui") or {}).get("yymm")
    else:
        # RunConfig.manual_yymm をチェック
        v = getattr(settings, "manual_yymm", None)
        if v is None:
            v = getattr(settings, "yymm", None)
        if v is None:
            ui = getattr(settings, "ui", None)
            if ui is not None:
                v = getattr(ui, "yymm", None)
    return _norm(v)


def require_ui_yymm(settings: Any) -> Tuple[str, str, Dict[str, Any]]:
    """
    UI YYMMを堅牢に取得（v5.3.5-ui-robust）
    
    Args:
        settings: UI設定オブジェクト（dict, dataclass, SimpleNamespace等）
        
    Returns:
        Tuple[str, str, Dict]: (YYMM値, ソース, メタデータ)
        
    Raises:
        ValueError: UI YYMMが見つからないか無効な場合
    """
    d = _as_dict(settings)
    candidates = []
    
    # 優先順序1: 明示的なキー
    for key in ["yymm", "ui_yymm", "manual_yymm"]:
        if key in d:
            candidates.append((key, d[key]))
    
    # 優先順序2: ui.yymm階層
    for ui_key in ["yymm", "ui_yymm", "manual_yymm"]:
        ui_full_key = f"ui.{ui_key}"
        if ui_full_key in d:
            candidates.append((ui_full_key, d[ui_full_key]))
    
    # 優先順序3: その他のキー
    for key in _UI_YYMM_KEYS:
        if key in d and key not in ["yymm", "ui_yymm", "manual_yymm"]:
            candidates.append((key, d[key]))
        
        ui_full_key = f"ui.{key}"
        if ui_full_key in d:
            candidates.append((ui_full_key, d[ui_full_key]))
    
    # 正規化と検証
    for key, raw_val in candidates:
        normalized = _normalize_yymm(raw_val)
        if normalized:
            meta = {
                "picked_key": key,
                "raw_value": raw_val,
                "normalized_value": normalized,
                "search_order": len([k for k, _ in candidates[:candidates.index((key, raw_val))+1]])
            }
            logger.info("[YYMM][UI_PICK] key=%s raw=%s norm=%s", key, raw_val, normalized)
            return normalized, "UI_FORCED", meta
    
    # 失敗時：詳細な検索結果をログ出力
    searched_keys = [key for key, _ in candidates]
    searched_values = [(key, val, type(val).__name__) for key, val in candidates]
    
    # 入力オブジェクト全体の内容もログ出力
    d_keys = list(d.keys()) if d else []
    d_sample = {k: (v, type(v).__name__) for k, v in (d or {}).items()}
    
    logger.error("[YYMM][UI_FORCED] Missing/invalid UI YYMM")
    logger.error("  searched_keys: %s", searched_keys)
    logger.error("  searched_values: %s", searched_values)
    logger.error("  available_keys: %s", d_keys)
    logger.error("  raw_settings_sample: %s", d_sample)
    
    raise ValueError(f"[YYMM][UI_FORCED] Missing/invalid UI YYMM. "
                    f"searched_keys={searched_keys} available_keys={d_keys}")

def resolve_yymm_by_policy(class_code: str, ctx: Any, settings: Any, detected: str = None, **kwargs) -> Tuple[Optional[str], str]:
    """
    RunConfig中心のYYMMポリシー解決（UI最優先システム + 後方互換性）
    
    Args:
        class_code: 分類コード
        ctx: コンテキストオブジェクト
        settings: 設定オブジェクト（RunConfigまたはUIContext）
        detected: 検出値（現在未使用）
        **kwargs: 後方互換性用
        
    Returns:
        Tuple[str, str]: (YYMM値, ソース)
    """
    code4 = class_code[:4] if class_code else ""
    
    # 🛡️ 後方互換性シム: detected_yymm= 引数を処理
    if 'detected_yymm' in kwargs:
        detected = kwargs.pop('detected_yymm')
        logger.warning(f"[BC] Using deprecated 'detected_yymm=' argument. Use 'detected=' instead.")
    
    # RunConfigを最優先で抽出
    run_config = _extract_run_config(settings, ctx)
    
    # 🚀 UI値最優先ショートカット（RunConfigベース）
    if run_config and run_config.has_manual_yymm():
        yymm = run_config.manual_yymm
        source = "UI"
        if hasattr(ctx, 'log'):
            ctx.log.info(f"[YYMM][POLICY] use={yymm} source={source} code={code4}")
        else:
            logger.info(f"[YYMM][POLICY] use={yymm} source={source} code={code4}")
        return yymm, source
    
    # 🚀 旧システム経由のUI値ショートカット（settingsベース）
    if hasattr(settings, "manual_yymm") and getattr(settings, "manual_yymm", None):
        yymm = settings.manual_yymm
        source = "UI"
        if hasattr(ctx, 'log'):
            ctx.log.info(f"[YYMM][POLICY] use={yymm} source={source} code={code4} [BC_PATH]")
        else:
            logger.info(f"[YYMM][POLICY] use={yymm} source={source} code={code4} [BC_PATH]")
        return yymm, source
    
    # UI値がない場合の処理
    # 1) UI必須コードのチェック
    if code4 in FORCE_UI_YYMM_CODES:
        raise ValueError(f"[FATAL][YYMM] UI value required but missing for {code4}")
    
    # 2) 従来のUI抽出を試行（フォールバック）
    ui_val = _get_ui_yymm(settings)
    if ui_val:
        source = "UI_FALLBACK"
        if hasattr(ctx, 'log'):
            ctx.log.info(f"[YYMM][POLICY] use={ui_val} source={source} code={code4}")
        else:
            logger.info(f"[YYMM][POLICY] use={ui_val} source={source} code={code4}")
        return ui_val, source
    
    # 3) 最終フォールバック：検出値またはNone
    if detected:
        if hasattr(ctx, 'log'):
            ctx.log.info(f"[YYMM][POLICY] use={detected} source=DETECTED code={code4}")
        else:
            logger.info(f"[YYMM][POLICY] use={detected} source=DETECTED code={code4}")
        return detected, "DETECTED"
    
    # 完全にYYMMが取得できない場合
    if hasattr(ctx, 'log'):
        ctx.log.info(f"[YYMM][POLICY] missing UI; leaving empty for code={code4}")
    else:
        logger.info(f"[YYMM][POLICY] missing UI; leaving empty for code={code4}")
    return None, "NONE"


def _validate_yymm(yymm: str) -> bool:
    """YYMM形式妥当性検証"""
    if not yymm or not isinstance(yymm, str):
        return False
    
    if not re.match(r'^\d{4}$', yymm):
        return False
    
    try:
        year = int(yymm[:2])
        month = int(yymm[2:])
        return 1 <= year <= 99 and 1 <= month <= 12
    except ValueError:
        return False

def log_yymm_decision(class_code: str, yymm: str, source: str, logger=None):
    """YYMM決定をログ出力（INFO/AUDIT/FATAL粒度対応）"""
    code4 = class_code[:4] if class_code else ""
    
    if logger:
        # INFO: 成功した決定
        logger.info(f"[YYMM][POLICY] code={code4} use={yymm} source={source}")
        
        # AUDIT: 監査用詳細ログ
        if source in ("UI_FORCED", "UI"):
            logger.info(f"[AUDIT][YYMM] source={source} value={yymm} validation=PASSED code={code4}")
        elif source in ("DOC/HEURISTIC", "OCR"):
            logger.info(f"[AUDIT][YYMM] source=DETECTED value={yymm} validation=PASSED code={code4}")
        else:
            logger.info(f"[AUDIT][YYMM] source={source} value={yymm} validation=PASSED code={code4}")
    else:
        print(f"[YYMM][POLICY] code={code4} use={yymm} source={source}")

def log_yymm_fatal(class_code: str, error_message: str, logger=None):
    """FATAL レベルのYYMMエラーログ"""
    code4 = class_code[:4] if class_code else ""
    
    if logger:
        logger.error(f"[FATAL][YYMM] {error_message} code={code4}")
    else:
        print(f"[FATAL][YYMM] {error_message} code={code4}")

def log_yymm_audit(event_type: str, details: dict, logger=None):
    """AUDIT レベルの詳細ログ"""
    details_str = " ".join(f"{k}={v}" for k, v in details.items())
    
    if logger:
        logger.info(f"[AUDIT][YYMM] {event_type} {details_str}")
    else:
        print(f"[AUDIT][YYMM] {event_type} {details_str}")

def validate_policy_result(yymm: str, source: str, class_code: str = None) -> bool:
    """ポリシー適用結果の検証"""
    if not _validate_yymm(yymm):
        return False
    
    # UI強制コードの場合はUI由来であることを確認
    if class_code and class_code[:4] in FORCE_UI_YYMM_CODES:
        return source in ("UI_FORCED", "UI_FALLBACK")
    
    return True