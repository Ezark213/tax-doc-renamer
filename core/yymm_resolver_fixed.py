#!/usr/bin/env python3
"""
YYMM resolution system with UI-forced handling v5.3.5-assets-hotfix  
YYMM解決システム - FATAL回避とバッチ処理継続
"""

import re
import logging
from typing import Optional, Tuple, Set, Dict, Any
from dataclasses import dataclass
from enum import Enum

# 堅牢なUI YYMM抽出機能
from helpers.yymm_policy import require_ui_yymm, resolve_yymm_by_policy

logger = logging.getLogger(__name__)


class YYMMSource(Enum):
    """YYMM取得ソース"""
    UI_FORCED = "UI_FORCED"           # UI強制入力
    DOC_HEURISTIC = "DOC/HEURISTIC"  # 文書から検出
    AUTO_FORCED_OVERRIDE = "AUTO_FORCED_OVERRIDE"  # 自動推定（UI強制コード）
    UI_FALLBACK = "UI_FALLBACK"      # UIフォールバック
    UI_REQUIRED = "UI_REQUIRED"      # UI入力必須（未確定状態）
    NEEDS_UI = "NEEDS_UI"            # UI必要（処理継続）
    NONE = "NONE"                    # 検出失敗


@dataclass
class YYMMResult:
    """YYMM解決結果"""
    yymm: Optional[str]
    source: YYMMSource
    confidence: float = 1.0
    detection_method: str = ""
    
    @property
    def is_ui_required(self) -> bool:
        """UI入力が必要かどうか"""
        return self.source == YYMMSource.UI_REQUIRED
    
    @property
    def is_valid(self) -> bool:
        """有効なYYMMが確定しているか"""
        return self.yymm is not None and self.source != YYMMSource.UI_REQUIRED


# v5.3.4 UI強制入力コード（仕様書より）
UI_FORCED_CODES: Set[str] = {
    "6001",  # 固定資産台帳
    "6002",  # 一括償却資産明細表 
    "6003",  # 少額減価償却資産明細表
    "0000"   # 納付税額一覧表
}


class NeedsUserInputError(Exception):
    """UI入力が必要な場合のエラー（v5.3.5：FATAL回避）"""
    
    def __init__(self, code: str, file_id: str = "unknown", hint: Optional[str] = None):
        self.code = code
        self.file_id = file_id
        self.hint = hint
        super().__init__(f"YYMM required for code={code} file={file_id}")


