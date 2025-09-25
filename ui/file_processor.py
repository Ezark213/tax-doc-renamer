#!/usr/bin/env python3
"""
File Processing Module
税務書類ファイル処理機能
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def handle_dropped_files(files: List[str], log: Callable[[str], None], settings: Dict[str, Any], 
                        success_callback: Optional[Callable] = None, error_callback: Optional[Callable] = None) -> tuple[int, int]:
    """
    ファイル処理を実行（元の機能を移植）
    """
    success_count = 0
    error_count = 0
    
    try:
        # ファイルまたはフォルダのパスを判定
        if len(files) == 1 and os.path.isdir(files[0]):
            # フォルダが指定された場合
            folder_path = files[0]
            log(f"フォルダ処理開始: {folder_path}")
            
            # 処理対象ファイルを取得（元のロジックと同じ）
            target_files = []
            try:
                for file in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, file)
                    # ファイルのみを対象（ディレクトリは除外）
                    if os.path.isfile(file_path):
                        # PDFファイル（既存）
                        if file.lower().endswith('.pdf') and not file.startswith('__split_'):
                            target_files.append(file_path)
                        # CSVファイル（新規追加）
                        elif file.lower().endswith('.csv'):
                            target_files.append(file_path)
            except Exception as e:
                log(f"フォルダの読み込みに失敗しました: {e}")
                return 0, 1
            
            if not target_files:
                log(f"選択されたフォルダにPDF・CSVファイルが見つかりませんでした: {folder_path}")
                return 0, 1
            
            # YYMMフォルダを作成（重複時は_2, _3と連番で作成）
            yymm = settings.get('year_month', '2508')
            base_output_folder = os.path.join(folder_path, yymm)
            
            # 既存フォルダがある場合は連番を追加
            counter = 1
            output_folder = base_output_folder
            
            while os.path.exists(output_folder):
                counter += 1
                output_folder = f"{base_output_folder}_{counter}"
            
            try:
                os.makedirs(output_folder, exist_ok=True)
                if counter > 1:
                    log(f"YYMMフォルダ作成（連番）: {output_folder}")
                else:
                    log(f"YYMMフォルダ作成: {output_folder}")
            except Exception as e:
                log(f"YYMMフォルダの作成に失敗しました: {e}")
                return 0, 1
            
            # 各ファイルを処理
            pdf_count = len([f for f in target_files if f.lower().endswith('.pdf')])
            csv_count = len([f for f in target_files if f.lower().endswith('.csv')])
            
            log(f"フォルダ一括処理開始: {len(target_files)}件のファイルを処理")
            log(f"  - PDFファイル: {pdf_count}件")
            log(f"  - CSVファイル: {csv_count}件")
            log(f"処理対象フォルダ: {folder_path}")
            log(f"出力先: {output_folder}")
            
            # 元のmain.pyの処理ロジックを使用
            try:
                # main.pyから必要なクラスとモジュールをインポート
                from main import TaxDocumentRenamerV5
                from core.pdf_processor import PDFProcessor
                from core.classification_v5 import DocumentClassifierV5
                from core.csv_processor import CSVProcessor
                import logging
                
                # ロガーを設定
                logger = logging.getLogger(__name__)
                
                # 必要なエンジンを初期化
                pdf_processor = PDFProcessor(logger=logger)
                classifier_v5 = DocumentClassifierV5(debug_mode=True)
                csv_processor = CSVProcessor()
                
                # 各ファイルを処理
                for i, file_path in enumerate(target_files, 1):
                    filename = os.path.basename(file_path)
                    log(f"処理中 ({i}/{len(target_files)}): {filename}")
                    
                    try:
                        # ファイル拡張子による処理分岐
                        if file_path.lower().endswith('.pdf'):
                            # PDF処理（Bundle分割含む）
                            success = process_single_pdf_file(
                                file_path, output_folder, yymm, pdf_processor, 
                                classifier_v5, settings, log, success_callback, error_callback
                            )
                        elif file_path.lower().endswith('.csv'):
                            # CSV処理
                            success = process_single_csv_file(
                                file_path, output_folder, yymm, csv_processor, log, success_callback, error_callback
                            )
                        else:
                            log(f"未対応ファイル形式: {filename}")
                            continue
                        
                        if success:
                            success_count += 1
                        else:
                            error_count += 1
                            # 処理失敗時のエラーコールバック
                            if error_callback:
                                error_callback(file_path, "処理に失敗しました")
                            
                    except Exception as e:
                        error_count += 1
                        log(f"ファイル処理エラー {filename}: {e}")
                        
                        # エラーコールバックを呼び出し
                        if error_callback:
                            error_callback(file_path, str(e))
                        
                        continue
                
                log(f"フォルダ一括処理完了: {success_count}/{len(target_files)}件処理")
                
            except Exception as e:
                log(f"処理エンジン初期化エラー: {e}")
                return 0, len(target_files)
                
        else:
            # 個別ファイルが指定された場合（従来通り）
            log("個別ファイル処理はサポートされていません")
            error_count = len(files)
            
    except Exception as e:
        log(f"処理エラー: {e}")
        error_count = len(files)
    
    return success_count, error_count


def process_single_pdf_file(file_path: str, output_folder: str, yymm: str, 
                           pdf_processor, classifier_v5, settings: Dict, log: Callable,
                           success_callback: Optional[Callable] = None, error_callback: Optional[Callable] = None) -> bool:
    """PDFファイルの処理（Bundle分割・分類・リネーム）"""
    try:
        filename = os.path.basename(file_path)
        
        # まずBundle分割を試行
        split_result = pdf_processor.maybe_split_pdf(
            input_pdf_path=file_path,
            out_dir=output_folder,
            force=False,
            processing_callback=None
        )
        
        if split_result['success']:
            # Bundle分割が成功した場合
            log(f"Bundle分割完了: {filename}")
            
            # 分割後の各ファイルをリネーム処理
            if split_result.get('split_files'):
                split_files = split_result.get('split_files', [])
                for split_file_path in split_files:
                    try:
                        # 分割後ファイルの分類・リネーム
                        process_pdf_classification_and_rename(
                            split_file_path, output_folder, yymm, classifier_v5, settings, log, success_callback, error_callback
                        )
                        
                        # 一時ファイルを削除
                        if os.path.exists(split_file_path) and os.path.basename(split_file_path).startswith("__split_"):
                            try:
                                os.remove(split_file_path)
                                log(f"一時ファイル削除: {os.path.basename(split_file_path)}")
                            except Exception as cleanup_error:
                                log(f"一時ファイル削除失敗: {cleanup_error}")
                        
                    except Exception as e:
                        log(f"分割後ファイル処理エラー {os.path.basename(split_file_path)}: {e}")
            
            return True
        else:
            # 通常の単一ファイル処理
            return process_pdf_classification_and_rename(
                file_path, output_folder, yymm, classifier_v5, settings, log, success_callback, error_callback
            )
            
    except Exception as e:
        log(f"PDF処理エラー {os.path.basename(file_path)}: {e}")
        return False


def process_pdf_classification_and_rename(file_path: str, output_folder: str, yymm: str,
                                        classifier_v5, settings: Dict, log: Callable,
                                        success_callback: Optional[Callable] = None, error_callback: Optional[Callable] = None) -> bool:
    """PDFファイルの分類・リネーム処理"""
    try:
        filename = os.path.basename(file_path)
        
        # PDFからテキストを抽出
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            log(f"PDF読み取りエラー: {e}")
            text = ""
        
        # 自治体設定を構築
        municipality_sets = {}
        if 'municipality_sets' in settings:
            for muni_set in settings['municipality_sets']:
                set_num = muni_set['set_number']
                municipality_sets[set_num] = {
                    'prefecture': muni_set['prefecture'],
                    'city': muni_set['city']
                }
        
        # ファイル分類
        classification_result = classifier_v5.classify_with_municipality_info_v5(
            text, filename, municipality_sets=municipality_sets
        )
        
        document_type = classification_result.document_type if classification_result else "9999_未分類"
        
        # 新ファイル名生成
        new_filename = f"{document_type}_{yymm}.pdf"
        
        # ファイルコピー（重複回避）
        import shutil
        output_path = os.path.join(output_folder, new_filename)
        
        # 重複回避処理
        counter = 1
        while os.path.exists(output_path):
            name, ext = os.path.splitext(new_filename)
            output_path = os.path.join(output_folder, f"{name}_{counter:03d}{ext}")
            counter += 1
        
        shutil.copy2(file_path, output_path)
        
        # 結果ログ
        if classification_result:
            confidence = f"{classification_result.confidence:.2f}"
            method = classification_result.classification_method
            matched_keywords = classification_result.matched_keywords or []
        else:
            confidence = "0.00"
            method = "未分類"
            matched_keywords = []
        
        log(f"✅ 処理完了: {filename} → {os.path.basename(output_path)}")
        log(f"  - 分類: {document_type}")
        log(f"  - 信頼度: {confidence}")
        log(f"  - 判定方法: {method}")
        if matched_keywords:
            log(f"  - キーワード: {matched_keywords}")
        
        # 成功コールバックを呼び出し
        if success_callback:
            success_callback(file_path, os.path.basename(output_path), document_type, method, confidence, matched_keywords)
        
        return True
        
    except Exception as e:
        log(f"分類・リネーム処理エラー {os.path.basename(file_path)}: {e}")
        return False


def process_single_csv_file(file_path: str, output_folder: str, yymm: str, 
                           csv_processor, log: Callable,
                           success_callback: Optional[Callable] = None, error_callback: Optional[Callable] = None) -> bool:
    """CSVファイルの処理"""
    try:
        filename = os.path.basename(file_path)
        
        # CSV処理
        result = csv_processor.process_csv(file_path)
        
        if not result.success:
            log(f"CSV処理失敗: {result.error_message}")
            return False
        
        # 新ファイル名生成（仕訳帳として処理）
        new_filename = f"5006_仕訳帳_{yymm}.csv"
        
        # ファイルコピー（重複回避）
        import shutil
        output_path = os.path.join(output_folder, new_filename)
        
        counter = 1
        while os.path.exists(output_path):
            name, ext = os.path.splitext(new_filename)
            output_path = os.path.join(output_folder, f"{name}_{counter:03d}{ext}")
            counter += 1
        
        shutil.copy2(file_path, output_path)
        
        log(f"✅ 処理完了: {filename} → {os.path.basename(output_path)}")
        log(f"  - 分類: 5006_仕訳帳")
        log(f"  - 判定方法: CSV自動判定")
        
        # 成功コールバックを呼び出し
        if success_callback:
            success_callback(file_path, os.path.basename(output_path), "5006_仕訳帳", "CSV自動判定", "1.00", ["CSV自動判定"])
        
        return True
        
    except Exception as e:
        log(f"CSV処理エラー {os.path.basename(file_path)}: {e}")
        return False

def handle_folder_processing(folder_path: str, log: Callable[[str], None], settings: Dict[str, Any], 
                            success_callback: Optional[Callable] = None, error_callback: Optional[Callable] = None) -> tuple[int, int]:
    """
    フォルダ処理のラッパー関数
    
    Args:
        folder_path: 処理するフォルダのパス
        log: ログ出力関数
        settings: 設定辞書
    
    Returns:
        tuple: (成功件数, 失敗件数)
    """
    return handle_dropped_files([folder_path], log, settings, success_callback, error_callback)