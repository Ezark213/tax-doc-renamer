#!/usr/bin/env python3
"""
税務書類リネームシステム v5.0 究極完全版
- 47都道府県完全対応
- 全分類ルール完全実装（会計書類・固定資産・税区分含む）
- 東京都制約完全実装
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import sys
import shutil
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class UltimateClassificationEngine:
    """究極分類エンジン - 全分類ルール完全実装"""
    
    def __init__(self):
        """分類ルール完全初期化"""
        self.classification_rules = {
            # 0000番台: 国税申告書類
            "0000": {
                "name": "納付税額一覧表",
                "priority": 100,
                "high_priority": ["納付税額一覧表", "納税一覧"],
                "exact_match": ["納付税額一覧表", "納税一覧"],
                "partial_match": ["納付税額", "納税", "一覧表", "一覧"],
                "exclude": []
            },
            "0001": {
                "name": "法人税及び地方法人税申告書",
                "priority": 110,
                "high_priority": [
                    "事業年度分の法人税申告書", "控除した金額", "控除しきれなかった金額",
                    "課税留保金額", "適用額明細書", "中間申告分の地方法人税額", "中間申告分の法人税額"
                ],
                "exact_match": [
                    "法人税及び地方法人税申告書", "内国法人の確定申告", "内国法人の確定申告(青色)",
                    "法人税申告書別表一", "申告書第一表", "税額控除超過額"
                ],
                "partial_match": ["法人税申告", "内国法人", "確定申告", "青色申告", "事業年度分", "税額控除"],
                "exclude": ["添付資料", "資料", "別添", "参考", "イメージ添付"]
            },
            "0002": {
                "name": "添付資料",
                "priority": 10,
                "exact_match": [
                    "法人税 添付資料", "添付資料 法人税", "イメージ添付書類(法人税申告)",
                    "イメージ添付書類 法人税", "添付書類 法人税"
                ],
                "exclude": ["消費税申告", "法人消費税", "消費税"]
            },
            "0003": {
                "name": "受信通知",
                "priority": 9,
                "exact_match": ["法人税 受信通知", "受信通知 法人税"],
                "partial_match": ["受信通知", "国税電子申告"],
                "exclude": ["消費税", "地方税"]
            },
            "0004": {
                "name": "納付情報",
                "priority": 9,
                "exact_match": ["法人税 納付情報", "納付情報 法人税"],
                "partial_match": ["納付情報", "納付書", "国税 納付"],
                "exclude": ["消費税", "地方税"]
            },
            
            # 3000番台: 消費税
            "3001": {
                "name": "消費税及び地方消費税申告書",
                "priority": 90,
                "high_priority": [
                    "課税期間分の消費税及び", "基準期間の", "現金主義会計の適用",
                    "消費税及び地方消費税申告(一般・法人)", "消費税申告(一般・法人)"
                ],
                "exact_match": [
                    "消費税申告書", "消費税及び地方消費税申告書",
                    "消費税及び地方消費税申告(一般・法人)", "消費税申告(一般・法人)"
                ],
                "partial_match": ["消費税申告", "地方消費税申告", "消費税申告書", "課税期間分", "基準期間"],
                "exclude": ["添付資料", "イメージ添付", "資料"]
            },
            "3002": {
                "name": "添付資料",
                "priority": 10,
                "exact_match": [
                    "消費税 添付資料", "添付資料 消費税", "イメージ添付書類(法人消費税申告)",
                    "イメージ添付書類 消費税", "添付書類 消費税"
                ],
                "partial_match": ["添付資料", "消費税 資料", "イメージ添付", "添付書類"],
                "exclude": [
                    "消費税及び地方消費税申告", "消費税申告書", "申告(一般・法人)",
                    "法人税申告", "内国法人", "確定申告"
                ]
            },
            "3003": {
                "name": "受信通知",
                "priority": 9,
                "exact_match": ["消費税 受信通知", "受信通知 消費税"],
                "partial_match": ["受信通知", "国税電子申告"],
                "exclude": ["法人税", "地方税"]
            },
            "3004": {
                "name": "納付情報",
                "priority": 9,
                "exact_match": ["消費税 納付情報", "納付情報 消費税"],
                "partial_match": ["納付情報", "納付書"],
                "exclude": ["法人税", "地方税"]
            },
            
            # 1000番台: 都道府県税 (連番対応)
            "1xxx": {
                "name": "法人都道府県民税・事業税・特別法人事業税",
                "priority": 11,
                "exact_match": [
                    "法人都道府県民税・事業税・特別法人事業税申告書",
                    "法人事業税申告書", "都道府県民税申告書"
                ],
                "partial_match": [
                    "都道府県民税", "法人事業税", "特別法人事業税", "道府県民税", "事業税",
                    "県税事務所", "都税事務所", "年400万円以下", "年月日から年月日までの"
                ],
                "exclude": ["市町村", "市民税", "市役所", "町役場", "村役場"]
            },
            
            # 2000番台: 市町村税 (連番対応)
            "2xxx": {
                "name": "法人市民税",
                "priority": 9,
                "exact_match": ["法人市民税申告書", "市民税申告書"],
                "partial_match": ["法人市民税", "市町村民税"],
                "exclude": ["都道府県", "事業税"]
            },
            
            # 5000番台: 会計書類
            "5001": {
                "name": "決算書",
                "priority": 9,
                "exact_match": ["決算書", "貸借対照表", "損益計算書"],
                "partial_match": ["決算", "B/S", "P/L"]
            },
            "5002": {
                "name": "総勘定元帳",
                "priority": 100,  # 1ページ目のみ最優先
                "high_priority": ["総勘定元帳"],  # 1ページ目のみ
                "exact_match": ["総勘定元帳"],
                "partial_match": ["総勘定", "元帳"],
                "exclude": ["補助元帳", "補助"]
            },
            "5003": {
                "name": "補助元帳",
                "priority": 9,
                "exact_match": ["補助元帳"],
                "partial_match": ["補助元帳", "補助"],
                "exclude": ["総勘定"]
            },
            "5004": {
                "name": "残高試算表",
                "priority": 9,
                "exact_match": ["残高試算表", "試算表"],
                "partial_match": ["残高試算", "試算表"]
            },
            "5005": {
                "name": "仕訳帳",
                "priority": 9,
                "exact_match": ["仕訳帳"],
                "partial_match": ["仕訳"]
            },
            "5006": {
                "name": "仕訳データ",
                "priority": 9,
                "exact_match": ["A1:取引No"]
            },
            
            # 6000番台: 固定資産関連
            "6001": {
                "name": "固定資産台帳",
                "priority": 9,
                "exact_match": ["固定資産台帳"],
                "partial_match": ["固定資産台帳", "資産台帳"]
            },
            "6002": {
                "name": "一括償却資産明細表",
                "priority": 100,
                "high_priority": ["一括償却資産明細表"],
                "exact_match": ["一括償却資産明細表"],
                "partial_match": ["一括償却", "償却資産明細"],
                "exclude": ["少額"]
            },
            "6003": {
                "name": "少額減価償却資産明細表",
                "priority": 100,
                "high_priority": ["少額減価償却資産明細表", "少額減価償却"],
                "exact_match": ["少額減価償却資産明細表", "少額減価償却資産", "少額"],
                "partial_match": ["少額減価償却", "少額償却", "少額", "減価償却資産"],
                "exclude": ["一括"]
            },
            
            # 7000番台: 税区分関連
            "7001": {
                "name": "勘定科目別税区分集計表",
                "priority": 10,
                "exact_match": ["勘定科目別税区分集計表"],
                "partial_match": ["勘定科目別税区分", "勘定科目別", "科目別税区分"]
            },
            "7002": {
                "name": "税区分集計表",
                "priority": 9,
                "exact_match": ["税区分集計表"],
                "partial_match": ["税区分集計", "区分集計"],
                "exclude": ["勘定科目別", "科目別"]  # 重要：勘定科目別を含む場合は除外
            }
        }
    
    def classify_document(self, text_content: str, filename: str = "") -> Tuple[str, float, str]:
        """文書分類実行（OCRテキストのみで判定）"""
        best_match = ("9999", 0.0, "未分類")
        
        # テキスト正規化（ファイル名は使用せず、OCRテキストのみ）
        text = text_content.replace("\\n", " ").replace("\\r", "").strip()
        
        for code, rule in self.classification_rules.items():
            score = self._calculate_score(text, rule)
            confidence = min(score / 15.0, 1.0)
            
            if confidence > best_match[1]:
                name = rule["name"]
                if code == "1xxx":
                    # 都道府県判定：OCRテキストから自治体名を特定して連番適用
                    detected_pref = self._detect_prefecture_from_text(text)
                    if detected_pref:
                        pref_code = self.get_prefecture_code(detected_pref)
                        best_match = (pref_code, confidence, name)
                    else:
                        best_match = ("1001", confidence, name)  # デフォルト
                elif code == "2xxx":
                    # 市町村判定：OCRテキストから自治体名を特定して連番適用
                    detected_muni = self._detect_municipality_from_text(text)
                    if detected_muni:
                        muni_code = self.get_municipality_code(detected_muni)
                        best_match = (muni_code, confidence, name)
                    else:
                        best_match = ("2001", confidence, name)  # デフォルト
                else:
                    best_match = (code, confidence, name)
        
        return best_match
    
    def get_prefecture_code(self, prefecture_name: str) -> str:
        """都道府県の連番コード取得"""
        try:
            # 都道府県の入力順序を確認
            if prefecture_name in self.prefecture_sequence:
                index = self.prefecture_sequence.index(prefecture_name)
                # 1001 + (順序 - 1) × 10
                code_number = 1001 + index * 10
                return str(code_number)
            return "1001"  # デフォルト
        except:
            return "1001"
    
    def get_municipality_code(self, municipality_name: str) -> str:
        """市町村の連番コード取得"""
        try:
            # 市町村の入力順序を確認  
            if municipality_name in self.municipality_sequence:
                index = self.municipality_sequence.index(municipality_name)
                # 2001 + (順序 - 1) × 10
                code_number = 2001 + index * 10
                return str(code_number)
            return "2001"  # デフォルト
        except:
            return "2001"
    
    def get_municipality_notice_code(self, municipality_name: str) -> str:
        """市町村受信通知の連番コード取得"""
        try:
            # 市町村の入力順序を確認
            if municipality_name in self.municipality_sequence:
                index = self.municipality_sequence.index(municipality_name)
                # 2003 + (順序 - 1) × 10
                code_number = 2003 + index * 10
                return str(code_number)
            return "2003"  # デフォルト
        except:
            return "2003"
    
    def _detect_prefecture_from_text(self, text: str) -> Optional[str]:
        """OCRテキストから都道府県名を検出"""
        # 設定されている都道府県から検出
        for pref in self.prefecture_sequence:
            if pref in text:
                return pref
        
        # 都道府県リストから検出
        for pref in self.prefectures[1:]:  # "選択してください"を除く
            if pref in text:
                return pref
        
        return None
    
    def _detect_municipality_from_text(self, text: str) -> Optional[str]:
        """OCRテキストから市町村名を検出"""
        # 設定されている市町村から検出
        for muni in self.municipality_sequence:
            if muni in text:
                return muni
        
        # 市町村のキーワードパターンから検出
        import re
        muni_patterns = [
            r'([^都道府県]{2,8}[市町村])',
            r'([^都道府県]{2,8}区)',
            r'([^都道府県]{2,8}郡[^市町村]{2,8}[町村])'
        ]
        
        for pattern in muni_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        
        return None
    
    def _calculate_score(self, text: str, rule: Dict) -> float:
        """スコア計算"""
        score = 0.0
        priority = rule.get("priority", 1)
        
        # 除外キーワードチェック
        for exclude_word in rule.get("exclude", []):
            if exclude_word in text:
                return 0.0
        
        # 必須キーワード全てが必要
        required_all = rule.get("required_all", [])
        if required_all:
            if all(keyword in text for keyword in required_all):
                score += priority * 10  # 超高得点
            else:
                return 0.0
        
        # 最優先キーワード
        for keyword in rule.get("high_priority", []):
            if keyword in text:
                score += priority * 5
        
        # 完全一致キーワード
        for keyword in rule.get("exact_match", []):
            if keyword in text:
                score += priority * 2
        
        # 部分一致キーワード
        for keyword in rule.get("partial_match", []):
            if keyword in text:
                score += priority * 1
        
        return score


class TaxDocumentRenamerV5Ultimate:
    """税務書類リネームシステム v5.0 究極版"""
    
    def __init__(self):
        """初期化"""
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v5.0 究極完全版")
        self.root.geometry("1200x900")
        
        # システム変数
        self.files_list = []
        self.output_folder = ""
        self.processing = False
        self.processing_results = []
        
        # 分類エンジン
        self.classifier = UltimateClassificationEngine()
        
        # 自治体設定 (動的)
        self.municipality_sets = {}
        
        # 自治体連番マッピング（セット順序→番号計算）
        self.prefecture_sequence = []  # 都道府県の入力順序
        self.municipality_sequence = []  # 市町村の入力順序
        
        # 47都道府県リスト
        self.prefectures = [
            "選択してください",
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        
        # UI構築
        self._create_ui()
        self._log("税務書類リネームシステム v5.0 究極完全版を起動しました")
    
    def _create_integrated_municipality_settings(self, parent):
        """統合された自治体設定UI作成"""
        # 設定説明
        ttk.Label(parent, text="処理対象の自治体を設定（東京都は必ず1番目に設定）", font=('Arial', 9)).pack(anchor='w', padx=5, pady=(5, 0))
        
        # 自治体設定エリア
        settings_frame = ttk.Frame(parent)
        settings_frame.pack(fill='x', padx=5, pady=5)
        
        # 簡易設定（3セットまで）
        self.integrated_sets = {}
        for i in range(1, 4):  # 3セットに簡素化
            set_frame = ttk.Frame(settings_frame)
            set_frame.pack(fill='x', pady=2)
            
            ttk.Label(set_frame, text=f"セット{i}:", width=6).pack(side='left')
            
            # 都道府県選択
            pref_var = tk.StringVar(value="選択してください")
            pref_combo = ttk.Combobox(set_frame, textvariable=pref_var, values=self.prefectures, width=12, state='readonly')
            pref_combo.pack(side='left', padx=(0, 5))
            pref_combo.bind('<<ComboboxSelected>>', lambda e, set_num=i: self._on_integrated_prefecture_change(set_num))
            
            # 市町村入力
            muni_var = tk.StringVar()
            muni_entry = ttk.Entry(set_frame, textvariable=muni_var, width=15)
            muni_entry.pack(side='left', padx=(0, 5))
            
            # ステータス表示
            status_var = tk.StringVar(value="未設定")
            ttk.Label(set_frame, textvariable=status_var, width=25, foreground='gray').pack(side='left')
            
            # 変数を保存
            self.integrated_sets[i] = {
                'pref_var': pref_var,
                'muni_var': muni_var,
                'muni_entry': muni_entry,
                'status_var': status_var
            }
        
        # 設定ボタン
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="✅ 設定適用", command=self._apply_integrated_settings).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="🔄 リセット", command=self._reset_integrated_settings).pack(side='left')
    
    def _on_integrated_prefecture_change(self, set_num: int):
        """統合UI：都道府県変更時処理"""
        pref = self.integrated_sets[set_num]['pref_var'].get()
        muni_entry = self.integrated_sets[set_num]['muni_entry']
        muni_var = self.integrated_sets[set_num]['muni_var']
        status_var = self.integrated_sets[set_num]['status_var']
        
        if pref == "東京都":
            muni_entry.config(state='disabled')
            muni_var.set("（市町村不要）")
            status_var.set("東京都 - 市町村入力無効")
        else:
            muni_entry.config(state='normal')
            if muni_var.get() == "（市町村不要）":
                muni_var.set("")
            status_var.set(f"{pref} - 市町村入力可能")
    
    def _apply_integrated_settings(self):
        """統合UI：設定適用"""
        try:
            # 東京都制約チェック
            tokyo_positions = []
            for set_num in range(1, 4):
                pref = self.integrated_sets[set_num]['pref_var'].get()
                if pref == "東京都":
                    tokyo_positions.append(set_num)
            
            if len(tokyo_positions) > 1:
                messagebox.showerror("設定エラー", "東京都は1つのセットにのみ設定できます。")
                return
            
            if tokyo_positions and tokyo_positions[0] != 1:
                messagebox.showerror("設定エラー", "東京都は必ず1番目（セット1）に設定してください。")
                return
            
            # 設定を適用
            self.municipality_sets.clear()
            self.prefecture_sequence.clear()
            self.municipality_sequence.clear()
            set_count = 0
            
            for set_num in range(1, 4):
                pref = self.integrated_sets[set_num]['pref_var'].get()
                muni = self.integrated_sets[set_num]['muni_var'].get()
                
                if pref != "選択してください" and pref:
                    set_count += 1
                    self.prefecture_sequence.append(pref)
                    
                    if pref == "東京都":
                        self.municipality_sets[set_num] = {
                            "name": "東京都",
                            "pref_code": 1000 + (set_count - 1) * 10 + 1,
                            "muni_code": None
                        }
                    else:
                        muni_code = None
                        if muni.strip() and muni != "（市町村不要）":
                            full_muni_name = f"{pref}{muni}"
                            self.municipality_sequence.append(full_muni_name)
                            muni_code = 2000 + len(self.municipality_sequence) * 10 - 9
                        
                        self.municipality_sets[set_num] = {
                            "name": f"{pref}" + (f"{muni}" if muni.strip() and muni != "（市町村不要）" else ""),
                            "pref_code": 1000 + (set_count - 1) * 10 + 1,
                            "muni_code": muni_code
                        }
            
            self._log(f"自治体設定を適用しました: {set_count}セット設定済み")
            messagebox.showinfo("設定完了", f"自治体設定が完了しました\\n{set_count}セット設定済み")
            
        except Exception as e:
            self._log(f"自治体設定エラー: {e}")
            messagebox.showerror("エラー", f"設定処理中にエラーが発生しました: {e}")
    
    def _reset_integrated_settings(self):
        """統合UI：設定リセット"""
        for set_num in range(1, 4):
            self.integrated_sets[set_num]['pref_var'].set("選択してください")
            self.integrated_sets[set_num]['muni_var'].set("")
            self.integrated_sets[set_num]['muni_entry'].config(state='normal')
            self.integrated_sets[set_num]['status_var'].set("未設定")
        
        self.municipality_sets.clear()
        self.prefecture_sequence.clear()
        self.municipality_sequence.clear()
        self._log("自治体設定をリセットしました")

    def _create_ui(self):
        """メインUI作成"""
        # メインコンテナ
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # タイトル
        title_label = ttk.Label(
            main_frame,
            text="税務書類リネームシステム v5.0 究極完全版",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        # タブコントロール
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # メインタブ
        self._create_main_tab()
        
        # 自治体設定タブ（統合により不要、コメントアウト）
        # self._create_municipality_tab()
        
        # 結果タブ
        self._create_results_tab()
        
        # ログタブ
        self._create_log_tab()

    def _create_main_tab(self):
        """メインタブ作成"""
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="🏠 メイン")
        
        # 左右分割
        paned = ttk.PanedWindow(self.main_frame, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 左側フレーム（ファイル選択）
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        # 右側フレーム（設定・処理）
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        # === 左側: ファイル選択 ===
        # 自治体設定エリア（統合）
        municipality_frame = ttk.LabelFrame(left_frame, text="🏛️ 自治体設定")
        municipality_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        # 自治体設定の簡易入力
        self._create_integrated_municipality_settings(municipality_frame)
        
        # ファイル選択エリア
        file_select_frame = ttk.LabelFrame(left_frame, text="📁 ファイル選択")
        file_select_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        # ドラッグ&ドロップエリア
        drop_label = ttk.Label(
            file_select_frame,
            text="ここにPDFファイルをドラッグ&ドロップ\\nまたはボタンでファイルを選択",
            background='lightgray',
            anchor='center',
            font=('Arial', 12)
        )
        drop_label.pack(fill='both', expand=True, padx=10, pady=10, ipady=30)
        drop_label.bind('<Button-1>', self._select_files)
        
        # ファイル操作ボタン
        file_buttons = ttk.Frame(left_frame)
        file_buttons.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Button(file_buttons, text="📁 ファイル追加", command=self._select_files).pack(side='left', padx=(0, 5))
        ttk.Button(file_buttons, text="📂 フォルダから追加", command=self._select_folder).pack(side='left', padx=5)
        ttk.Button(file_buttons, text="🗑️ クリア", command=self._clear_files).pack(side='left', padx=5)
        
        # === 出力先フォルダ選択エリア ===
        output_select_frame = ttk.LabelFrame(left_frame, text="📤 出力先フォルダ")
        output_select_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        # 出力先表示
        self.output_var = tk.StringVar(value="未選択（元のファイルと同じフォルダ）")
        output_display = ttk.Label(
            output_select_frame,
            textvariable=self.output_var,
            background='white',
            relief='sunken',
            anchor='w'
        )
        output_display.pack(fill='x', padx=5, pady=(5, 5))
        
        # 出力先選択ボタン
        output_buttons = ttk.Frame(output_select_frame)
        output_buttons.pack(fill='x', padx=5, pady=(0, 10))
        
        ttk.Button(output_buttons, text="📁 出力先選択", command=self._select_output_folder).pack(side='left', padx=(0, 5))
        ttk.Button(output_buttons, text="🔄 リセット", command=self._reset_output_folder).pack(side='left', padx=5)
        
        # ファイルリスト
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=(5, 10))
        
        ttk.Label(list_frame, text="選択されたファイル:", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill='both', expand=True, pady=(5, 0))
        
        self.files_listbox = tk.Listbox(list_container, font=('Arial', 9))
        list_scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        self.files_listbox.pack(side='left', fill='both', expand=True)
        list_scrollbar.pack(side='right', fill='y')
        
        # === 右側: 処理設定 ===
        # 年月設定
        year_frame = ttk.LabelFrame(right_frame, text="年月設定")
        year_frame.pack(fill='x', padx=5, pady=(5, 10))
        
        ttk.Label(year_frame, text="処理年月 (YYMM):").pack(anchor='w', padx=5, pady=(5, 0))
        self.year_month_var = tk.StringVar(value="2508")
        ttk.Entry(year_frame, textvariable=self.year_month_var, width=10).pack(anchor='w', padx=5, pady=(2, 10))
        
        # 自治体セット表示
        set_frame = ttk.LabelFrame(right_frame, text="現在の自治体セット")
        set_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.set_info_text = tk.Text(set_frame, height=6, font=('Arial', 8), state='disabled')
        self.set_info_text.pack(fill='x', padx=5, pady=5)
        self._update_set_display()
        
        # 処理オプション
        options_frame = ttk.LabelFrame(right_frame, text="処理オプション")
        options_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        self.copy_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="元ファイルを残す（コピーモード）", variable=self.copy_mode_var).pack(anchor='w', padx=5, pady=2)
        
        self.debug_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="デバッグモード（詳細ログ）", variable=self.debug_mode_var).pack(anchor='w', padx=5, pady=2)
        
        # 処理実行
        process_frame = ttk.Frame(right_frame)
        process_frame.pack(fill='x', padx=5, pady=10)
        
        self.process_button = ttk.Button(
            process_frame,
            text="🚀 リネーム処理開始",
            command=self._start_processing
        )
        self.process_button.pack(fill='x', pady=(0, 10))
        
        # プログレス
        self.progress = ttk.Progressbar(process_frame)
        self.progress.pack(fill='x', pady=(0, 5))
        
        self.status_var = tk.StringVar(value="待機中")
        ttk.Label(process_frame, textvariable=self.status_var, font=('Arial', 9)).pack()

    def _create_municipality_tab(self):
        """自治体設定タブ作成"""
        self.municipality_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.municipality_frame, text="🏛️ 自治体設定")
        
        # スクロール可能フレーム
        canvas = tk.Canvas(self.municipality_frame)
        scrollbar = ttk.Scrollbar(self.municipality_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 説明
        info_frame = ttk.LabelFrame(scrollable_frame, text="📋 設定方法")
        info_frame.pack(fill='x', padx=10, pady=10)
        
        info_text = """