def resolve_yymm(code: str, document: Any, ui_context: Dict[str, Any] = None, 
                 allow_auto_forced_codes: bool = False,
                 batch_mode: bool = True,
                 file_id: str = "unknown") -> YYMMResult:
    """
    YYMM解決（v5.3.5-assets-hotfix：FATAL回避対応）
    
    Args:
        code: 書類コード
        document: 文書オブジェクト
        ui_context: UI入力コンテキスト
        allow_auto_forced_codes: UI強制コードでも自動推定を許可
        batch_mode: バッチモード（FATAL回避）
        file_id: ファイルID
        
    Returns:
        YYMMResult: YYMM解決結果
        
    Raises:
        NeedsUserInputError: UI入力が必要（batch_mode=Falseのみ）
    """
    ui_context = ui_context or {}
    
    logger.debug("YYMM resolution started for code: %s (batch_mode=%s)", code, batch_mode)
    
    # v5.3.5-ui-robust: 新しいポリシーベースYYMM解決システム使用
    try:
        # 文書検出
        doc_result = _detect_from_document(document)
        detected_yymm = doc_result.yymm if doc_result else None
        
        # ポリシー適用（RunConfig中心システム対応）
        yymm_value, source_str = resolve_yymm_by_policy(
            class_code=code,
            ctx={"default_yymm": None, "run_config": None},  # RunConfig対応
            settings=ui_context,
            detected=detected_yymm  # 引数名修正
        )
        
        # ソース変換
        source_mapping = {
            "UI_FORCED": YYMMSource.UI_FORCED,
            "UI_FALLBACK": YYMMSource.UI_FALLBACK,
            "DOC/HEURISTIC": YYMMSource.DOC_HEURISTIC,
            "CONTEXT": YYMMSource.UI_FALLBACK,
            "NEEDS_UI": YYMMSource.NEEDS_UI,
            "NONE": YYMMSource.NONE
        }
        
        source = source_mapping.get(source_str, YYMMSource.NONE)
        
        if yymm_value:
            logger.info("[YYMM][POLICY_SUCCESS] code=%s value=%s source=%s file=%s", 
                       code, yymm_value, source_str, file_id)
            return YYMMResult(yymm_value, source, 1.0, "policy_based")
        elif source_str == "NEEDS_UI":
            # v5.3.5：FATALを投げず、NEEDS_UIで処理継続
            if batch_mode:
                logger.warning("[YYMM][NEEDS_UI] code=%s file=%s (堅牢UI抽出失敗)", code, file_id)
                return YYMMResult(None, YYMMSource.NEEDS_UI, 0.0, "policy_needs_ui")
            else:
                # 非バッチモードのみ例外
                raise NeedsUserInputError(code=code, file_id=file_id)
        
    except Exception as e:
        logger.error("[YYMM][POLICY_ERROR] code=%s file=%s error=%s", code, file_id, str(e))
        # フォールバック：従来の方式
        pass
    
    # フォールバック：従来の単純UI検索
    ui_yymm = ui_context.get('yymm') or ui_context.get('period_yymm')
    if ui_yymm and _validate_yymm_format(ui_yymm):
        source = YYMMSource.UI_FORCED if code in UI_FORCED_CODES else YYMMSource.UI_FALLBACK
        logger.info("UI input accepted (fallback): %s (source: %s) for code %s", ui_yymm, source.value, code)
        return YYMMResult(ui_yymm, source, 1.0, "ui_input_fallback")
    
    # UI強制コードでUI入力なしの場合
    if code in UI_FORCED_CODES:
        if batch_mode:
            logger.warning("[YYMM][NEEDS_UI] code=%s file=%s (UI強制コード・未入力）", code, file_id)
            return YYMMResult(None, YYMMSource.NEEDS_UI, 0.0, "awaiting_ui_input")
        else:
            # 非バッチモードのみ例外
            raise NeedsUserInputError(code=code, file_id=file_id)
    
    # 全て失敗（フォールバック後も検出できず）
    if batch_mode:
        logger.warning("[YYMM][NEEDS_UI] code=%s file=%s hint=%s", code, file_id, "推定不可")
        return YYMMResult(None, YYMMSource.NEEDS_UI, 0.0, "detection_failed")
    else:
        raise NeedsUserInputError(code=code, file_id=file_id, hint="推定不可")


def _resolve_ui_forced_legacy(code: str, ui_context: Dict[str, Any]) -> YYMMResult:
    """レガシー：UI強制処理（v5.3.5では非推奨）"""
    """UI強制入力コードの処理"""
    logger.debug("UI forced code detected: %s", code)
    
    # UI入力値を取得
    ui_yymm = ui_context.get('yymm') or ui_context.get('period_yymm')
    
    if ui_yymm and _validate_yymm_format(ui_yymm):
        logger.info("UI forced YYMM confirmed: %s for code %s", ui_yymm, code)
        return YYMMResult(ui_yymm, YYMMSource.UI_FORCED, 1.0, "ui_input")
    
    # UI入力が無いまたは無効な場合
    logger.warning("UI input required for code: %s", code)
    return YYMMResult(None, YYMMSource.UI_REQUIRED, 0.0, "awaiting_ui_input")


