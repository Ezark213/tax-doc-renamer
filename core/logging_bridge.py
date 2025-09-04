#!/usr/bin/env python3
"""
Three-way consistency logging system v5.3.4
三者一致ログシステム - 表示/ログ/ファイル名の整合性保証
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .domain import resolve_domain, get_domain_description
from .overlay import OverlayResult

logger = logging.getLogger(__name__)


@dataclass
class ClassifyResult:
    """分類結果（三者一致対応）"""
    base_code: str                    # 元の分類コード（三者一致の起点）
    overlay_code: Optional[str]       # オーバーレイコード（地方税のみ）
    yymm: Optional[str]              # 期間
    yymm_source: Optional[str]       # 期間ソース
    title: str                       # 書類名
    confidence: float = 1.0          # 信頼度
    classification_method: str = "normal"  # 判定方法
    matched_keywords: list = None    # マッチしたキーワード
    meta: Dict[str, Any] = None      # メタデータ
    
    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []
        if self.meta is None:
            self.meta = {}
    
    @property
    def display_code(self) -> str:
        """表示用コード（三者一致: 常にbase_code）"""
        return self.base_code
    
    @property
    def final_code(self) -> str:
        """最終ファイル名用コード（オーバーレイ優先）"""
        return self.overlay_code or self.base_code
    
    @property
    def has_overlay(self) -> bool:
        """オーバーレイが適用されているか"""
        return self.overlay_code is not None and self.overlay_code != self.base_code


def create_title_mapping() -> Dict[str, str]:
    """書類コードから書類名へのマッピング"""
    return {
        # 国税系
        "0000": "納付税額一覧表",
        "0001": "法人税及び地方法人税申告書",
        "0002": "添付資料_法人税",
        "0003": "受信通知",
        "0004": "納付情報",
        
        # 地方税系（都道府県）
        "1001": "法人都道府県民税・事業税・特別法人事業税申告書",
        "1011": "法人都道府県民税・事業税・特別法人事業税申告書",  # 愛知県版
        "1021": "法人都道府県民税・事業税・特別法人事業税申告書",  # 福岡県版
        "1031": "法人都道府県民税・事業税・特別法人事業税申告書",  # 大阪府版
        "1041": "法人都道府県民税・事業税・特別法人事業税申告書",  # 神奈川県版
        "1003": "受信通知",
        "1013": "受信通知",  # 連番2番目
        "1023": "受信通知",  # 連番3番目
        "1004": "納付情報",
        
        # 地方税系（市町村）
        "2001": "法人市民税申告書",
        "2011": "法人市民税申告書",  # 福岡市版
        "2021": "法人市民税申告書",  # 大阪市版
        "2031": "法人市民税申告書",  # 横浜市版
        "2041": "法人市民税申告書",  # 名古屋市版
        "2003": "受信通知",
        "2013": "受信通知",  # 連番2番目
        "2023": "受信通知",  # 連番3番目
        "2004": "納付情報",
        
        # 消費税系
        "3001": "消費税及び地方消費税申告書",
        "3002": "添付資料_消費税",
        "3003": "受信通知",
        "3004": "納付情報",
        
        # 帳票系
        "5001": "決算書",
        "5002": "総勘定元帳",
        "5003": "補助簿等",
        "5004": "残高試算表",
        "5005": "仕訳帳",
        
        # 資産系
        "6001": "固定資産台帳",
        "6002": "一括償却資産明細表",
        "6003": "少額減価償却資産明細表",
        
        # その他
        "7001": "勘定科目別税区分集計表",
        "7002": "法人事業概況説明書",
        
        # 未分類
        "9999": "その他書類"
    }


def title_of(code: str) -> str:
    """書類コードから書類名を取得"""
    title_map = create_title_mapping()
    return title_map.get(code, f"不明書類_{code}")


def log_detailed_classification(result: ClassifyResult, filename: str) -> None:
    """
    詳細分類結果ログ出力（v5.3.4三者一致対応）
    
    仕様:
        - 「分類結果」は常にbase_codeを表示（表示/ログ/ファイル名の一致）
        - オーバーレイがある場合のみ別途表示
        - ノイズ抑制によりLOCAL_TAX以外ではオーバーレイ情報は出力しない
    """
    logger.info("=" * 60)
    logger.info("**詳細分類結果**")
    logger.info("ファイル名: %s", filename)
    
    # v5.3.4仕様: 表示は常にbase_code（三者一致の起点）
    display_title = title_of(result.display_code)
    logger.info("分類結果: %s_%s", result.display_code, display_title)
    logger.info("信頼度: %.2f", result.confidence)
    logger.info("判定方法: %s", result.classification_method)
    
    # オーバーレイ情報（地方税のみ、かつ実際に変化がある場合のみ）
    if result.has_overlay:
        logger.info("自治体変更版: %s_%s", result.overlay_code, title_of(result.overlay_code))
        overlay_reason = result.meta.get("overlay_reason", "unknown")
        logger.info("オーバーレイ理由: %s", overlay_reason)
    
    # マッチしたキーワードの詳細
    if result.matched_keywords:
        logger.info("マッチしたキーワード: %s", result.matched_keywords)
    
    # YYMM情報
    if result.yymm:
        logger.info("期間: %s (ソース: %s)", result.yymm, result.yymm_source or "不明")
    else:
        logger.warning("WARNING 期間未確定: ソース=%s", result.yymm_source or "不明")
    
    # ドメイン情報
    domain = resolve_domain(result.display_code)
    domain_desc = get_domain_description(result.display_code)
    logger.info("ドメイン: %s (%s)", domain, domain_desc)
    
    # メタデータ
    if result.meta:
        important_meta = {k: v for k, v in result.meta.items() 
                         if k in ['no_split', 'ui_required', 'classification_steps']}
        if important_meta:
            logger.info("メタデータ: %s", important_meta)
    
    logger.info("=" * 60)


def log_overlay_decision(base_code: str, overlay_result: OverlayResult, 
                        set_context: Any = None) -> None:
    """オーバーレイ決定ログ"""
    if overlay_result.skipped:
        # ノイズ抑制: 簡潔なスキップログのみ
        domain = resolve_domain(base_code)
        logger.info("overlay=SKIPPED(domain=%s)", domain)
    else:
        # 地方税: 詳細なオーバーレイ情報
        logger.info("自治体名付きコード生成: %s → %s", base_code, overlay_result.overlay_code)
        if set_context:
            logger.debug("Set context: prefecture=%s, city=%s", 
                        getattr(set_context, 'prefecture', None),
                        getattr(set_context, 'city', None))


def log_yymm_resolution(code: str, yymm: Optional[str], source: str, 
                       ui_required: bool = False) -> None:
    """YYMM解決ログ"""
    if ui_required:
        logger.warning("UI入力必須: code=%s (YYMM未確定)", code)
    elif yymm:
        logger.info("YYMM確定: %s (source=%s) for code=%s", yymm, source, code)
    else:
        logger.warning("WARNING YYMM未確定: source=%s for code=%s", source, code)


def log_filename_generation(result: ClassifyResult, final_filename: str) -> None:
    """ファイル名生成ログ"""
    logger.info("ファイル名生成:")
    logger.info("   表示コード: %s_%s", result.display_code, title_of(result.display_code))
    logger.info("   最終コード: %s_%s", result.final_code, title_of(result.final_code))
    logger.info("   期間: %s", result.yymm or "未確定")
    logger.info("   生成ファイル名: %s", final_filename)
    
    # 三者一致確認
    codes_match = result.display_code == result.final_code
    if codes_match:
        logger.info("OK 三者一致: 表示/ログ/ファイル名が一致")
    else:
        logger.info("オーバーレイ適用: 表示=%s, ファイル名=%s", 
                   result.display_code, result.final_code)


def log_split_reset(operation: str = "general") -> None:
    """分割リセットログ（v5.3.4新機能）"""
    if operation == "batch":
        logger.info("[reset] __split_ 一括処理開始 - 処理状態リセット")
    elif operation == "single":
        logger.info("[reset] __split_ 処理開始 - 分割状態リセット")
    else:
        logger.info("[reset] __split_ %s処理開始 - 状態リセット", operation)


def create_classification_result(base_code: str, title: str = None, 
                               confidence: float = 1.0, 
                               classification_method: str = "normal",
                               matched_keywords: list = None,
                               meta: Dict[str, Any] = None) -> ClassifyResult:
    """ClassifyResult作成ヘルパー"""
    return ClassifyResult(
        base_code=base_code,
        overlay_code=None,  # 後でオーバーレイ処理で設定
        yymm=None,          # 後でYYMM処理で設定
        yymm_source=None,
        title=title or title_of(base_code),
        confidence=confidence,
        classification_method=classification_method,
        matched_keywords=matched_keywords or [],
        meta=meta or {}
    )


if __name__ == "__main__":
    # テスト実行
    import sys
    
    print("三者一致ログシステム テスト")
    print("=" * 50)
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # テストケース
    test_cases = [
        # 国税（オーバーレイなし）
        ClassifyResult("0001", None, "2507", "DOC/HEURISTIC", 
                      "法人税及び地方法人税申告書", 0.95, "AND_condition", 
                      ["法人税申告", "確定申告"], {"domain": "NATIONAL_TAX"}),
        
        # 地方税（オーバーレイあり）
        ClassifyResult("1001", "1011", "2507", "DOC/HEURISTIC",
                      "法人都道府県民税・事業税・特別法人事業税申告書", 0.90, "normal",
                      ["都道府県民税", "事業税"], 
                      {"domain": "LOCAL_TAX", "overlay_reason": "PREF=愛知県"}),
    ]
    
    for i, result in enumerate(test_cases, 1):
        print(f"\n=== テストケース {i} ===")
        log_detailed_classification(result, f"test_file_{i}.pdf")
        
        if result.has_overlay:
            from .overlay import OverlayResult
            overlay_result = OverlayResult(result.overlay_code, result.meta.get("overlay_reason", ""))
            log_overlay_decision(result.base_code, overlay_result)
        
        final_filename = f"{result.final_code}_{result.title}_{result.yymm}.pdf"
        log_filename_generation(result, final_filename)
    
    print("\n" + "=" * 50)
    print("テスト完了")