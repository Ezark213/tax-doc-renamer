#!/usr/bin/env python3
"""
税務書類処理システム データモデル v5.3
決定論的命名とスナップショット方式のためのデータ構造
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import hashlib
import json
from pathlib import Path


@dataclass
class RenameFields:
    """
    1ページ分のリネーム情報（Pre-Extract段階で取得）
    OCR結果から推論した書類メタデータを格納
    """
    code_hint: Optional[str] = None          # 書類コードヒント（1003/2001/3001など）
    doc_hints: Optional[List[str]] = None     # 書類名ヒント（受信通知/納付情報/申告書...）
    muni_name: Optional[str] = None          # 東京都/愛知県蒲郡市...（自治体名）
    tax_kind: Optional[str] = None           # 国税/地方税/消費税 など
    period_yyyymm: Optional[str] = None      # 2508/202508/令和xxなど内部規格化した期間
    serial_bucket: Optional[str] = None      # 地方税受信通知の連番バケット識別子
    extra: Dict[str, Any] = field(default_factory=dict)  # 予備フィールド（納付区分番号など）

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（JSON serialization用）"""
        return {
            'code_hint': self.code_hint,
            'doc_hints': self.doc_hints,
            'muni_name': self.muni_name,
            'tax_kind': self.tax_kind,
            'period_yyyymm': self.period_yyyymm,
            'serial_bucket': self.serial_bucket,
            'extra': self.extra
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RenameFields':
        """辞書から復元"""
        return cls(
            code_hint=data.get('code_hint'),
            doc_hints=data.get('doc_hints'),
            muni_name=data.get('muni_name'),
            tax_kind=data.get('tax_kind'),
            period_yyyymm=data.get('period_yyyymm'),
            serial_bucket=data.get('serial_bucket'),
            extra=data.get('extra', {})
        )


@dataclass(frozen=True)
class PageFingerprint:
    """ページの一意性を担保するフィンガープリント"""
    page_md5: str                    # ページバイトのmd5（レンダ/抽出後どちらでも可）
    text_sha1: str                   # 正規化テキストのsha1
    
    def to_dict(self) -> Dict[str, str]:
        return {'page_md5': self.page_md5, 'text_sha1': self.text_sha1}
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'PageFingerprint':
        return cls(page_md5=data['page_md5'], text_sha1=data['text_sha1'])


@dataclass(frozen=True)
class DocItemID:
    """分割後の各書類の源泉情報"""
    source_doc_md5: str              # 元PDF全体のmd5
    page_index: int                  # 元のページ番号（0-indexed）
    fp: PageFingerprint
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_doc_md5': self.source_doc_md5,
            'page_index': self.page_index,
            'fp': self.fp.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocItemID':
        return cls(
            source_doc_md5=data['source_doc_md5'],
            page_index=data['page_index'],
            fp=PageFingerprint.from_dict(data['fp'])
        )


@dataclass
class PreExtractSnapshot:
    """
    元PDF単位でのページ毎RenameFields保持
    分割前に一度だけ作成し、以降は読み取り専用で使用
    """
    source_path: str                 # 元PDFファイルパス
    source_doc_md5: str              # 元PDF全体のmd5
    pages: List[RenameFields]        # ページ順のRenameFields
    created_at: str                  # 作成タイムスタンプ
    version: str = "5.3"            # スナップショット形式バージョン
    
    def to_dict(self) -> Dict[str, Any]:
        """JSON serialization用"""
        return {
            'source_path': self.source_path,
            'source_doc_md5': self.source_doc_md5,
            'pages': [page.to_dict() for page in self.pages],
            'created_at': self.created_at,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PreExtractSnapshot':
        """JSON deserialization"""
        return cls(
            source_path=data['source_path'],
            source_doc_md5=data['source_doc_md5'],
            pages=[RenameFields.from_dict(page) for page in data['pages']],
            created_at=data['created_at'],
            version=data.get('version', '5.3')
        )
    
    def save(self, snapshot_dir: Path) -> Path:
        """スナップショットをJSONファイルとして保存"""
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_dir / f"{self.source_doc_md5}.json"
        
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        return snapshot_file
    
    @classmethod
    def load(cls, snapshot_dir: Path, source_doc_md5: str) -> Optional['PreExtractSnapshot']:
        """スナップショットをJSONファイルから読み込み"""
        snapshot_file = snapshot_dir / f"{source_doc_md5}.json"
        
        if not snapshot_file.exists():
            return None
            
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


@dataclass
class SerialAllocation:
    """連番割り当て情報（決定論的）"""
    bucket_key: str                  # (source_md5, muni_name, period) のハッシュ
    items: List[tuple]               # (page_index, text_sha1, assigned_serial)のリスト
    
    def get_serial_for_page(self, page_index: int, text_sha1: str) -> Optional[int]:
        """特定のページの連番を取得"""
        for p_idx, t_sha1, serial in self.items:
            if p_idx == page_index and t_sha1 == text_sha1:
                return serial
        return None


def compute_file_md5(file_path: str) -> str:
    """ファイルのMD5ハッシュを計算"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def compute_text_sha1(text: str) -> str:
    """正規化テキストのSHA1ハッシュを計算"""
    return hashlib.sha1(text.encode('utf-8')).hexdigest()


def compute_page_md5(page_bytes: bytes) -> str:
    """ページバイトのMD5ハッシュを計算"""
    return hashlib.md5(page_bytes).hexdigest()


def make_bucket_key(source_md5: str, muni_name: str, period: str) -> str:
    """連番バケット用のキーを生成"""
    bucket_input = f"{source_md5}|{muni_name or 'NO_MUNI'}|{period or 'NO_PERIOD'}"
    return hashlib.sha256(bucket_input.encode('utf-8')).hexdigest()[:16]