def _detect_from_document(document: Any) -> YYMMResult:
    """文書からのYYMM検出（v5.3.5：元号推定強化）"""
    if not document or not hasattr(document, 'text'):
        return YYMMResult(None, YYMMSource.NONE, 0.0, "no_text")
    
    text = document.text if isinstance(document.text, str) else str(document.text)
    filename = getattr(document, 'filename', '')
    
    # パターン1: 元号年からの推定（令和・平成）
    era_result = _detect_from_era_year(text)
    if era_result.yymm:
        return era_result
    
    # パターン2: 終期日付からの推定
    period_end_result = _detect_from_period_end(text)
    if period_end_result.yymm:
        return period_end_result
    
    # パターン3: 令和X年Y月形式（既存）
    reiwa_pattern = r'令和(\d{1,2})年(\d{1,2})月'
    match = re.search(reiwa_pattern, text)
    if match:
        year, month = match.groups()
        yymm = f"{int(year):02d}{int(month):02d}"
        if _validate_yymm_format(yymm):
            logger.debug("YYMM detected (Reiwa format): %s", yymm)
            return YYMMResult(yymm, YYMMSource.DOC_HEURISTIC, 0.9, "reiwa_pattern")
    
    # パターン4: YYMM直接形式（４桁数字）
    yymm_pattern = r'\b(\d{4})\b'
    matches = re.findall(yymm_pattern, text)
    for match in matches:
        if _validate_yymm_format(match) and _looks_like_period(match):
            logger.debug("YYMM detected (direct format): %s", match)
            return YYMMResult(match, YYMMSource.DOC_HEURISTIC, 0.7, "direct_pattern")
    
    # パターン5: 課税期間形式
    period_pattern = r'課税期間.*?(\d{2})年(\d{1,2})月.*?(\d{1,2})月'
    match = re.search(period_pattern, text)
    if match:
        year, start_month, end_month = match.groups()
        # 課税期間の終了月を使用
        yymm = f"{int(year):02d}{int(end_month):02d}"
        if _validate_yymm_format(yymm):
            logger.debug("YYMM detected (period format): %s", yymm)
            return YYMMResult(yymm, YYMMSource.DOC_HEURISTIC, 0.8, "period_pattern")
    
    # パターン6: ファイル名からの推定
    filename_result = _detect_from_filename(filename)
    if filename_result.yymm:
        return filename_result
    
    logger.debug("No YYMM pattern found in document")
    return YYMMResult(None, YYMMSource.NONE, 0.0, "no_pattern_found")


def _detect_from_era_year(text: str) -> YYMMResult:
    """元号年からYYMM推定（v5.3.5追加）"""
    # 令和X年 → 2018 + X年
    reiwa_match = re.search(r'令和(\d{1,2})年', text)
    if reiwa_match:
        reiwa_year = int(reiwa_match.group(1))
        western_year = 2018 + reiwa_year  # 令和元年=2019
        yy = western_year % 100
        # 資産・会計は01月固定（仕様書の命名例と整合）
        mm = 1
        yymm = f"{yy:02d}{mm:02d}"
        logger.debug("Era detection: 令和%d年 → %d年 → %s", reiwa_year, western_year, yymm)
        return YYMMResult(yymm, YYMMSource.DOC_HEURISTIC, 0.85, "era_reiwa")
    
    # 平成X年 → 1988 + X年
    heisei_match = re.search(r'平成(\d{1,2})年', text)
    if heisei_match:
        heisei_year = int(heisei_match.group(1))
        western_year = 1988 + heisei_year  # 平成元年=1989
        yy = western_year % 100
        mm = 1
        yymm = f"{yy:02d}{mm:02d}"
        logger.debug("Era detection: 平成%d年 → %d年 → %s", heisei_year, western_year, yymm)
        return YYMMResult(yymm, YYMMSource.DOC_HEURISTIC, 0.85, "era_heisei")
    
    return YYMMResult(None, YYMMSource.NONE, 0.0, "no_era")


def _detect_from_period_end(text: str) -> YYMMResult:
    """終期日付からYYMM推定（v5.3.5追加）"""
    # 自 YYYY/MM/DD 至 YYYY/MM/DD 形式
    period_pattern = r'自\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s*至\s*(\d{4})[/-](\d{1,2})[/-](\d{1,2})'
    match = re.search(period_pattern, text)
    if match:
        end_year = int(match.group(4))
        end_month = int(match.group(5))
        yy = end_year % 100
        mm = end_month
        yymm = f"{yy:02d}{mm:02d}"
        if _validate_yymm_format(yymm):
            logger.debug("Period end detection: %d/%d → %s", end_year, end_month, yymm)
            return YYMMResult(yymm, YYMMSource.DOC_HEURISTIC, 0.8, "period_end")
    
    return YYMMResult(None, YYMMSource.NONE, 0.0, "no_period_end")


