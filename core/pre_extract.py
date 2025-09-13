#!/usr/bin/env python3
"""
Pre-Extract スナップショット機能 v5.3
分割前にPDF全体をスキャンしてリネーム情報を抽出・保存
"""

import pymupdf as fitz  # PyMuPDF
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import (
    RenameFields, PreExtractSnapshot, PageFingerprint,
    compute_file_md5, compute_text_sha1, compute_page_md5
)


class PreExtractEngine:
    """Pre-Extract処理エンジン"""
    
    def __init__(self, logger: Optional[logging.Logger] = None, snapshot_dir: Optional[Path] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.snapshot_dir = snapshot_dir or Path("./snapshots")
        
        # 既存の分類パターンを活用
        self._init_extraction_patterns()
    
    def _init_extraction_patterns(self):
        """抽出パターンの初期化"""
        # 書類コード検出パターン（既存分類システムから流用）
        self.code_patterns = {
            r'\b(0003|0004|3003|3004|1003|1013|1023|1004|2003|2013|2023|2004|6002|6003)\b': 'strong',
            r'納付税額一覧表': '0000',
            r'法人税.*申告書': '0001',
            r'添付資料.*法人税': '0002',
            r'消費税.*申告書': '3001',
            r'添付資料.*消費税': '3002'
        }
        
        # 自治体名検出パターン
        self.muni_patterns = [
            r'([都道府県]{2,3}[都道府県])',  # 東京都、神奈川県など
            r'([市区町村]{1,3}[市区町村])',  # 横浜市、世田谷区など
            r'(札幌市|仙台市|千葉市|横浜市|川崎市|相模原市|新潟市|静岡市|浜松市|名古屋市|京都市|大阪市|堺市|神戸市|岡山市|広島市|北九州市|福岡市|熊本市)',
            r'([都道府県][市区町村][都道府県市区町村])',  # 愛知県蒲郡市など
        ]
        
        # 期間検出パターン
        self.period_patterns = [
            r'(\d{4})[\s]*[-/年][\s]*(\d{1,2})[\s]*[-/月]',  # 2025年8月、2025-08など
            r'令和(\d{1,2})年(\d{1,2})月',  # 令和7年8月
            r'(\d{2})(\d{2})',  # 2508（既存システムで使用中）
        ]
        
        # 税務カテゴリ検出パターン
        self.tax_kind_patterns = {
            '国税': [r'法人税', r'消費税', r'所得税', r'国税電子申告', r'税務署'],
            '地方税': [r'都道府県民税', r'市町村民税', r'事業税', r'地方税電子申告', r'県税事務所', r'市役所'],
            '消費税': [r'消費税及び地方消費税']
        }
        
        # 書類種別ヒント
        self.doc_hint_patterns = {
            '受信通知': [r'受信通知', r'申告受付完了', r'受信結果'],
            '納付情報': [r'納付情報', r'納付書', r'納付区分番号'],
            '申告書': [r'申告書', r'確認表'],
            '添付資料': [r'添付資料', r'明細表'],
            '帳票': [r'一括償却資産', r'少額減価償却', r'明細表']
        }
    
    def build_snapshot(self, pdf_path: str, max_scan_pages: Optional[int] = None, user_provided_yymm: Optional[str] = None, ui_context: Optional[Dict[str, Any]] = None) -> PreExtractSnapshot:
        """
        PDFファイルからPreExtractSnapshotを構築
        
        Args:
            pdf_path: 対象PDFファイルパス
            max_scan_pages: 最大スキャンページ数（Noneで全ページ）
            user_provided_yymm: ユーザー指定のYYMM（セット入力優先・必須）
            ui_context: UI設定コンテキスト（設定伝搬用）
            
        Returns:
            PreExtractSnapshot: 構築されたスナップショット
        """
        # --- YYMM唯一ソース検証 ---
        if not user_provided_yymm or len(user_provided_yymm) != 4 or not user_provided_yymm.isdigit():
            raise ValueError(f"[FATAL] YYMM is required and must be 4 digits from GUI. Example: 2508. Got: {user_provided_yymm}")
        
        # YYMM監査ログ：GUI値専用
        self.logger.info(f"[AUDIT][YYMM] source=GUI value={user_provided_yymm} validation=PASSED")
        self.logger.info(f"[v5.3] YYMM source validation passed: {user_provided_yymm} (GUI mandatory)")
        self.logger.info(f"[pre_extract] Building snapshot: {Path(pdf_path).name}")
        
        # PDF全体のMD5計算
        source_doc_md5 = compute_file_md5(pdf_path)
        
        # 既存スナップショットのチェック
        existing = PreExtractSnapshot.load(self.snapshot_dir, source_doc_md5)
        if existing:
            self.logger.info(f"[pre_extract] Using existing snapshot: {source_doc_md5}")
            return existing
        
        # 新規スナップショット作成
        try:
            doc = fitz.open(pdf_path)
            page_count = doc.page_count
            scan_pages = min(page_count, max_scan_pages or page_count)
            
            self.logger.debug(f"[pre_extract] Scanning {scan_pages}/{page_count} pages")
            
            pages = []
            for i in range(scan_pages):
                page = doc[i]
                
                # 高速OCRでテキスト抽出
                text = page.get_text()
                normalized_text = self._normalize_text(text)
                
                # ページフィンガープリント生成
                page_bytes = page.get_pixmap().pil_tobytes(format="PNG")
                page_md5 = compute_page_md5(page_bytes)
                text_sha1 = compute_text_sha1(normalized_text)
                
                # RenameFields推論
                fields = self._infer_rename_fields(normalized_text, i, user_provided_yymm)
                
                pages.append(fields)
                
                self.logger.debug(f"[pre_extract] Page {i}: code_hint={fields.code_hint}, muni={fields.muni_name}")
            
            doc.close()
            
            # スナップショット作成
            snapshot = PreExtractSnapshot(
                source_path=pdf_path,
                source_doc_md5=source_doc_md5,
                pages=pages,
                created_at=datetime.now().isoformat()
            )
            
            # GUI YYMM と UI設定をメタデータとして保存
            snapshot.meta = {
                'yymm': user_provided_yymm,
                'yymm_source': 'GUI',
                'ui_context': ui_context or {}
            }
            
            # 永続化
            snapshot_file = snapshot.save(self.snapshot_dir)
            self.logger.info(f"[pre_extract] Snapshot saved: {snapshot_file}")
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"[pre_extract] Failed to build snapshot: {e}")
            raise
    
    def _normalize_text(self, text: str) -> str:
        """テキスト正規化（既存システムと共通化）"""
        if not text:
            return ""
        
        # 全角・半角統一
        normalized = text.translate(str.maketrans(
            "０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ",
            "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        ))
        
        # 連続空白の縮約
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 余分な改行・特殊文字除去
        normalized = re.sub(r'[・\r\t]', '', normalized)
        
        return normalized.strip()
    
    def _infer_rename_fields(self, normalized_text: str, page_index: int, user_provided_yymm: Optional[str] = None) -> RenameFields:
        """正規化テキストからRenameFieldsを推論"""
        fields = RenameFields()
        
        # 書類コード検出
        fields.code_hint = self._detect_code(normalized_text)
        
        # 書類種別ヒント検出
        fields.doc_hints = self._detect_doc_hints(normalized_text)
        
        # 自治体名検出
        fields.muni_name = self._detect_municipality(normalized_text)
        
        # 税務カテゴリ検出
        fields.tax_kind = self._detect_tax_kind(normalized_text)
        
        # 期間検出：GUI値のみ（他ソース禁止）
        fields.period_yyyymm = user_provided_yymm
        self.logger.debug(f"[pre_extract] Using GUI-only YYMM: {user_provided_yymm}")
        
        # 連番バケット（地方税系の場合）
        if fields.code_hint and fields.code_hint.startswith(('1', '2')):
            fields.serial_bucket = f"{fields.muni_name}_{fields.period_yyyymm}"
        
        # 追加情報
        fields.extra = {
            'page_index': page_index,
            'text_length': len(normalized_text),
            'has_date': bool(re.search(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', normalized_text))
        }
        
        return fields
    
    def _detect_code(self, text: str) -> Optional[str]:
        """書類コード検出"""
        for pattern, code_type in self.code_patterns.items():
            if code_type == 'strong':
                # 数字コードの直接マッチング
                match = re.search(pattern, text)
                if match:
                    return match.group(1)
            else:
                # 書類名からのコード推論
                if re.search(pattern, text, re.IGNORECASE):
                    return code_type
        return None
    
    def _detect_doc_hints(self, text: str) -> List[str]:
        """書類種別ヒント検出"""
        hints = []
        for hint_type, patterns in self.doc_hint_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    hints.append(hint_type)
                    break
        return hints
    
    def _detect_municipality(self, text: str) -> Optional[str]:
        """自治体名検出"""
        for pattern in self.muni_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None
    
    def _detect_tax_kind(self, text: str) -> Optional[str]:
        """税務カテゴリ検出"""
        for kind, patterns in self.tax_kind_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return kind
        return None
    
    def cleanup_old_snapshots(self, max_age_days: int = 30):
        """古いスナップショットファイルの削除"""
        if not self.snapshot_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
        
        for snapshot_file in self.snapshot_dir.glob("*.json"):
            if snapshot_file.stat().st_mtime < cutoff_time:
                snapshot_file.unlink()
                self.logger.debug(f"[pre_extract] Cleaned up old snapshot: {snapshot_file}")


def create_pre_extract_engine(logger: Optional[logging.Logger] = None, 
                             snapshot_dir: Optional[Path] = None) -> PreExtractEngine:
    """PreExtractEngineのファクトリ関数"""
    return PreExtractEngine(logger=logger, snapshot_dir=snapshot_dir)