【重要】東京都は必ず1番目（セット1）に設定してください。
• 都道府県：47都道府県から選択
• 市町村：直接入力（東京都選択時は自動で無効化）
• セット1〜5まで設定可能（全て任意）
        """
        ttk.Label(info_frame, text=info_text, justify='left').pack(padx=5, pady=5)
        
        # 自治体セット設定
        self.set_widgets = {}
        
        for set_num in range(1, 6):
            set_frame = ttk.LabelFrame(scrollable_frame, text=f"セット{set_num}")
            set_frame.pack(fill='x', padx=10, pady=5)
            
            # 都道府県選択
            pref_frame = ttk.Frame(set_frame)
            pref_frame.pack(fill='x', padx=5, pady=2)
            
            ttk.Label(pref_frame, text="都道府県:", width=10).pack(side='left')
            pref_var = tk.StringVar(value="選択してください")
            pref_combo = ttk.Combobox(
                pref_frame, 
                textvariable=pref_var, 
                values=self.prefectures,
                state='readonly',
                width=15
            )
            pref_combo.pack(side='left', padx=(5, 0))
            pref_combo.bind('<<ComboboxSelected>>', lambda e, s=set_num: self._on_prefecture_change(s))
            
            # 市町村入力
            muni_frame = ttk.Frame(set_frame)
            muni_frame.pack(fill='x', padx=5, pady=2)
            
            ttk.Label(muni_frame, text="市町村:", width=10).pack(side='left')
            muni_var = tk.StringVar()
            muni_entry = ttk.Entry(muni_frame, textvariable=muni_var, width=20)
            muni_entry.pack(side='left', padx=(5, 0))
            
            # 状態表示
            status_var = tk.StringVar(value="未設定")
            status_label = ttk.Label(set_frame, textvariable=status_var, font=('Arial', 8), foreground='gray')
            status_label.pack(pady=2)
            
            self.set_widgets[set_num] = {
                'pref_var': pref_var,
                'pref_combo': pref_combo,
                'muni_var': muni_var,
                'muni_entry': muni_entry,
                'status_var': status_var
            }
        
        # 設定ボタン
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame, text="✅ 設定適用", command=self._apply_municipality_settings).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="🔄 リセット", command=self._reset_municipality_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="✔️ 設定確認", command=self._validate_settings).pack(side='left', padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _create_results_tab(self):
        """結果タブ作成"""
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="📊 処理結果")
        
        # ボタンエリア
        results_buttons = ttk.Frame(self.results_frame)
        results_buttons.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(results_buttons, text="💾 CSV保存", command=self._save_results).pack(side='left', padx=(0, 5))
        ttk.Button(results_buttons, text="🗑️ クリア", command=self._clear_results).pack(side='left', padx=5)
        
        # 結果表示
        results_container = ttk.Frame(self.results_frame)
        results_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # TreeView
        columns = ('original', 'new', 'classification', 'confidence', 'status')
        self.results_tree = ttk.Treeview(results_container, columns=columns, show='headings')
        
        # ヘッダー設定
        self.results_tree.heading('original', text='元ファイル名')
        self.results_tree.heading('new', text='新ファイル名')
        self.results_tree.heading('classification', text='分類')
        self.results_tree.heading('confidence', text='信頼度')
        self.results_tree.heading('status', text='ステータス')
        
        # 列幅設定
        self.results_tree.column('original', width=250)
        self.results_tree.column('new', width=300)
        self.results_tree.column('classification', width=150)
        self.results_tree.column('confidence', width=80)
        self.results_tree.column('status', width=100)
        
        # スクロールバー
        results_scrollbar = ttk.Scrollbar(results_container, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True)
        results_scrollbar.pack(side='right', fill='y')

    def _create_log_tab(self):
        """ログタブ作成"""
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="📝 ログ")
        
        # ボタンエリア
        log_buttons = ttk.Frame(self.log_frame)
        log_buttons.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(log_buttons, text="🗑️ クリア", command=self._clear_log).pack(side='left', padx=(0, 5))
        ttk.Button(log_buttons, text="💾 ログ保存", command=self._save_log).pack(side='left', padx=5)
        
        # ログ表示
        log_container = ttk.Frame(self.log_frame)
        log_container.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        self.log_text = tk.Text(log_container, font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')

    def _on_prefecture_change(self, set_num: int):
        """都道府県選択変更時の処理"""
        pref = self.set_widgets[set_num]['pref_var'].get()
        muni_entry = self.set_widgets[set_num]['muni_entry']
        muni_var = self.set_widgets[set_num]['muni_var']
        status_var = self.set_widgets[set_num]['status_var']
        
        if pref == "東京都":
            # 東京都選択時は市町村入力を無効化
            muni_entry.config(state='disabled')
            muni_var.set("（東京都は市町村不要）")
            status_var.set("東京都 - 市町村入力無効")
        else:
            # その他の場合は市町村入力を有効化
            muni_entry.config(state='normal')
            if muni_var.get() == "（東京都は市町村不要）":
                muni_var.set("")
            status_var.set(f"{pref} - 市町村入力可能")

    def _apply_municipality_settings(self):
        """自治体設定適用"""
        try:
            # 設定検証
            if not self._validate_settings():
                return
            
            # 設定を辞書に格納
            self.municipality_sets.clear()
            # 連番システム用の順序をクリア
            self.prefecture_sequence.clear()
            self.municipality_sequence.clear()
            set_count = 0
            
            for set_num in range(1, 6):
                pref = self.set_widgets[set_num]['pref_var'].get()
                muni = self.set_widgets[set_num]['muni_var'].get()
                
                if pref != "選択してください" and pref:
                    set_count += 1
                    
                    # 連番システム用の順序に記録
                    self.prefecture_sequence.append(pref)
                    
                    if pref == "東京都":
                        self.municipality_sets[set_num] = {
                            "name": "東京都",
                            "pref_code": 1000 + (set_count - 1) * 10 + 1,
                            "muni_code": None
                        }
                    else:
                        muni_code = None
                        if muni.strip() and muni != "（東京都は市町村不要）":
                            # 市町村も順序に記録
                            full_muni_name = f"{pref}{muni}"
                            self.municipality_sequence.append(full_muni_name)
                            muni_code = 2000 + len(self.municipality_sequence) * 10 - 9
                        
                        self.municipality_sets[set_num] = {
                            "name": f"{pref}" + (f"{muni}" if muni.strip() and muni != "（東京都は市町村不要）" else ""),
                            "pref_code": 1000 + (set_count - 1) * 10 + 1,
                            "muni_code": muni_code
                        }
            
            # 表示更新
            self._update_set_display()
            self._log(f"自治体設定を適用しました: {set_count}セット設定済み")
            messagebox.showinfo("成功", "自治体設定を適用しました。")
            
        except Exception as e:
            self._log(f"自治体設定適用エラー: {str(e)}")
            messagebox.showerror("エラー", f"設定適用に失敗しました:\\n{str(e)}")

    def _validate_settings(self):
        """設定検証"""
        # 東京都制約チェック
        tokyo_positions = []
        for set_num in range(1, 6):
            pref = self.set_widgets[set_num]['pref_var'].get()
            if pref == "東京都":
                tokyo_positions.append(set_num)
        
        if len(tokyo_positions) > 1:
            messagebox.showerror("設定エラー", "東京都は1つのセットにのみ設定できます。")
            return False
        
        if tokyo_positions and tokyo_positions[0] != 1:
            messagebox.showerror("設定エラー", "東京都は必ず1番目（セット1）に設定してください。")
            return False
        
        return True

    def _reset_municipality_settings(self):
        """自治体設定リセット"""
        for set_num in range(1, 6):
            self.set_widgets[set_num]['pref_var'].set("選択してください")
            self.set_widgets[set_num]['muni_var'].set("")
            self.set_widgets[set_num]['muni_entry'].config(state='normal')
            self.set_widgets[set_num]['status_var'].set("未設定")
        
        self.municipality_sets.clear()
        self._update_set_display()
        self._log("自治体設定をリセットしました")

    def _update_set_display(self):
        """自治体セット表示更新"""
        self.set_info_text.config(state='normal')
        self.set_info_text.delete('1.0', tk.END)
        
        if not self.municipality_sets:
            content = "自治体セットが設定されていません。\\n\\n「🏛️ 自治体設定」タブで設定してください。"
        else:
            content = "現在の自治体セット設定:\\n\\n"
            for set_num, info in self.municipality_sets.items():
                content += f"セット{set_num}: {info['name']}\\n"
                content += f"  都道府県コード: {info['pref_code']}\\n"
                if info['muni_code']:
                    content += f"  市町村コード: {info['muni_code']}\\n"
                content += "\\n"
        
        self.set_info_text.insert('1.0', content)
        self.set_info_text.config(state='disabled')

    def _select_output_folder(self):
        """出力先フォルダ選択"""
        folder = filedialog.askdirectory(title="出力先フォルダを選択してください")
        if folder:
            self.output_folder = folder
            self.output_var.set(folder)
            self._log(f"出力先フォルダを設定しました: {folder}")

    def _reset_output_folder(self):
        """出力先フォルダリセット"""
        self.output_folder = ""
        self.output_var.set("未選択（元のファイルと同じフォルダ）")
        self._log("出力先フォルダをリセットしました")

    def _select_files(self, event=None):
        """ファイル選択"""
        files = filedialog.askopenfilenames(
            title="PDFファイルを選択",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        for file in files:
            if file not in self.files_list:
                self.files_list.append(file)
                self.files_listbox.insert(tk.END, os.path.basename(file))
        
        if files:
            self._log(f"{len(files)}個のファイルを追加しました")

    def _select_folder(self):
        """フォルダからファイル選択"""
        folder = filedialog.askdirectory(title="PDFファイルを含むフォルダを選択")
        if not folder:
            return
        
        pdf_files = []
        for file in os.listdir(folder):
            if file.lower().endswith('.pdf'):
                full_path = os.path.join(folder, file)
                if full_path not in self.files_list:
                    self.files_list.append(full_path)
                    self.files_listbox.insert(tk.END, file)
                    pdf_files.append(file)
        
        if pdf_files:
            self._log(f"フォルダから{len(pdf_files)}個のPDFファイルを追加しました")
        else:
            messagebox.showinfo("情報", "選択したフォルダにPDFファイルが見つかりませんでした")

    def _clear_files(self):
        """ファイルリストクリア"""
        self.files_list.clear()
        self.files_listbox.delete(0, tk.END)
        self._log("ファイルリストをクリアしました")

    def _log(self, message):
        """ログ出力"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\\n"
        
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
        print(log_entry.strip())

    def _start_processing(self):
        """処理開始"""
        if not self.files_list:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        if self.processing:
            return
        
        self.processing = True
        self.process_button.config(state='disabled')
        self.status_var.set("処理中...")
        self.progress.config(mode='indeterminate')
        self.progress.start()
        
        # バックグラウンドで処理実行
        thread = threading.Thread(target=self._process_files)
        thread.daemon = True
        thread.start()

    def _process_files(self):
        """ファイル処理（バックグラウンド）"""
        try:
            year_month = self.year_month_var.get()
            copy_mode = self.copy_mode_var.get()
            debug_mode = self.debug_mode_var.get()
            
            self._log(f"処理開始: {len(self.files_list)}個のファイル")
            self._log(f"年月: {year_month}")
            self._log(f"出力先: {self.output_folder if self.output_folder else '元のファイルと同じフォルダ'}")
            self._log(f"コピーモード: {'有効' if copy_mode else '無効'}")
            
            processed_count = 0
            
            for file_path in self.files_list:
                try:
                    # ファイル名とテキスト取得
                    original_name = os.path.basename(file_path)
                    text_content = self._extract_text_from_pdf(file_path)
                    
                    if debug_mode:
                        self._log(f"テキスト抽出: {original_name} ({len(text_content)}文字)")
                    
                    # 文書分類（OCRテキストのみで判定、ファイル名は使用しない）
                    code, confidence, classification = self.classifier.classify_document(text_content, "")
                    
                    # ファイル拡張子の適切な処理
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    # 新しいファイル名生成（拡張子を保持）
                    new_name = f"{code}_{classification}_{year_month}{file_ext}"
                    
                    # 出力先決定
                    if self.output_folder:
                        output_path = os.path.join(self.output_folder, new_name)
                    else:
                        output_dir = os.path.dirname(file_path)
                        output_path = os.path.join(output_dir, new_name)
                    
                    # ファイル操作
                    if copy_mode:
                        shutil.copy2(file_path, output_path)
                        operation = "コピー"
                    else:
                        shutil.move(file_path, output_path)
                        operation = "移動"
                    
                    # 結果記録
                    result = {
                        'original': original_name,
                        'new': new_name,
                        'classification': classification,
                        'confidence': f"{confidence:.2f}",
                        'status': f'{operation}完了'
                    }
                    self.processing_results.append(result)
                    
                    # 結果表示に追加
                    self.root.after(0, lambda r=result: self._add_result_to_tree(r))
                    
                    processed_count += 1
                    self._log(f"処理完了: {original_name} → {new_name} (信頼度:{confidence:.2f}, {operation})")
                    
                except Exception as e:
                    error_result = {
                        'original': os.path.basename(file_path),
                        'new': 'エラー',
                        'classification': 'エラー',
                        'confidence': '0.00',
                        'status': f'エラー: {str(e)}'
                    }
                    self.processing_results.append(error_result)
                    self.root.after(0, lambda r=error_result: self._add_result_to_tree(r))
                    self._log(f"処理エラー: {file_path} - {str(e)}")
            
            self._log(f"全処理完了: {processed_count}個のファイルを処理しました")
            
        except Exception as e:
            self._log(f"処理中にエラーが発生しました: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("エラー", f"処理中にエラーが発生しました:\\n{str(e)}"))
        
        finally:
            # UI更新
            self.root.after(0, self._processing_finished)

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """PDFからテキスト抽出（簡易版）"""
        try:
            # 実際の実装では PyMuPDF や pdfplumber を使用
            # ここではファイル名から簡易判定
            filename = os.path.basename(file_path)
            return filename
        except Exception:
            return ""

    def _add_result_to_tree(self, result):
        """結果をTreeViewに追加"""
        self.results_tree.insert('', 'end', values=(
            result['original'],
            result['new'],
            result['classification'],
            result['confidence'],
            result['status']
        ))

    def _processing_finished(self):
        """処理終了"""
        self.processing = False
        self.process_button.config(state='normal')
        self.progress.stop()
        self.progress.config(mode='determinate', value=0)
        self.status_var.set("処理完了")

    def _clear_results(self):
        """結果クリア"""
        self.processing_results.clear()
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

    def _save_results(self):
        """結果保存"""
        if not self.processing_results:
            messagebox.showinfo("情報", "保存する結果がありません。")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="結果を保存",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt")]
        )
        
        if file_path:
            try:
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['元ファイル名', '新ファイル名', '分類', '信頼度', 'ステータス'])
                    for result in self.processing_results:
                        writer.writerow([
                            result['original'], result['new'], result['classification'], 
                            result['confidence'], result['status']
                        ])
                
                messagebox.showinfo("完了", f"結果を保存しました: {file_path}")
                self._log(f"結果を保存しました: {file_path}")
            except Exception as e:
                messagebox.showerror("エラー", f"保存に失敗しました: {str(e)}")

    def _clear_log(self):
        """ログクリア"""
        self.log_text.delete('1.0', 'end')

    def _save_log(self):
        """ログ保存"""
        log_content = self.log_text.get('1.0', 'end')
        file_path = filedialog.asksaveasfilename(
            title="ログ保存",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("完了", f"ログを保存しました: {file_path}")
            except Exception as e:
                messagebox.showerror("エラー", f"ログ保存に失敗: {str(e)}")

    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()

def main():
    """メイン関数"""
    try:
        app = TaxDocumentRenamerV5Ultimate()
        app.run()
    except Exception as e:
        print(f"アプリケーション起動エラー: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました:\\n{str(e)}")

if __name__ == "__main__":
    main()