def _detect_from_filename(filename: str) -> YYMMResult:
    """ファイル名からYYMM推定（v5.3.5追加）"""
    if not filename:
        return YYMMResult(None, YYMMSource.NONE, 0.0, "no_filename")
    
    # _YYYYMMDD_ 形式
    date_pattern = r'_(\d{4})(\d{2})(\d{2})_'
    match = re.search(date_pattern, filename)
    if match:
        year, month, day = match.groups()
        yy = int(year) % 100
        mm = int(month)
        yymm = f"{yy:02d}{mm:02d}"
        if _validate_yymm_format(yymm):
            logger.debug("Filename date detection: %s → %s", match.group(0), yymm)
            return YYMMResult(yymm, YYMMSource.DOC_HEURISTIC, 0.75, "filename_date")
    
    return YYMMResult(None, YYMMSource.NONE, 0.0, "no_filename_date")


def _get_ui_fallback(ui_context: Dict[str, Any]) -> YYMMResult:
    """UIフォールバック取得"""
    ui_yymm = ui_context.get('yymm') or ui_context.get('period_yymm')
    
    if ui_yymm and _validate_yymm_format(ui_yymm):
        logger.debug("UI fallback YYMM: %s", ui_yymm)
        return YYMMResult(ui_yymm, YYMMSource.UI_FALLBACK, 0.5, "ui_fallback")
    
    return YYMMResult(None, YYMMSource.NONE, 0.0, "no_ui_fallback")


def _validate_yymm_format(yymm: str) -> bool:
    """YYMM形式の妥当性検証"""
    if not yymm or not isinstance(yymm, str):
        return False
    
    # 4桁数字であること
    if not re.match(r'^\d{4}$', yymm):
        return False
    
    try:
        year = int(yymm[:2])
        month = int(yymm[2:])
        
        # 年: 01-99（令和元年-99年相当）
        # 月: 01-12
        return 1 <= year <= 99 and 1 <= month <= 12
    except ValueError:
        return False


def _looks_like_period(yymm_str: str) -> bool:
    """数字がYYMM期間らしく見えるかの判定"""
    try:
        year = int(yymm_str[:2])
        month = int(yymm_str[2:])
        
        # 令和年代らしい年（01-30程度が現実的）
        # 12月以下の妥当な月
        return 1 <= year <= 30 and 1 <= month <= 12
    except (ValueError, IndexError):
        return False


def is_ui_forced_code(code: str) -> bool:
    """UI強制入力コードかどうかを判定"""
    return code in UI_FORCED_CODES


def format_yymm_log(result: YYMMResult, code: str) -> str:
    """YYMMログの形式化（v5.3.5拡張）"""
    if result.source == YYMMSource.NEEDS_UI:
        return f"[YYMM][NEEDS_UI] code={code} 処理継続・後でUI入力必要"
    elif result.source == YYMMSource.AUTO_FORCED_OVERRIDE:
        return f"[YYMM][AUTO_FORCED_OVERRIDE] code={code} value={result.yymm} 自動推定適用"
    elif result.is_ui_required:
        return f"[YYMM][UI_REQUIRED] code={code} UI入力必須 source={result.source.value}"
    elif result.yymm:
        return f"[YYMM][POLICY] code={code} value={result.yymm} source={result.source.value}"
    else:
        return f"[YYMM][POLICY] code={code} 未確定 source={result.source.value}"


def create_ui_required_error(code: str, yymm_result: YYMMResult) -> NeedsUserInputError:
    """UI入力必要エラーの生成"""
    return NeedsUserInputError(code, "YYMM", yymm_result.source.value)


