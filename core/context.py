#!/usr/bin/env python3
"""
Pipeline Context for v5.3 with YYMM propagation
"""

import copy
from dataclasses import dataclass
from typing import Optional

@dataclass
class PipelineContext:
    """
    パイプライン処理中のコンテキスト情報
    v5.3: YYMM値の一意ソース管理を追加
    """
    yymm: Optional[str] = None
    yymm_source: Optional[str] = None  # "UI_ONLY" を期待
    document_id: Optional[str] = None
    municipality_set: Optional[int] = None
    classification_code: Optional[str] = None
    
    def clone(self):
        """コンテキストの完全なクローンを作成"""
        return copy.deepcopy(self)
    
    def validate_yymm(self):
        """YYMM値の検証"""
        if not self.yymm:
            raise ValueError("[FATAL] YYMM is required from GUI snapshot")
        
        if not self.yymm.isdigit() or len(self.yymm) != 4:
            raise ValueError(f"[FATAL] YYMM must be 4 digits from GUI. Got: {self.yymm}")
        
        if self.yymm_source != "UI_ONLY":
            raise ValueError(f"[FATAL] YYMM must come from GUI snapshot only. Got source: {self.yymm_source}")

def attach_context(doc, ctx: PipelineContext):
    """ドキュメントにコンテキストを紐づける"""
    if hasattr(doc, '_pipeline_context'):
        doc._pipeline_context = ctx
    else:
        setattr(doc, '_pipeline_context', ctx)

def get_context(doc) -> Optional[PipelineContext]:
    """ドキュメントからコンテキストを取得"""
    if hasattr(doc, '_pipeline_context'):
        return doc._pipeline_context
    return None