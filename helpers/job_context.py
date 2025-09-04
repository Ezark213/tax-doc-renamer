#!/usr/bin/env python3
"""
JobContext - 税務書類処理ジョブの一元管理
確定YYMM値の単一ソース化とジョブライフサイクル管理
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from helpers.run_config import RunConfig

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """処理統計情報"""
    total_files: int = 0
    processed_files: int = 0
    bundle_split_count: int = 0
    ui_forced_files: int = 0
    detected_files: int = 0
    error_files: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def get_processing_time(self) -> Optional[float]:
        """処理時間を秒で返す"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass  
class JobContext:
    """
    税務書類処理ジョブの単一コンテキスト
    確定YYMM値の一元管理と処理ライフサイクル制御
    """
    # 必須情報
    job_id: str                           # ジョブ識別子
    confirmed_yymm: Optional[str]         # 確定したYYMM値（唯一のソース）
    yymm_source: str                      # YYMM値の取得元（UI/DETECTED/NONE）
    run_config: Optional[RunConfig]       # 実行設定
    
    # 処理設定
    batch_mode: bool = True               # バッチ処理モード
    debug_mode: bool = False              # デバッグモード
    output_directory: Optional[str] = None # 出力ディレクトリ
    
    # 処理状態
    status: str = "INITIALIZED"           # ジョブステータス
    processing_stats: ProcessingStats = field(default_factory=ProcessingStats)
    
    # メタデータ
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    error_messages: List[str] = field(default_factory=list)
    audit_log: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初期化後の処理"""
        self.updated_at = datetime.now()
        self.audit_log.append(f"[{self.created_at}] JobContext initialized: job_id={self.job_id}")
        
        # YYMM値の妥当性チェック
        if self.confirmed_yymm:
            if not self._validate_yymm(self.confirmed_yymm):
                raise ValueError(f"Invalid YYMM format: {self.confirmed_yymm}")
        
        # RunConfigから情報を同期
        if self.run_config:
            self._sync_from_run_config()
    
    def _validate_yymm(self, yymm: str) -> bool:
        """YYMM形式の妥当性検証"""
        import re
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
    
    def _sync_from_run_config(self):
        """RunConfigから情報を同期"""
        if self.run_config and self.run_config.has_manual_yymm():
            if self.confirmed_yymm != self.run_config.manual_yymm:
                self.audit_log.append(
                    f"[{datetime.now()}] YYMM sync from RunConfig: "
                    f"{self.confirmed_yymm} -> {self.run_config.manual_yymm}"
                )
                self.confirmed_yymm = self.run_config.manual_yymm
                self.yymm_source = "UI"
    
    def set_confirmed_yymm(self, yymm: str, source: str, reason: str = None):
        """確定YYMM値を設定（唯一のエントリーポイント）"""
        if not self._validate_yymm(yymm):
            raise ValueError(f"Invalid YYMM format: {yymm}")
        
        old_yymm = self.confirmed_yymm
        self.confirmed_yymm = yymm
        self.yymm_source = source
        self.updated_at = datetime.now()
        
        log_message = f"[{self.updated_at}] YYMM confirmed: {old_yymm} -> {yymm} (source={source})"
        if reason:
            log_message += f" reason={reason}"
        
        self.audit_log.append(log_message)
        logger.info(f"[JOB_CONTEXT] {log_message}")
    
    def get_yymm_for_classification(self, classification_code: str) -> str:
        """分類コード用のYYMM値を取得"""
        code4 = classification_code[:4] if classification_code else ""
        ui_forced_codes = {"6001", "6002", "6003", "0000"}
        
        # UI強制コードの場合はUI値が必須
        if code4 in ui_forced_codes:
            if not self.confirmed_yymm or self.yymm_source not in ("UI", "UI_FORCED"):
                raise ValueError(
                    f"[FATAL][JOB_CONTEXT] UI YYMM required but missing for {code4}. "
                    f"confirmed_yymm={self.confirmed_yymm}, source={self.yymm_source}"
                )
        
        return self.confirmed_yymm or ""
    
    def update_status(self, new_status: str, message: str = None):
        """ジョブステータスを更新"""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now()
        
        log_message = f"[{self.updated_at}] Status change: {old_status} -> {new_status}"
        if message:
            log_message += f" ({message})"
        
        self.audit_log.append(log_message)
        logger.info(f"[JOB_CONTEXT] {log_message}")
    
    def add_error(self, error_message: str):
        """エラーメッセージを追加"""
        self.error_messages.append(error_message)
        self.audit_log.append(f"[{datetime.now()}] ERROR: {error_message}")
        logger.error(f"[JOB_CONTEXT] {error_message}")
    
    def start_processing(self, total_files: int):
        """処理開始"""
        self.processing_stats.total_files = total_files
        self.processing_stats.start_time = datetime.now()
        self.update_status("PROCESSING", f"Started processing {total_files} files")
    
    def complete_processing(self, success: bool = True):
        """処理完了"""
        self.processing_stats.end_time = datetime.now()
        status = "COMPLETED" if success else "FAILED"
        
        processing_time = self.processing_stats.get_processing_time()
        message = f"Processed {self.processing_stats.processed_files}/{self.processing_stats.total_files} files"
        if processing_time:
            message += f" in {processing_time:.2f}s"
        
        self.update_status(status, message)
    
    def increment_processed_files(self):
        """処理済みファイル数をインクリメント"""
        self.processing_stats.processed_files += 1
    
    def increment_bundle_splits(self):
        """Bundle分割数をインクリメント"""
        self.processing_stats.bundle_split_count += 1
    
    def increment_ui_forced_files(self):
        """UI強制ファイル数をインクリメント"""
        self.processing_stats.ui_forced_files += 1
    
    def increment_detected_files(self):
        """検出ベースファイル数をインクリメント"""
        self.processing_stats.detected_files += 1
    
    def increment_error_files(self):
        """エラーファイル数をインクリメント"""
        self.processing_stats.error_files += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """処理サマリーを取得"""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "confirmed_yymm": self.confirmed_yymm,
            "yymm_source": self.yymm_source,
            "processing_stats": {
                "total_files": self.processing_stats.total_files,
                "processed_files": self.processing_stats.processed_files,
                "bundle_split_count": self.processing_stats.bundle_split_count,
                "ui_forced_files": self.processing_stats.ui_forced_files,
                "detected_files": self.processing_stats.detected_files,
                "error_files": self.processing_stats.error_files,
                "processing_time": self.processing_stats.get_processing_time()
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "error_count": len(self.error_messages),
            "audit_entries": len(self.audit_log)
        }
    
    def log_summary(self):
        """サマリーをログ出力"""
        summary = self.get_summary()
        logger.info(f"[JOB_CONTEXT] Job Summary: {summary}")
        
        # 詳細な監査ログも出力（デバッグモード時）
        if self.debug_mode:
            logger.debug(f"[JOB_CONTEXT] Audit Log:")
            for entry in self.audit_log:
                logger.debug(f"  {entry}")


# ユーティリティ関数

def create_job_context_from_run_config(run_config: RunConfig, 
                                     job_id: str = None,
                                     output_directory: str = None) -> JobContext:
    """RunConfigからJobContextを作成"""
    import uuid
    
    if job_id is None:
        job_id = f"job_{int(datetime.now().timestamp() * 1000)}"
    
    # YYMM値の確定
    confirmed_yymm = None
    yymm_source = "NONE"
    
    if run_config.has_manual_yymm():
        confirmed_yymm = run_config.manual_yymm
        yymm_source = "UI"
    
    return JobContext(
        job_id=job_id,
        confirmed_yymm=confirmed_yymm,
        yymm_source=yymm_source,
        run_config=run_config,
        batch_mode=run_config.batch_mode,
        debug_mode=run_config.debug_mode,
        output_directory=output_directory
    )


def create_job_context_from_gui(yymm_var_value: str,
                               output_directory: str = None,
                               batch_mode: bool = True,
                               debug_mode: bool = False,
                               job_id: str = None) -> JobContext:
    """GUI入力からJobContextを作成（便利関数）"""
    import uuid
    
    if job_id is None:
        job_id = f"gui_job_{int(datetime.now().timestamp() * 1000)}"
    
    # RunConfigを作成
    run_config = RunConfig.from_ui_input(
        yymm_input=yymm_var_value,
        batch_mode=batch_mode,
        debug_mode=debug_mode
    )
    
    return create_job_context_from_run_config(
        run_config=run_config,
        job_id=job_id,
        output_directory=output_directory
    )


if __name__ == "__main__":
    # テスト実行
    print("JobContext テスト実行")
    print("=" * 50)
    
    # GUI入力からのJobContext作成テスト
    test_cases = [
        {"yymm": "2508", "expected_source": "UI"},
        {"yymm": "25-08", "expected_source": "UI"},
        {"yymm": "", "expected_source": "NONE"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nテスト {i}: yymm='{case['yymm']}'")
        try:
            job_ctx = create_job_context_from_gui(
                yymm_var_value=case["yymm"],
                output_directory="test_output",
                debug_mode=True
            )
            
            print(f"  confirmed_yymm: {job_ctx.confirmed_yymm}")
            print(f"  yymm_source: {job_ctx.yymm_source}")
            print(f"  期待値: {case['expected_source']}")
            
            # UI強制コードテスト
            for code in ["6001", "0001"]:
                try:
                    result_yymm = job_ctx.get_yymm_for_classification(code)
                    print(f"  {code}: {result_yymm} (OK)")
                except ValueError as e:
                    print(f"  {code}: ERROR - {e}")
            
            # サマリー出力
            job_ctx.log_summary()
            
        except Exception as e:
            print(f"  エラー: {e}")
    
    print("\n" + "=" * 50)
    print("JobContext テスト完了")