def get_ui_forced_codes() -> Set[str]:
    """UI強制コード一覧を取得"""
    return UI_FORCED_CODES.copy()


def audit_yymm_usage(yymm: str, source: YYMMSource, filename: str = "unknown") -> None:
    """YYMM使用監査ログ（v5.3.5-ui-robust拡張）"""
    audit_level = "INFO" if source in [YYMMSource.UI_FORCED, YYMMSource.DOC_HEURISTIC] else "WARNING"
    
    logger.info("[AUDIT][YYMM_USAGE] value=%s source=%s file=%s level=%s", 
               yymm, source.value, filename, audit_level)
    
    # 詳細監査情報
    if source == YYMMSource.UI_FORCED:
        logger.info("[AUDIT][UI_FORCED_SUCCESS] UI入力によりYYMM確定: %s", yymm)
    elif source == YYMMSource.AUTO_FORCED_OVERRIDE:
        logger.warning("[AUDIT][AUTO_OVERRIDE] UI強制コードを自動推定: %s (要確認)", yymm)
    elif source == YYMMSource.NEEDS_UI:
        logger.warning("[AUDIT][UI_REQUIRED] UI入力必須: file=%s", filename)
    elif source == YYMMSource.UI_FALLBACK:
        logger.info("[AUDIT][UI_FALLBACK] UIフォールバック: %s", yymm)
    elif source == YYMMSource.DOC_HEURISTIC:
        logger.info("[AUDIT][DOC_DETECTED] 文書から検出: %s", yymm)


def parse_batch_yymm_input(batch_input: str) -> Dict[str, str]:
    """バッチYYMM入力解析（v5.3.5追加）"""
    if not batch_input:
        return {}
    
    result = {}
    for pair in batch_input.split(','):
        if '=' in pair:
            code, yymm = pair.split('=', 1)
            code = code.strip()
            yymm = yymm.strip()
            if _validate_yymm_format(yymm):
                result[code] = yymm
                logger.debug("Batch YYMM: %s=%s", code, yymm)
            else:
                logger.warning("Invalid batch YYMM format: %s=%s", code, yymm)
    
    return result


if __name__ == "__main__":
    # テスト実行
    import sys
    from types import SimpleNamespace
    
    print("YYMM解決システム テスト")
    print("=" * 50)
    
    # ログ設定
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # テストドキュメント
    test_doc = SimpleNamespace(text="課税期間 令和7年4月1日から令和7年5月31日まで 消費税申告書")
    ui_ctx_with_yymm = {"yymm": "2508"}
    ui_ctx_empty = {}
    
    test_cases = [
        # UI強制コード（UI入力あり）
        ("6001", test_doc, ui_ctx_with_yymm, "固定資産台帳 - UI強制（入力済）"),
        
        # UI強制コード（UI入力なし）
        ("6002", test_doc, ui_ctx_empty, "一括償却資産 - UI強制（未入力）"),
        
        # 通常コード（文書検出）
        ("3001", test_doc, ui_ctx_empty, "消費税 - 文書検出"),
        
        # 通常コード（UIフォールバック）
        ("0001", SimpleNamespace(text="法人税申告書"), ui_ctx_with_yymm, "法人税 - UIフォールバック"),
        
        # 検出失敗
        ("1001", SimpleNamespace(text="都道府県税"), ui_ctx_empty, "地方税 - 検出失敗"),
    ]
    
    for code, doc, ui_ctx, description in test_cases:
        print(f"\n--- {description} ---")
        print(f"Code: {code}, UI Context: {ui_ctx}")
        
        try:
            result = resolve_yymm(code, doc, ui_ctx)
            print(f"Result: {result}")
            print(format_yymm_log(result, code))
            
            if result.is_ui_required:
                print("⚠️  UI入力が必要です")
            elif result.yymm:
                print(f"✅ YYMM確定: {result.yymm}")
            else:
                print("❌ YYMM確定失敗")
                
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    print("UI強制コード一覧:")
    for code in get_ui_forced_codes():
        print(f"  {code}: UI入力必須")
    
    print("\nテスト完了")