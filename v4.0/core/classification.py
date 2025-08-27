#!/usr/bin/env python3
"""
書類分類エンジン v4.0
高精度書類種別判定システム（詳細ログ対応版）
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
import datetime

@dataclass
class ClassificationStep:
    """分類の1ステップを表すデータクラス"""
    document_type: str
    score: float
    matched_keywords: List[str]
    excluded: bool
    exclude_reason: str = ""

@dataclass
class ClassificationResult:
    """分類結果を表すデータクラス"""
    document_type: str
    confidence: float
    matched_keywords: List[str]
    classification_method: str
    debug_steps: List[ClassificationStep] = field(default_factory=list)
    processing_log: List[str] = field(default_factory=list)

class DocumentClassifier:
    """書類分類のメインクラス"""
    
    def __init__(self, debug_mode: bool = False, log_callback: Optional[Callable[[str], None]] = None):
        """初期化
        
        Args:
            debug_mode: デバッグモードの有効化
            log_callback: ログ出力のコールバック関数
        """
        self.debug_mode = debug_mode
        self.log_callback = log_callback
        self.current_filename = ""
        self.processing_log = []
        # 書類分類の優先度付きキーワード辞書
        self.classification_rules = {
            # 申告書類（0000番台）
            "0000_納付税額一覧表": {
                "priority": 2,  # 優先度を下げて最優先キーワードを優先
                "exact_keywords": [],  # 通常分類では空にして最優先のみで検出
                "partial_keywords": [],
                "exclude_keywords": []
            },
            "0001_法人税及び地方法人税申告書": {
                "priority": 15,
                "exact_keywords": [
                    "法人税及び地方法人税申告書",
                    "内国法人の確定申告",
                    "内国法人の確定申告(青色)",
                    "法人税申告書別表一",
                    "申告書第一表",
                    "事業年度分の法人税申告書",
                    "税額控除超過額",
                    "控除した金額"
                ],
                "partial_keywords": ["法人税申告", "内国法人", "確定申告", "青色申告", "事業年度分", "税額控除"],
                "exclude_keywords": ["添付資料", "資料", "別添", "参考", "イメージ添付"],
                "filename_keywords": ["内国法人", "確定申告", "青色"]
            },
            "0002_添付資料_法人税": {
                "priority": 10,
                "exact_keywords": [
                    "法人税 添付資料", 
                    "添付資料 法人税",
                    "イメージ添付書類(法人税申告)",
                    "イメージ添付書類 法人税",
                    "添付書類 法人税"
                ],
                "partial_keywords": ["添付資料", "法人税 資料", "申告資料", "イメージ添付"],
                "exclude_keywords": ["消費税申告", "法人消費税", "消費税"],
                "filename_keywords": ["法人税申告", "法人税", "内国法人"]
            },
            "0003_受信通知_法人税": {
                "priority": 9,
                "exact_keywords": ["法人税 受信通知", "受信通知 法人税"],
                "partial_keywords": ["受信通知", "国税電子申告"],
                "exclude_keywords": ["消費税", "地方税"]
            },
            "0004_納付情報_法人税": {
                "priority": 9,
                "exact_keywords": ["法人税 納付情報", "納付情報 法人税"],
                "partial_keywords": ["納付情報", "納付書", "国税 納付"],
                "exclude_keywords": ["消費税", "地方税"]
            },
            
            # 都道府県関連（1000番台）
            "1001_都道府県_法人都道府県民税・事業税・特別法人事業税": {
                "priority": 11,
                "exact_keywords": [
                    "法人都道府県民税・事業税・特別法人事業税申告書",
                    "法人事業税申告書",
                    "都道府県民税申告書"
                ],
                "partial_keywords": [
                    "都道府県民税", "法人事業税", "特別法人事業税",
                    "道府県民税", "事業税", "県税事務所",
                    "都税事務所", "年400万円以下", "年月日から年月日までの"
                ],
                "exclude_keywords": ["市町村", "市民税", "市役所", "町役場", "村役場"],
                "filename_keywords": ["県税事務所", "都税事務所"]
            },
            "1003_受信通知_都道府県": {
                "priority": 8,
                "exact_keywords": ["都道府県 受信通知"],
                "partial_keywords": ["受信通知", "地方税電子申告"],
                "exclude_keywords": ["市町村", "国税"]
            },
            "1004_納付情報_都道府県": {
                "priority": 8,
                "exact_keywords": ["都道府県 納付情報"],
                "partial_keywords": ["納付情報", "地方税 納付"],
                "exclude_keywords": ["市町村", "国税"]
            },
            
            # 市町村関連（2000番台）
            "2001_市町村_法人市民税": {
                "priority": 9,
                "exact_keywords": ["法人市民税申告書", "市民税申告書"],
                "partial_keywords": ["法人市民税", "市町村民税"],
                "exclude_keywords": ["都道府県", "事業税"]
            },
            "2003_受信通知_市町村": {
                "priority": 8,
                "exact_keywords": ["市町村 受信通知"],
                "partial_keywords": ["受信通知", "地方税電子申告"],
                "exclude_keywords": ["都道府県", "国税"]
            },
            "2004_納付情報_市町村": {
                "priority": 8,
                "exact_keywords": ["市町村 納付情報"],
                "partial_keywords": ["納付情報", "地方税 納付"],
                "exclude_keywords": ["都道府県", "国税"]
            },
            
            # 消費税関連（3000番台）
            "3001_消費税及び地方消費税申告書": {
                "priority": 15,
                "exact_keywords": [
                    "消費税申告書", 
                    "消費税及び地方消費税申告書",
                    "消費税及び地方消費税申告(一般・法人)",
                    "消費税申告(一般・法人)",
                    "課税期間分の消費税及び",
                    "基準期間の",
                    "現金主義会計の適用"
                ],
                "partial_keywords": ["消費税申告", "地方消費税申告", "消費税申告書", "課税期間分", "基準期間"],
                "exclude_keywords": ["添付資料", "イメージ添付", "資料"],
                "filename_keywords": ["消費税及び地方消費税申告", "消費税申告", "地方消費税申告"]
            },
            "3002_添付資料_消費税": {
                "priority": 10,
                "exact_keywords": [
                    "消費税 添付資料", 
                    "添付資料 消費税",
                    "イメージ添付書類(法人消費税申告)",
                    "イメージ添付書類 消費税",
                    "添付書類 消費税"
                ],
                "partial_keywords": ["添付資料", "消費税 資料", "イメージ添付", "添付書類"],
                "exclude_keywords": ["消費税及び地方消費税申告", "消費税申告書", "申告(一般・法人)", "法人税申告", "内国法人", "確定申告"],
                "filename_keywords": ["イメージ添付書類", "添付書類", "法人消費税"]
            },
            "3003_受信通知_消費税": {
                "priority": 9,
                "exact_keywords": ["消費税 受信通知", "受信通知 消費税"],
                "partial_keywords": ["受信通知", "国税電子申告"],
                "exclude_keywords": ["法人税", "地方税"]
            },
            "3004_納付情報_消費税": {
                "priority": 9,
                "exact_keywords": ["消費税 納付情報", "納付情報 消費税"],
                "partial_keywords": ["納付情報", "納付書"],
                "exclude_keywords": ["法人税", "地方税"]
            },
            
            # 会計書類（5000番台）
            "5001_決算書": {
                "priority": 9,
                "exact_keywords": ["決算書", "貸借対照表", "損益計算書"],
                "partial_keywords": ["決算", "B/S", "P/L"],
                "exclude_keywords": []
            },
            "5002_総勘定元帳": {
                "priority": 15,
                "exact_keywords": ["総勘定元帳"],
                "partial_keywords": ["総勘定", "元帳"],
                "exclude_keywords": ["補助元帳", "補助"]
            },
            "5003_補助元帳": {
                "priority": 9,
                "exact_keywords": ["補助元帳"],
                "partial_keywords": ["補助元帳", "補助"],
                "exclude_keywords": ["総勘定"]
            },
            "5004_残高試算表": {
                "priority": 9,
                "exact_keywords": ["残高試算表", "試算表"],
                "partial_keywords": ["残高試算", "試算表"],
                "exclude_keywords": []
            },
            "5005_仕訳帳": {
                "priority": 9,
                "exact_keywords": ["仕訳帳"],
                "partial_keywords": ["仕訳"],
                "exclude_keywords": []
            },
            
            # 固定資産関連（6000番台）
            "6001_固定資産台帳": {
                "priority": 9,
                "exact_keywords": ["固定資産台帳"],
                "partial_keywords": ["固定資産台帳", "資産台帳"],
                "exclude_keywords": []
            },
            "6002_一括償却資産明細表": {
                "priority": 15,
                "exact_keywords": ["一括償却資産明細表"],
                "partial_keywords": ["一括償却", "償却資産明細"],
                "exclude_keywords": ["少額"]
            },
            "6003_少額減価償却資産明細表": {
                "priority": 15,
                "exact_keywords": ["少額減価償却資産明細表"],
                "partial_keywords": ["少額減価償却", "少額償却"],
                "exclude_keywords": ["一括"]
            },
            
            # 税区分関連（7000番台）- 重要な修正
            "7001_勘定科目別税区分集計表": {
                "priority": 10,
                "exact_keywords": ["勘定科目別税区分集計表"],
                "partial_keywords": ["勘定科目別税区分", "勘定科目別", "科目別税区分"],
                "exclude_keywords": []
            },
            "7002_税区分集計表": {
                "priority": 9,
                "exact_keywords": ["税区分集計表"],
                "partial_keywords": ["税区分集計", "区分集計"],
                "exclude_keywords": ["勘定科目別", "科目別"]  # 重要：勘定科目別を含む場合は除外
            }
        }

    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # 内部ログリストに追加
        self.processing_log.append(log_entry)
        
        # コールバックがあれば呼び出し
        if self.log_callback:
            self.log_callback(log_entry)
        
        # デバッグモードの場合はコンソール出力
        if self.debug_mode:
            print(log_entry)

    def _log_debug(self, message: str):
        """デバッグレベルのログ"""
        if self.debug_mode:
            self._log(message, "DEBUG")

    def _log_classification_step(self, doc_type: str, score: float, keywords: List[str], excluded: bool = False, exclude_reason: str = ""):
        """分類ステップのログ"""
        status = "除外" if excluded else f"スコア:{score:.1f}"
        keywords_str = ", ".join(keywords) if keywords else "なし"
        reason_str = f" ({exclude_reason})" if exclude_reason else ""
        
        self._log_debug(f"  → {doc_type}: {status}, キーワード:[{keywords_str}]{reason_str}")

    def _check_highest_priority_keywords(self, text: str, filename: str, file_path: Optional[str] = None) -> Optional[ClassificationResult]:
        """最優先キーワードをチェックして即座に分類を決定"""
        combined_text = f"{text} {filename}"
        
        # 最優先分類キーワード（優先度順）
        highest_priority_keywords = {
            # 納付税額一覧表（最高優先度 - 2つのキーワード要件）
            "納付税額一覧表": {
                "document_type": "0000_納付税額一覧表",
                "required_keywords": ["納付税額一覧表", "既納付額"],
                "match_type": "all",  # すべてのキーワードが必要
                "priority": 100
            },
            # 総勘定元帳（最高優先度 - 1ページ目限定）
            "総勘定元帳": {
                "document_type": "5002_総勘定元帳",
                "required_keywords": ["総勘定元帳"],
                "match_type": "any",  # いずれかのキーワードで可
                "priority": 100,
                "page_specific": True,  # 1ページ目のみ適用
                "target_page": 1
            },
            # 少額減価償却資産明細表（最高優先度）
            "少額減価償却資産明細表": {
                "document_type": "6003_少額減価償却資産明細表",
                "required_keywords": ["少額減価償却資産明細表"],
                "match_type": "any",
                "priority": 100
            },
            # 一括償却資産明細表（最高優先度）
            "一括償却資産明細表": {
                "document_type": "6002_一括償却資産明細表",
                "required_keywords": ["一括償却資産明細表"],
                "match_type": "any",
                "priority": 100
            },
            # 消費税添付資料（最高優先度 - 2つのキーワード要件）
            "消費税添付資料": {
                "document_type": "3002_添付資料",
                "required_keywords": ["添付書類送付書", "消費税及び"],
                "match_type": "all",  # 両方のキーワードが必要
                "priority": 100
            },
            # 法人税添付資料（最高優先度 - 2つのキーワード要件）
            "法人税添付資料": {
                "document_type": "0002_添付資料",
                "required_keywords": ["添付書類送付書", "内国法人の確定申告"],
                "match_type": "all",  # 両方のキーワードが必要
                "priority": 115
            },
            # 消費税申告書（高優先度 - 複数キーワードの組み合わせ）
            "消費税申告": {
                "document_type": "3001_消費税及び地方消費税申告書",
                "required_keywords": [
                    "課税期間分の消費税及び",
                    "基準期間の",
                    "現金主義会計の適用",
                    "消費税及び地方消費税申告(一般・法人)",
                    "消費税申告(一般・法人)"
                ],
                "match_type": "any",
                "priority": 90
            },
            # 法人税申告書（最高優先度 - 複数キーワードの組み合わせ）
            "法人税申告": {
                "document_type": "0001_法人税及び地方法人税申告書",
                "required_keywords": [
                    "事業年度分の法人税申告書",
                    "事業年度分の法人税",
                    "控除した金額",
                    "控除しきれなかった金額",
                    "課税留保金額",
                    "適用額明細書",
                    "中間申告分の地方法人税額",
                    "中間申告分の法人税額"
                ],
                "match_type": "any",
                "priority": 110  # 総勘定元帳より高く設定
            },
            # 都道府県書類（10系統）
            "都道府県書類": {
                "document_type": "1001_都道府県_法人都道府県民税・事業税・特別法人事業税",
                "required_keywords": [
                    "県税事務所",
                    "都税事務所", 
                    "道府県民税",
                    "法人事業税",
                    "特別法人事業税",
                    "年400万円以下",
                    "年月日から年月日までの"
                ],
                "match_type": "any",
                "priority": 105,
                "exclude_keywords": ["添付書類送付書"]  # 法人税添付資料との区別
            },
            # 市町村書類（20系統）
            "市町村書類": {
                "document_type": "2001_市町村_法人市民税",
                "required_keywords": [
                    "市役所",
                    "町役場",
                    "村役場",
                    "法人市民税",
                    "市町村民税",
                    "市民税申告書"
                ],
                "match_type": "any",
                "priority": 95
            }
        }
        
        self._log("最優先キーワード判定開始")
        
        # 優先度順でチェック
        for rule_name, rule_info in sorted(highest_priority_keywords.items(), 
                                         key=lambda x: x[1]["priority"], reverse=True):
            
            matched_keywords = []
            
            # ページ特定ルールの場合、該当ページのテキストを取得
            text_to_search = combined_text
            if rule_info.get("page_specific", False) and file_path:
                target_page = rule_info.get("target_page", 1)
                page_text = self._extract_page_text(file_path, target_page)
                if page_text:
                    text_to_search = f"{page_text} {filename}"
                    self._log_debug(f"ページ{target_page}特定ルール適用: {rule_name}")
                else:
                    self._log_debug(f"ページ{target_page}のテキスト抽出失敗 - ルールをスキップ: {rule_name}")
                    continue
            
            # 新フォーマットの場合
            if "required_keywords" in rule_info:
                keywords_to_check = rule_info["required_keywords"]
                match_type = rule_info.get("match_type", "any")
                
                for keyword in keywords_to_check:
                    if keyword in text_to_search:
                        matched_keywords.append(keyword)
                
                # マッチ条件判定
                match_success = False
                if match_type == "all":
                    # すべてのキーワードが必要
                    match_success = len(matched_keywords) == len(keywords_to_check)
                else:  # match_type == "any"
                    # いずれかのキーワードで可
                    match_success = len(matched_keywords) > 0
                    
            else:
                # 旧フォーマットとの互換性
                for keyword in rule_info.get("keywords", []):
                    if keyword in combined_text:
                        matched_keywords.append(keyword)
                match_success = len(matched_keywords) > 0
            
            # キーワードマッチした場合
            if match_success:
                self._log(f"最優先キーワード検出: {rule_name} → {rule_info['document_type']}")
                self._log_debug(f"マッチしたキーワード: {matched_keywords}")
                if "match_type" in rule_info:
                    self._log_debug(f"マッチタイプ: {rule_info['match_type']}")
                
                return ClassificationResult(
                    document_type=rule_info["document_type"],
                    confidence=1.0,  # 最優先なので信頼度100%
                    matched_keywords=matched_keywords,
                    classification_method="highest_priority_keyword",
                    debug_steps=[],
                    processing_log=self.processing_log.copy()
                )
        
        self._log_debug("最優先キーワードマッチなし - 通常分類処理に移行")
        return None

    def _extract_page_text(self, file_path: str, page_number: int) -> Optional[str]:
        """指定されたページのテキストを抽出
        
        Args:
            file_path: PDFファイルパス
            page_number: ページ番号（1から開始）
            
        Returns:
            ページのテキスト、エラーの場合はNone
        """
        try:
            import fitz
            doc = fitz.open(file_path)
            
            # ページ番号調整（1から開始 → 0から開始）
            page_index = page_number - 1
            
            if page_index >= doc.page_count or page_index < 0:
                doc.close()
                self._log_debug(f"ページ{page_number}は存在しません（総ページ数: {doc.page_count}）")
                return None
                
            page = doc[page_index]
            text = page.get_text()
            doc.close()
            
            self._log_debug(f"ページ{page_number}テキスト抽出成功（{len(text)}文字）")
            return text
            
        except Exception as e:
            self._log_debug(f"ページ{page_number}テキスト抽出エラー: {e}")
            return None

    def classify_document(self, text: str, filename: str = "", file_path: Optional[str] = None) -> ClassificationResult:
        """書類を分類（詳細ログ対応版）"""
        self.processing_log = []  # ログをリセット
        self.current_filename = filename
        
        self._log(f"書類分類開始: {filename}")
        
        # テキストの前処理
        text_cleaned = self._preprocess_text(text)
        filename_cleaned = self._preprocess_text(filename)
        
        self._log_debug(f"入力テキスト長: {len(text)} → 前処理後: {len(text_cleaned)}")
        self._log_debug(f"ファイル名: {filename} → 前処理後: {filename_cleaned}")
        
        # 抽出テキストの一部を表示（デバッグ用）
        if text_cleaned:
            preview = text_cleaned[:200] + "..." if len(text_cleaned) > 200 else text_cleaned
            self._log_debug(f"テキスト内容: {preview}")
        
        # 最優先キーワード判定（新機能）
        priority_result = self._check_highest_priority_keywords(text_cleaned, filename_cleaned, file_path)
        if priority_result:
            return priority_result
        
        best_match = None
        best_score = 0
        best_keywords = []
        best_method = "keyword_matching"
        debug_steps = []
        
        self._log("分類ルール評価開始")
        
        # 各分類ルールに対してスコア計算
        for doc_type, rules in self.classification_rules.items():
            self._log_debug(f"評価中: {doc_type} (優先度: {rules.get('priority', 5)})")
            
            # テキストとファイル名を分けてスコア計算
            text_score, text_keywords = self._calculate_score(text_cleaned, rules, "テキスト")
            filename_score, filename_keywords = self._calculate_filename_score(filename_cleaned, rules)
            
            # 総合スコア（ファイル名を重視）
            total_score = text_score + (filename_score * 1.5)
            combined_keywords = text_keywords + filename_keywords
            
            # 除外判定チェック
            excluded = (text_score == 0 and len(rules.get("exclude_keywords", [])) > 0) or \
                      (filename_score == 0 and len(rules.get("exclude_keywords", [])) > 0)
            exclude_reason = ""
            if excluded:
                # 除外理由を特定
                for exclude_keyword in rules.get("exclude_keywords", []):
                    if exclude_keyword in text_cleaned or exclude_keyword in filename_cleaned:
                        exclude_reason = f"除外キーワード '{exclude_keyword}' を検出"
                        break
            
            # デバッグステップ記録
            step = ClassificationStep(
                document_type=doc_type,
                score=total_score,
                matched_keywords=combined_keywords,
                excluded=excluded,
                exclude_reason=exclude_reason
            )
            debug_steps.append(step)
            
            # ログ出力
            if excluded:
                self._log_classification_step(doc_type, 0, [], True, exclude_reason)
            else:
                self._log_classification_step(doc_type, total_score, combined_keywords)
                if text_score > 0:
                    self._log_debug(f"    - テキストスコア: {text_score:.1f} (キーワード: {text_keywords})")
                if filename_score > 0:
                    self._log_debug(f"    - ファイル名スコア: {filename_score:.1f} × 1.5 = {filename_score * 1.5:.1f} (キーワード: {filename_keywords})")
            
            # 最高スコア更新
            if not excluded and total_score > best_score:
                old_best = best_match
                best_score = total_score
                best_match = doc_type
                best_keywords = combined_keywords
                self._log_debug(f"    新たな最高スコア! {old_best} → {doc_type}")
        
        # 信頼度を計算（0.0-1.0）
        confidence = min(best_score / 15.0, 1.0)
        
        self._log(f"最終結果: {best_match}, スコア: {best_score:.1f}, 信頼度: {confidence:.2f}")
        
        # 分類できない場合のデフォルト
        if not best_match or confidence < 0.3:
            old_match = best_match
            best_match = "0000_未分類"
            confidence = 0.0
            best_method = "default"
            self._log(f"信頼度不足により未分類に変更: {old_match} → {best_match}")
        
        result = ClassificationResult(
            document_type=best_match,
            confidence=confidence,
            matched_keywords=best_keywords,
            classification_method=best_method,
            debug_steps=debug_steps,
            processing_log=self.processing_log.copy()
        )
        
        self._log("書類分類完了")
        return result

    def _preprocess_text(self, text: str) -> str:
        """テキストの前処理"""
        if not text:
            return ""
        
        # 不要な空白・改行を除去
        cleaned = re.sub(r'\s+', ' ', text)
        
        # 全角英数字を半角に変換
        cleaned = cleaned.translate(str.maketrans(
            '０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ',
            '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        ))
        
        return cleaned.strip()

    def _calculate_score(self, text: str, rules: Dict, source: str = "") -> Tuple[float, List[str]]:
        """分類ルールに基づいてスコアを計算（詳細ログ対応版）"""
        score = 0
        matched_keywords = []
        priority = rules.get("priority", 5)
        
        # 除外キーワードチェック（優先）
        for exclude_keyword in rules.get("exclude_keywords", []):
            if exclude_keyword in text:
                self._log_debug(f"    除外: {source}除外キーワード検出: '{exclude_keyword}'")
                return 0, []  # 除外キーワードが含まれている場合はスコア0
        
        # 完全一致キーワード（高スコア）
        for exact_keyword in rules.get("exact_keywords", []):
            if exact_keyword in text:
                points = priority * 2
                score += points
                matched_keywords.append(exact_keyword)
                self._log_debug(f"    完全一致: {source}'{exact_keyword}' (+{points})")
        
        # 部分一致キーワード（中スコア）
        for partial_keyword in rules.get("partial_keywords", []):
            if partial_keyword in text:
                points = priority * 1
                score += points
                matched_keywords.append(partial_keyword)
                self._log_debug(f"    部分一致: {source}'{partial_keyword}' (+{points})")
        
        return score, matched_keywords

    def _calculate_filename_score(self, filename: str, rules: Dict) -> Tuple[float, List[str]]:
        """ファイル名に基づいてスコアを計算（詳細ログ対応版）"""
        score = 0
        matched_keywords = []
        priority = rules.get("priority", 5)
        
        # 除外キーワードチェック（ファイル名でも重要）
        for exclude_keyword in rules.get("exclude_keywords", []):
            if exclude_keyword in filename:
                self._log_debug(f"    除外: ファイル名除外キーワード検出: '{exclude_keyword}'")
                return 0, []  # 除外キーワードが含まれている場合はスコア0
        
        # ファイル名専用キーワードがある場合
        filename_keywords = rules.get("filename_keywords", [])
        for keyword in filename_keywords:
            if keyword in filename:
                points = priority * 3  # ファイル名マッチは最高スコア
                score += points
                matched_keywords.append(f"[ファイル名]{keyword}")
                self._log_debug(f"    ファイル名専用一致: '{keyword}' (+{points})")
        
        # 通常のキーワードもファイル名でチェック
        for exact_keyword in rules.get("exact_keywords", []):
            if exact_keyword in filename:
                points = priority * 2
                score += points
                matched_keywords.append(f"[ファイル名]{exact_keyword}")
                self._log_debug(f"    ファイル名完全一致: '{exact_keyword}' (+{points})")
        
        return score, matched_keywords

    def classify_with_municipality_info(self, text: str, filename: str, 
                                      municipality_settings: Optional[Dict] = None,
                                      file_path: Optional[str] = None) -> ClassificationResult:
        """自治体情報を考慮した分類（自治体名付きコード対応版）
        
        Args:
            text: OCRで抽出されたテキスト
            filename: ファイル名
            municipality_settings: {
                "set1": {"prefecture": "東京都", "municipality": ""},
                "set2": {"prefecture": "愛知県", "municipality": "蒲郡市"},
                "set3": {"prefecture": "大阪府", "municipality": "大阪市"},
                "set4": {"prefecture": "", "municipality": ""},
                "set5": {"prefecture": "", "municipality": ""}
            }
        """
        if not municipality_settings:
            municipality_settings = {}
        
        # 東京都エラーチェック（セット1以外に東京都がある場合）
        tokyo_error = self._check_tokyo_error(municipality_settings)
        if tokyo_error:
            self._log(f"東京都エラー: {tokyo_error}")
            # エラーメッセージを含む結果を返す
            return ClassificationResult(
                document_type="エラー_東京都はセット1のみ設定可能",
                confidence=0.0,
                matched_keywords=[],
                classification_method="tokyo_error_check",
                debug_steps=[],
                processing_log=[tokyo_error]
            )
        
        # OCRテキストから検出された都道府県・市町村を特定
        detected_set = self._detect_municipality_from_text(text, filename, municipality_settings)
        
        # 基本分類を実行
        base_result = self.classify_document(text, filename, file_path)
        
        # 自治体名付きコード生成（検出されたセット情報を使用）
        final_code = self._generate_municipality_code_with_detection(
            base_result.document_type, 
            municipality_settings, 
            detected_set
        )
        
        if final_code != base_result.document_type:
            self._log(f"自治体名付きコード生成: {base_result.document_type} → {final_code}")
            base_result.document_type = final_code
        
        return base_result
    
    def _detect_from_filename(self, filename: str, municipality_settings: Dict) -> Optional[str]:
        """ファイル名から都道府県・市町村を検出（セット設定優先）"""
        filename_lower = filename.lower()
        
        # セット設定から都道府県・市町村名を取得して照合
        for set_name, settings in municipality_settings.items():
            prefecture = settings.get("prefecture", "").strip()
            municipality = settings.get("municipality", "").strip()
            
            # 都道府県名の照合（複数パターン）
            if prefecture:
                prefecture_patterns = [
                    prefecture,  # 完全名：愛知県
                    prefecture.replace("県", "").replace("都", "").replace("府", "").replace("道", ""),  # 基本名：愛知
                    f"{prefecture}税事務所",  # 税務事務所名
                    f"{prefecture.replace('県', '').replace('都', '').replace('府', '').replace('道', '')}県税事務所"
                ]
                
                for pattern in prefecture_patterns:
                    if pattern and pattern in filename:
                        self._log_debug(f"ファイル名で都道府県検出: {pattern} → {set_name}({prefecture})")
                        return set_name
            
            # 市町村名の照合（複数パターン）
            if municipality:
                municipality_patterns = [
                    municipality,  # 完全名：蒲郡市
                    f"{municipality}役所",  # 役所名：蒲郡市役所
                    f"{prefecture}{municipality}" if prefecture else municipality  # 組み合わせ：愛知県蒲郡市
                ]
                
                for pattern in municipality_patterns:
                    if pattern and pattern in filename:
                        self._log_debug(f"ファイル名で市町村検出: {pattern} → {set_name}({prefecture}{municipality})")
                        return set_name
        
        return None
    
    def _confirm_detection_with_ocr(self, text: str, detected_set: str, municipality_settings: Dict) -> bool:
        """OCRテキストでファイル名検出を補完的に確認"""
        if detected_set not in municipality_settings:
            return False
            
        settings = municipality_settings[detected_set]
        prefecture = settings.get("prefecture", "").strip()
        municipality = settings.get("municipality", "").strip()
        
        # 都道府県名または市町村名がOCRテキストに含まれているかチェック
        confirmation_keywords = []
        if prefecture:
            confirmation_keywords.extend([prefecture, prefecture.replace("県", "").replace("都", "").replace("府", "").replace("道", "")])
        if municipality:
            confirmation_keywords.append(municipality)
            
        for keyword in confirmation_keywords:
            if keyword and keyword in text:
                self._log_debug(f"OCR確認成功: {keyword}")
                return True
                
        self._log_debug(f"OCR確認失敗: {confirmation_keywords}がテキストに見つからない")
        return False
    
    def _detect_from_settings_with_ocr(self, text: str, filename: str, municipality_settings: Dict) -> Optional[str]:
        """セット設定を基準にOCRテキストから検出"""
        combined_text = f"{text} {filename}"
        
        # セット順序で確認（set1, set2, set3, set4, set5）
        for set_name in ["set1", "set2", "set3", "set4", "set5"]:
            if set_name in municipality_settings:
                settings = municipality_settings[set_name]
                prefecture = settings.get("prefecture", "").strip()
                municipality = settings.get("municipality", "").strip()
                
                # 都道府県名での検出
                if prefecture:
                    prefecture_keywords = [
                        prefecture,
                        prefecture.replace("県", "").replace("都", "").replace("府", "").replace("道", ""),
                        f"{prefecture}税事務所",
                        f"{prefecture.replace('県', '').replace('都', '').replace('府', '').replace('道', '')}県税事務所"
                    ]
                    
                    for keyword in prefecture_keywords:
                        if keyword and keyword in combined_text:
                            self._log_debug(f"セット設定ベース検出(都道府県): {keyword} → {set_name}")
                            return set_name
                
                # 市町村名での検出
                if municipality:
                    municipality_keywords = [
                        municipality,
                        f"{municipality}役所",
                        f"{prefecture}{municipality}" if prefecture else municipality
                    ]
                    
                    for keyword in municipality_keywords:
                        if keyword and keyword in combined_text:
                            self._log_debug(f"セット設定ベース検出(市町村): {keyword} → {set_name}")
                            return set_name
        
        return None
    
    def _detect_municipality_from_text(self, text: str, filename: str, municipality_settings: Dict) -> Optional[str]:
        """セット設定優先で都道府県・市町村を検出（画像認識は補完的に使用）"""
        # Stage 1: ファイル名から直接検出（最優先）
        filename_detected = self._detect_from_filename(filename, municipality_settings)
        if filename_detected:
            self._log_debug(f"ファイル名から検出: {filename} → {filename_detected}")
            # ファイル名で検出できた場合は、OCRテキストで補完的確認
            is_confirmed = self._confirm_detection_with_ocr(text, filename_detected, municipality_settings)
            if is_confirmed:
                self._log_debug(f"OCRテキストで確認完了: {filename_detected}")
                return filename_detected
            else:
                self._log_debug(f"OCRテキストでの確認失敗、ファイル名検出を採用: {filename_detected}")
                return filename_detected  # ファイル名優先のため、確認失敗でも採用
        
        # Stage 2: セット設定を基準にOCRテキストから検出（フォールバック）
        set_based_detected = self._detect_from_settings_with_ocr(text, filename, municipality_settings)
        if set_based_detected:
            self._log_debug(f"セット設定ベースで検出: {set_based_detected}")
            return set_based_detected
        
        # Stage 3: 従来のOCRテキスト中心検出（最終フォールバック）
        combined_text = f"{text} {filename}"
        prefecture_keywords = ["付加価値割", "付加価値額総額", "合計事業税額", "県税事務所", "都税事務所", "道税事務所", "府税事務所"]
        is_prefecture_document = any(keyword in combined_text for keyword in prefecture_keywords)
        
        if is_prefecture_document:
            return self._detect_prefecture_from_addressee(combined_text, municipality_settings)
        else:
            return self._detect_municipality_from_content(combined_text, municipality_settings)
    
    def _detect_prefecture_from_addressee(self, text: str, municipality_settings: Dict) -> Optional[str]:
        """宛先情報から都道府県を判定（セット優先のパターンベース検出）"""
        
        import re
        
        # セット順序で優先度決定（set1, set2, set3, set4, set5の順）
        ordered_sets = [(f"set{i}", municipality_settings.get(f"set{i}", {})) 
                       for i in range(1, 6) if f"set{i}" in municipality_settings]
        
        # Pattern 1: ●●[都道府県]事務所長 殿 のパターン検出（都道府県書類用）
        prefecture_office_pattern = r'([^\s]+(?:都|道|府|県)).*?事務所長\s*殿?'
        matches = re.findall(prefecture_office_pattern, text)
        
        if matches:
            detected_prefecture_text = matches[0]
            self._log_debug(f"都道府県事務所長パターン検出: {detected_prefecture_text}")
            
            # セット設定と照合（設定順序で優先）
            for set_name, settings in ordered_sets:
                set_prefecture = settings.get("prefecture", "").strip()
                if set_prefecture and (set_prefecture in detected_prefecture_text or 
                                     set_prefecture.replace("県", "").replace("都", "").replace("府", "").replace("道", "") in detected_prefecture_text):
                    self._log_debug(f"セット照合成功: {detected_prefecture_text} → {set_name}({set_prefecture})")
                    return set_name
        
        # Stage 2: 具体的な税務事務所名パターンで検索（補完的）
        tax_office_patterns = [
            # 福岡県（重要：テストケースに含まれる）
            ("福岡県西福岡県税事務所長", "福岡県"),
            ("福岡県東福岡県税事務所長", "福岡県"),
            ("福岡県南福岡県税事務所長", "福岡県"),
            ("福岡県北福岡県税事務所長", "福岡県"),
            # 愛知県
            ("愛知県東三河県税事務所長", "愛知県"),
            ("愛知県西三河県税事務所長", "愛知県"), 
            ("愛知県名古屋中村県税事務所長", "愛知県"),
            ("愛知県豊橋県税事務所長", "愛知県"),
            # 東京都
            ("東京都港都税事務所長", "東京都"),
            ("東京都新宿都税事務所長", "東京都"),
            ("東京都渋谷都税事務所長", "東京都")
        ]
        
        detected_prefecture = None
        
        # 具体的なパターンマッチング
        for pattern, prefecture_name in tax_office_patterns:
            if pattern in text:
                detected_prefecture = prefecture_name
                self._log_debug(f"税務事務所検出: {pattern} → {prefecture_name}")
                break
        
        # 検出された都道府県から対応するセット検索（セット優先順序で）
        if detected_prefecture:
            for set_name, settings in ordered_sets:
                set_prefecture = settings.get("prefecture", "").strip()
                if set_prefecture == detected_prefecture:
                    self._log_debug(f"都道府県マッチング: {detected_prefecture} → {set_name}")
                    return set_name
        
        # Stage 3: 一般的な県税事務所パターンで検出（セット設定優先）
        for set_name, settings in ordered_sets:
            set_prefecture = settings.get("prefecture", "").strip()
            if set_prefecture:
                prefecture_base = set_prefecture.replace("都", "").replace("道", "").replace("府", "").replace("県", "")
                
                general_patterns = [
                    f"{set_prefecture}事務所長",
                    f"{prefecture_base}県税事務所長",
                    f"{prefecture_base}都税事務所長",
                    f"{prefecture_base}道税事務所長", 
                    f"{prefecture_base}府税事務所長"
                ]
                
                for pattern in general_patterns:
                    if pattern in text:
                        self._log_debug(f"一般的な税務事務所検出: {pattern} → {set_name}({set_prefecture})")
                        return set_name
        
        # Stage 4: 都道府県名直接検出（最終フォールバック - セット優先順序で）
        for set_name, settings in ordered_sets:
            set_prefecture = settings.get("prefecture", "").strip()
            if set_prefecture and set_prefecture in text:
                self._log_debug(f"都道府県名直接検出: {set_prefecture} → {set_name}")
                return set_name
        
        self._log_debug(f"都道府県検出失敗: text contains {text[:100]}...")
        return None
    
    def _detect_municipality_from_content(self, text: str, municipality_settings: Dict) -> Optional[str]:
        """テキスト内容から市町村を検出（パターンベース + セット優先）"""
        
        import re
        
        # セット順序で優先度決定（set1, set2, set3, set4, set5の順）
        ordered_sets = [(f"set{i}", municipality_settings.get(f"set{i}", {})) 
                       for i in range(1, 6) if f"set{i}" in municipality_settings]
        
        # Pattern 1: ●●[都道府県]●●[市町村]長 殿 のパターン検出（市町村書類用）
        municipality_mayor_pattern = r'([^\s]+(?:都|道|府|県))([^\s]+(?:市|町|村))長\s*殿?'
        matches = re.findall(municipality_mayor_pattern, text)
        
        if matches:
            detected_prefecture_text, detected_municipality_text = matches[0]
            self._log_debug(f"市町村長パターン検出: {detected_prefecture_text}{detected_municipality_text}長")
            
            # セット設定と照合（設定順序で優先）
            for set_name, settings in ordered_sets:
                set_prefecture = settings.get("prefecture", "").strip()
                set_municipality = settings.get("municipality", "").strip()
                
                if set_prefecture and set_municipality:
                    # 都道府県と市町村の両方をチェック
                    prefecture_match = (set_prefecture in detected_prefecture_text or 
                                      set_prefecture.replace("県", "").replace("都", "").replace("府", "").replace("道", "") in detected_prefecture_text)
                    municipality_match = set_municipality in detected_municipality_text
                    
                    if prefecture_match and municipality_match:
                        self._log_debug(f"セット照合成功: {detected_prefecture_text}{detected_municipality_text} → {set_name}({set_prefecture}{set_municipality})")
                        return set_name
        
        # Stage 2: 市町村名直接検出（補完的）
        for set_name, settings in ordered_sets:
            prefecture = settings.get("prefecture", "").strip()
            municipality = settings.get("municipality", "").strip()
            
            if municipality:
                # 市町村のキーワード検出
                if municipality in text:
                    self._log_debug(f"市町村直接検出: {municipality} → {set_name}")
                    return set_name
        
        # Stage 3: 都道府県名直接検出（最終フォールバック）
        for set_name, settings in ordered_sets:
            prefecture = settings.get("prefecture", "").strip()
            
            if prefecture:
                # 都道府県のキーワード検出（市町村書類の場合の補助的判定）
                prefecture_keywords = [
                    prefecture,
                    prefecture.replace("都", "").replace("道", "").replace("府", "").replace("県", ""),
                ]
                
                for keyword in prefecture_keywords:
                    if keyword and keyword in text:
                        self._log_debug(f"都道府県直接検出: {keyword} → {set_name}")
                        return set_name
        
        return None
    
    def _check_tokyo_error(self, municipality_settings: Dict) -> Optional[str]:
        """東京都エラーチェック"""
        tokyo_sets = []
        for set_name, settings in municipality_settings.items():
            prefecture = settings.get("prefecture", "")
            if "東京" in prefecture:
                tokyo_sets.append(set_name)
        
        if len(tokyo_sets) > 1:
            return f"エラー: 東京都が複数のセット({', '.join(tokyo_sets)})に設定されています。東京都はセット1のみ設定可能です。"
        elif len(tokyo_sets) == 1 and tokyo_sets[0] != "set1":
            return f"エラー: 東京都が{tokyo_sets[0]}に設定されています。東京都はセット1のみ設定可能です。"
        
        return None
    
    def _generate_municipality_code_with_detection(self, base_document_type: str, 
                                                 municipality_settings: Dict, 
                                                 detected_set: Optional[str] = None) -> str:
        """検出されたセット情報を使用した自治体名付きドキュメントコード生成"""
        # 都道府県書類の場合
        if base_document_type.startswith("1001_都道府県"):
            return self._generate_prefecture_code_with_detection(
                base_document_type, municipality_settings, detected_set
            )
        
        # 市町村書類の場合  
        elif base_document_type.startswith("2001_市町村"):
            return self._generate_municipality_specific_code_with_detection(
                base_document_type, municipality_settings, detected_set
            )
        
        # その他の書類はそのまま返す
        return base_document_type
    
    def _generate_prefecture_code_with_detection(self, base_code: str, 
                                               municipality_settings: Dict, 
                                               detected_set: Optional[str] = None) -> str:
        """検出されたセット情報を使用した都道府県書類のコード生成（入力順序による連番付き）"""
        # 入力順序連番コード: 1番目→1001, 2番目→1011, 3番目→1021, 4番目→1031, 5番目→1041
        sequence_codes = [1001, 1011, 1021, 1031, 1041]
        
        # 実際に入力された自治体を順番で取得
        ordered_sets = self._get_ordered_input_sets(municipality_settings)
        
        if not ordered_sets:
            return base_code.replace("1001_都道府県", "1001_未設定")
        
        # 検出されたセットがある場合、その順序位置を特定
        if detected_set and detected_set in municipality_settings:
            settings = municipality_settings[detected_set]
            prefecture = settings.get("prefecture", "").strip()
            
            if prefecture:
                # 検出されたセットの順序位置を特定
                set_index_mapping = {"set1": 0, "set2": 1, "set3": 2, "set4": 3, "set5": 4}
                
                if detected_set in set_index_mapping:
                    # 実際に入力されている自治体のうち、検出されたセットが何番目かを計算
                    actual_index = 0
                    for set_name in ["set1", "set2", "set3", "set4", "set5"]:
                        if set_name in municipality_settings:
                            set_prefecture = municipality_settings[set_name].get("prefecture", "").strip()
                            if set_prefecture:  # 都道府県が入力されているセットのみカウント
                                if set_name == detected_set:
                                    break
                                actual_index += 1
                    
                    set_code = sequence_codes[actual_index] if actual_index < len(sequence_codes) else sequence_codes[-1]
                    parts = base_code.split("_", 2)
                    if len(parts) >= 3:
                        final_code = f"{set_code}_{prefecture}_{parts[2]}"
                    else:
                        final_code = f"{set_code}_{prefecture}_法人都道府県民税・事業税・特別法人事業税"
                    
                    self._log_debug(f"都道府県コード生成: {detected_set}({actual_index+1}番目) → {final_code}")
                    return final_code
        
        # 検出されなかった場合は最初の都道府県設定を使用（フォールバック）
        if ordered_sets:
            first_set_name, first_settings = ordered_sets[0]
            prefecture = first_settings.get("prefecture", "").strip()
            if prefecture:
                set_code = sequence_codes[0]
                parts = base_code.split("_", 2)
                if len(parts) >= 3:
                    return f"{set_code}_{prefecture}_{parts[2]}"
                else:
                    return f"{set_code}_{prefecture}_法人都道府県民税・事業税・特別法人事業税"
        
        # 設定がない場合はエラーコードを返す
        return base_code.replace("1001_都道府県", "1001_未設定")
    
    def _generate_municipality_specific_code_with_detection(self, base_code: str, 
                                                          municipality_settings: Dict, 
                                                          detected_set: Optional[str] = None) -> str:
        """検出されたセット情報を使用した市町村書類のコード生成（入力順序による連番付き）"""
        # 入力順序連番コード: 1番目→2001, 2番目→2011, 3番目→2021, 4番目→2031, 5番目→2041
        sequence_codes = [2001, 2011, 2021, 2031, 2041]
        
        # 東京都を除いた市町村設定を入力順で取得
        municipality_sets = self._get_ordered_municipality_sets(municipality_settings)
        
        # 検出されたセットがある場合、その順序位置を特定
        if detected_set and detected_set in municipality_settings:
            settings = municipality_settings[detected_set]
            prefecture = settings.get("prefecture", "").strip()
            municipality = settings.get("municipality", "").strip()
            
            # 東京都の場合は市町村書類は生成しない
            if "東京" in prefecture:
                self._log_debug(f"東京都のため市町村書類をスキップ: {detected_set}")
                return base_code.replace("2001_市町村", "2001_東京都_市町村書類なし")
                
            if prefecture and municipality:
                # 検出されたセットが市町村設定の何番目かを実際に計算
                actual_index = 0
                for set_name in ["set1", "set2", "set3", "set4", "set5"]:
                    if set_name in municipality_settings:
                        set_settings = municipality_settings[set_name]
                        set_prefecture = set_settings.get("prefecture", "").strip()
                        set_municipality = set_settings.get("municipality", "").strip()
                        
                        # 東京都でない場合かつ市町村が設定されている場合のみカウント
                        if set_prefecture and set_municipality and "東京" not in set_prefecture:
                            if set_name == detected_set:
                                break
                            actual_index += 1
                
                set_code = sequence_codes[actual_index] if actual_index < len(sequence_codes) else sequence_codes[-1]
                parts = base_code.split("_", 2)
                municipality_name = f"{prefecture}{municipality}"
                if len(parts) >= 3:
                    final_code = f"{set_code}_{municipality_name}_{parts[2]}"
                else:
                    final_code = f"{set_code}_{municipality_name}_法人市民税"
                
                self._log_debug(f"市町村コード生成: {detected_set}({actual_index+1}番目) → {final_code}")
                return final_code
        
        # 検出されなかった場合は最初の市町村設定を使用（フォールバック）
        if municipality_sets:
            first_set_name, first_settings = municipality_sets[0]
            prefecture = first_settings.get("prefecture", "").strip()
            municipality = first_settings.get("municipality", "").strip()
            if prefecture and municipality:
                set_code = sequence_codes[0]
                parts = base_code.split("_", 2)
                municipality_name = f"{prefecture}{municipality}"
                if len(parts) >= 3:
                    return f"{set_code}_{municipality_name}_{parts[2]}"
                else:
                    return f"{set_code}_{municipality_name}_法人市民税"
        
        # 設定がない場合はエラーコードを返す
        return base_code.replace("2001_市町村", "2001_未設定")
    
    def _get_ordered_input_sets(self, municipality_settings: Dict) -> List[Tuple[str, Dict]]:
        """入力された順番で自治体設定を取得"""
        ordered_sets = []
        
        # セット順序でチェック（set1, set2, set3, set4, set5）
        for set_name in ["set1", "set2", "set3", "set4", "set5"]:
            if set_name in municipality_settings:
                settings = municipality_settings[set_name]
                prefecture = settings.get("prefecture", "").strip()
                municipality = settings.get("municipality", "").strip()
                
                # 実際に入力がある場合のみ追加
                if prefecture:  # 都道府県が入力されている
                    ordered_sets.append((set_name, settings))
        
        return ordered_sets
    
    def _generate_prefecture_code(self, base_code: str, municipality_settings: Dict) -> str:
        """都道府県書類のコード生成（入力順序による連番付き）"""
        # 入力順序連番コード: 1番目→1001, 2番目→1011, 3番目→1021, 4番目→1031, 5番目→1041
        sequence_codes = [1001, 1011, 1021, 1031, 1041]
        
        # 実際に入力された自治体を順番で取得
        ordered_sets = self._get_ordered_input_sets(municipality_settings)
        
        if not ordered_sets:
            # 設定がない場合はデフォルト
            return base_code.replace("1001_都道府県", "1001_未設定")
        
        # 1番目に入力された都道府県を使用
        first_set_name, first_settings = ordered_sets[0]
        prefecture = first_settings.get("prefecture", "").strip()
        
        if prefecture:
            # 1番目は必ず1001
            set_code = sequence_codes[0]
            parts = base_code.split("_", 2)
            if len(parts) >= 3:
                return f"{set_code}_{prefecture}_{parts[2]}"
            else:
                return f"{set_code}_{prefecture}_法人都道府県民税・事業税・特別法人事業税"
        
        # 設定がない場合はデフォルト
        return base_code.replace("1001_都道府県", "1001_未設定")
    
    def _get_ordered_municipality_sets(self, municipality_settings: Dict) -> List[Tuple[str, Dict]]:
        """東京都を除いた市町村設定を入力順で取得"""
        municipality_sets = []
        
        # セット順序でチェック（set1, set2, set3, set4, set5）
        for set_name in ["set1", "set2", "set3", "set4", "set5"]:
            if set_name in municipality_settings:
                settings = municipality_settings[set_name]
                prefecture = settings.get("prefecture", "").strip()
                municipality = settings.get("municipality", "").strip()
                
                # 東京都でない場合かつ市町村が設定されている場合のみ追加
                if prefecture and municipality and "東京" not in prefecture:
                    municipality_sets.append((set_name, settings))
                    self._log_debug(f"市町村セット追加: {set_name} -> {prefecture}{municipality}")
                elif "東京" in prefecture:
                    self._log_debug(f"東京都セットをスキップ: {set_name} -> {prefecture}")
        
        self._log_debug(f"最終市町村セット数: {len(municipality_sets)}")
        return municipality_sets

    def _generate_municipality_specific_code(self, base_code: str, municipality_settings: Dict) -> str:
        """市町村書類のコード生成（入力順序による連番付き）"""
        # 入力順序連番コード: 1番目→2001, 2番目→2011, 3番目→2021, 4番目→2031, 5番目→2041
        sequence_codes = [2001, 2011, 2021, 2031, 2041]
        
        # 東京都を除いた市町村設定を入力順で取得
        municipality_sets = self._get_ordered_municipality_sets(municipality_settings)
        
        if not municipality_sets:
            # 設定がない場合はデフォルト
            return base_code.replace("2001_市町村", "2001_未設定")
        
        # 1番目の市町村を使用（東京都除く）
        first_set_name, first_settings = municipality_sets[0]
        prefecture = first_settings.get("prefecture", "").strip()
        municipality = first_settings.get("municipality", "").strip()
        
        if prefecture and municipality:
            # 1番目は必ず2001
            set_code = sequence_codes[0]
            parts = base_code.split("_", 2)
            municipality_name = f"{prefecture}{municipality}"
            if len(parts) >= 3:
                return f"{set_code}_{municipality_name}_{parts[2]}"
            else:
                return f"{set_code}_{municipality_name}_法人市民税"
        
        # 設定がない場合はデフォルト
        return base_code.replace("2001_市町村", "2001_未設定")

    def _determine_final_code_with_set_priority(self, document_type: str, 
                                              prefecture_code: Optional[int] = None,
                                              municipality_code: Optional[int] = None,
                                              available_sets: Optional[List[int]] = None) -> str:
        """セット優先順序による最終コード決定
        
        Args:
            document_type: 基本分類結果
            prefecture_code: 都道府県コード
            municipality_code: 市町村コード  
            available_sets: 利用可能なセット番号リスト
            
        Returns:
            最終的なドキュメントコード
        """
        # セット優先順序定義 (セット1 → セット2 → セット3 → セット4 → セット5)
        set_priority = [1001, 1011, 1021, 1031, 1041]  # 都道府県用
        municipality_set_priority = [2001, 2011, 2021, 2031, 2041]  # 市町村用
        
        # 都道府県関連書類の場合
        if document_type.startswith("1001_"):
            base_code = document_type.split("_", 1)
            if len(base_code) == 2:
                # セット優先順序で最適なコードを決定
                if available_sets:
                    # 利用可能なセットから最も優先度が高いものを選択
                    for priority_code in set_priority:
                        if priority_code in available_sets:
                            self._log_debug(f"都道府県セット優先選択: {priority_code}")
                            return f"{priority_code}_{base_code[1]}"
                elif prefecture_code:
                    # 指定されたコードを使用
                    return f"{prefecture_code}_{base_code[1]}"
                    
        # 市町村関連書類の場合
        elif document_type.startswith("2001_"):
            base_code = document_type.split("_", 1)
            if len(base_code) == 2:
                # セット優先順序で最適なコードを決定
                if available_sets:
                    # 利用可能なセットから最も優先度が高いものを選択
                    for priority_code in municipality_set_priority:
                        if priority_code in available_sets:
                            self._log_debug(f"市町村セット優先選択: {priority_code}")
                            return f"{priority_code}_{base_code[1]}"
                elif municipality_code:
                    # 指定されたコードを使用
                    return f"{municipality_code}_{base_code[1]}"
        
        # その他の場合は元のコードをそのまま返す
        return document_type

    def _classify_prefecture_document(self, text: str, filename: str, 
                                    prefecture_code: Optional[int] = None) -> Optional[ClassificationResult]:
        """都道府県申告書の特別判定処理"""
        # 都道府県申告書判定キーワード群
        prefecture_keywords = [
            "県税事務所", "都税事務所", "道府県民税", "事業税", "特別法人事業税",
            "年400万円以下", "年月日から年月日までの", "申告書"
        ]
        
        # テキストとファイル名を結合して判定
        combined_text = f"{text} {filename}".lower()
        
        # 東京都の特別処理
        is_tokyo = "都税事務所" in combined_text or "東京都" in combined_text
        
        # 東京都でセット2-5の場合のエラー処理
        if is_tokyo and prefecture_code and prefecture_code in [1011, 1021, 1031, 1041]:
            self._log(f"東京都エラー処理: セット{(prefecture_code-1001)//10+1}は東京都では使用不可")
            self._log_debug(f"東京都セット2-5エラー: prefecture_code={prefecture_code}")
            
            # 東京都の場合はセット1(1001)に強制変更
            prefecture_code = 1001
            self._log(f"東京都のためセット1(1001)に変更")
        
        # キーワードマッチング数をカウント
        matched_keywords = []
        for keyword in prefecture_keywords:
            if keyword in combined_text:
                matched_keywords.append(keyword)
        
        match_count = len(matched_keywords)
        
        # 3個以上のキーワードマッチで都道府県申告書と判定
        if match_count >= 3:
            # 優先度: セット1 > セット2 > セット3 > セット4 > セット5
            prefecture_code_mapping = {
                None: 1001,  # デフォルト
                1011: 1011,  # セット2
                1021: 1021,  # セット3
                1031: 1031,  # セット4
                1041: 1041   # セット5
            }
            
            file_code = prefecture_code_mapping.get(prefecture_code, 1001)
            confidence = min(match_count / len(prefecture_keywords), 1.0)
            
            self._log_debug(f"都道府県申告書判定: マッチ数={match_count}, 信頼度={confidence:.2f}, コード={file_code}")
            self._log_debug(f"マッチキーワード: {matched_keywords}")
            
            return ClassificationResult(
                document_type=f"{file_code}_都道府県_法人都道府県民税・事業税・特別法人事業税",
                confidence=confidence,
                matched_keywords=matched_keywords,
                classification_method="prefecture_special_classification",
                debug_steps=[],
                processing_log=[]
            )
        
        return None

    def get_document_category(self, document_type: str) -> str:
        """書類分類からカテゴリを取得"""
        if document_type.startswith("0"):
            return "申告書類"
        elif document_type.startswith("1"):
            return "都道府県関連"
        elif document_type.startswith("2"):
            return "市町村関連"
        elif document_type.startswith("3"):
            return "消費税関連"
        elif document_type.startswith("5"):
            return "会計書類"
        elif document_type.startswith("6"):
            return "固定資産関連"
        elif document_type.startswith("7"):
            return "税区分関連"
        else:
            return "その他"

if __name__ == "__main__":
    # テスト用
    classifier = DocumentClassifier()
    print("書類分類エンジン v4.0 初期化完了")