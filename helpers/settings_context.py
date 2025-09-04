#!/usr/bin/env python3
"""
Settings context management v5.3.5-ui-robust
設定コンテキスト管理 - パイプライン全体での一貫した設定伝播
"""

import logging
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class UIContext:
    """UI設定コンテキスト（v5.3.5-ui-robust対応）"""
    # YYMM関連（優先順位順）
    yymm: Optional[str] = None
    ui_yymm: Optional[str] = None
    manual_yymm: Optional[str] = None
    manual_input_yymm: Optional[str] = None
    input_yymm: Optional[str] = None
    period_yymm: Optional[str] = None
    year_month_yymm: Optional[str] = None
    
    # バッチ処理設定
    batch_mode: bool = True
    allow_auto_forced_codes: bool = False
    
    # ファイル関連
    source_filename: Optional[str] = None
    file_id: Optional[str] = None
    
    # 自治体設定
    municipality_sets: Optional[Dict[int, Dict[str, str]]] = None
    
    # デバッグ・ログ設定
    debug_mode: bool = False
    verbose_logging: bool = False
    
    # メタデータ
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（堅牢なUI YYMM抽出対応）"""
        result = {}
        
        # YYMM関連フィールドのみを取得
        yymm_fields = [
            'yymm', 'ui_yymm', 'manual_yymm', 'manual_input_yymm',
            'input_yymm', 'period_yymm', 'year_month_yymm'
        ]
        
        for field_name in yymm_fields:
            value = getattr(self, field_name, None)
            if value is not None:
                result[field_name] = value
        
        # その他の設定
        if self.batch_mode is not None:
            result['batch_mode'] = self.batch_mode
        if self.allow_auto_forced_codes is not None:
            result['allow_auto_forced_codes'] = self.allow_auto_forced_codes
        if self.source_filename:
            result['source_filename'] = self.source_filename
        if self.file_id:
            result['file_id'] = self.file_id
        if self.municipality_sets:
            result['municipality_sets'] = self.municipality_sets
        if self.debug_mode is not None:
            result['debug_mode'] = self.debug_mode
        if self.verbose_logging is not None:
            result['verbose_logging'] = self.verbose_logging
        
        # メタデータ
        if self.meta:
            result.update(self.meta)
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIContext':
        """辞書からUIContextを生成"""
        if not data:
            return cls()
        
        # 基本フィールドを抽出
        kwargs = {}
        yymm_fields = [
            'yymm', 'ui_yymm', 'manual_yymm', 'manual_input_yymm',
            'input_yymm', 'period_yymm', 'year_month_yymm'
        ]
        
        for field_name in yymm_fields:
            if field_name in data:
                kwargs[field_name] = data[field_name]
        
        # その他のフィールド
        for field_name in ['batch_mode', 'allow_auto_forced_codes', 'source_filename', 
                          'file_id', 'municipality_sets', 'debug_mode', 'verbose_logging']:
            if field_name in data:
                kwargs[field_name] = data[field_name]
        
        # メタデータ
        meta = {k: v for k, v in data.items() 
               if k not in yymm_fields + ['batch_mode', 'allow_auto_forced_codes', 
                                         'source_filename', 'file_id', 'municipality_sets', 
                                         'debug_mode', 'verbose_logging']}
        if meta:
            kwargs['meta'] = meta
        
        return cls(**kwargs)
    
    def get_primary_yymm(self) -> Optional[str]:
        """最優先のYYMM値を取得"""
        for field_name in ['yymm', 'ui_yymm', 'manual_yymm', 'manual_input_yymm', 
                          'input_yymm', 'period_yymm', 'year_month_yymm']:
            value = getattr(self, field_name, None)
            if value:
                return value
        return None
    
    def add_meta(self, key: str, value: Any) -> None:
        """メタデータ追加"""
        if self.meta is None:
            self.meta = {}
        self.meta[key] = value
    
    def log_context(self) -> None:
        """コンテキスト情報をログ出力"""
        primary_yymm = self.get_primary_yymm()
        logger.info("[SETTINGS_CONTEXT] primary_yymm=%s batch_mode=%s file_id=%s", 
                   primary_yymm, self.batch_mode, self.file_id or "unknown")
        
        if self.debug_mode:
            logger.debug("[SETTINGS_CONTEXT] full_context=%s", self.to_dict())


def create_ui_context_from_gui(yymm_var_value: str, 
                               municipality_sets: Dict = None,
                               batch_mode: bool = True,
                               allow_auto_forced_codes: bool = False,
                               source_filename: str = None,
                               file_path: str = None,
                               debug_mode: bool = False) -> UIContext:
    """GUIから UIContext を作成"""
    return UIContext(
        yymm=yymm_var_value,
        municipality_sets=municipality_sets,
        batch_mode=batch_mode,
        allow_auto_forced_codes=allow_auto_forced_codes,
        source_filename=source_filename or file_path,
        debug_mode=debug_mode
    )


def normalize_settings_input(settings_input: Union[Dict, Any, None]) -> UIContext:
    """様々な設定入力を UIContext に正規化"""
    if settings_input is None:
        return UIContext()
    
    if isinstance(settings_input, UIContext):
        return settings_input
    
    if isinstance(settings_input, dict):
        return UIContext.from_dict(settings_input)
    
    # PreExtractSnapshot対応
    if hasattr(settings_input, 'meta') and isinstance(settings_input.meta, dict):
        ui_context_data = settings_input.meta.get('ui_context', {})
        if ui_context_data:
            return UIContext.from_dict(ui_context_data)
        # フォールバック：メタデータから直接YYMM取得
        yymm = settings_input.meta.get('yymm')
        if yymm:
            return UIContext(yymm=yymm)
    
    # レガシーオブジェクト対応
    if hasattr(settings_input, '__dict__'):
        return UIContext.from_dict(settings_input.__dict__)
    
    # その他の場合は文字列として扱う
    try:
        yymm_str = str(settings_input).strip()
        if yymm_str:
            return UIContext(yymm=yymm_str)
    except:
        pass
    
    # フォールバック
    return UIContext()


# プロパティパスによる設定アクセス
def get_nested_setting(settings: Any, path: str, default: Any = None) -> Any:
    """ネストした設定値を取得（例: 'ui.yymm'）"""
    if settings is None:
        return default
    
    parts = path.split('.')
    current = settings
    
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return default
        
        if current is None:
            return default
    
    return current


if __name__ == "__main__":
    # テスト実行
    import sys
    
    print("設定コンテキスト管理テスト")
    print("=" * 50)
    
    # テストケース
    test_cases = [
        {
            "name": "基本UI設定",
            "data": {"yymm": "2508", "debug_mode": True}
        },
        {
            "name": "複数YYMM候補",
            "data": {"manual_yymm": "2507", "ui_yymm": "2508", "yymm": "2509"}
        },
        {
            "name": "自治体設定込み",
            "data": {
                "yymm": "2508",
                "municipality_sets": {1: {"prefecture": "愛知県", "city": "名古屋市"}}
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nテストケース {i}: {test_case['name']}")
        
        # UIContext作成
        context = UIContext.from_dict(test_case["data"])
        print(f"  プライマリYYMM: {context.get_primary_yymm()}")
        
        # 辞書変換テスト
        converted = context.to_dict()
        print(f"  変換結果: {len(converted)}項目")
        
        # 正規化テスト
        normalized = normalize_settings_input(test_case["data"])
        print(f"  正規化: {normalized.get_primary_yymm()}")
    
    print("\n" + "=" * 50)
    print("テスト完了")