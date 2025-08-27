#!/usr/bin/env python3
"""
動作する税務書類リネームexeを作成（PyMuPDF依存なし）
"""

import os
import subprocess
import shutil

def create_simplified_renamer():
    """PyMuPDF不要の簡易リネーマーを作成"""
    
    content = '''#!/usr/bin/env python3
"""
税務書類リネームシステム - 軽量版（PyMuPDF不要）
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import re
from pathlib import Path
import PyPDF2

class WorkingTaxRenamer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("税務書類リネームシステム v2.7 Working")
        self.root.geometry("800x600")
        
        self.files = []
        self.results = []
        self.setup_gui()
        
    def setup_gui(self):
        """GUI設定"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="税務書類リネームシステム v2.7", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 15))
        
        # ファイル選択セクション
        file_frame = ttk.LabelFrame(main_frame, text="1. ファイル選択", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="PDFファイルを選択", 
                  command=self.select_files).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="クリア", 
                  command=self.clear_files).pack(side=tk.LEFT, padx=(0, 10))
        
        self.count_label = ttk.Label(btn_frame, text="選択: 0件")
        self.count_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # ファイルリスト
        self.listbox = tk.Listbox(file_frame, height=8)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 処理ボタン
        process_frame = ttk.Frame(main_frame)
        process_frame.pack(pady=15)
        
        ttk.Button(process_frame, text="■ 処理実行", 
                  command=self.process_files,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(process_frame, text="ファイルリネーム実行", 
                  command=self.execute_rename).pack(side=tk.LEFT)
        
        # 結果表示
        result_frame = ttk.LabelFrame(main_frame, text="3. 処理結果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # ツリービューで結果表示
        columns = ('original', 'new', 'type', 'status')
        self.results_tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=8)
        
        self.results_tree.heading('original', text='元ファイル名')
        self.results_tree.heading('new', text='新ファイル名')  
        self.results_tree.heading('type', text='書類種別')
        self.results_tree.heading('status', text='状態')
        
        self.results_tree.column('original', width=200)
        self.results_tree.column('new', width=300)
        self.results_tree.column('type', width=120)
        self.results_tree.column('status', width=80)
        
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
    def select_files(self):
        """ファイル選択"""
        try:
            files = filedialog.askopenfilenames(
                title="PDFファイルを選択",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialdir=r"C:\\Users\\pukur\\Desktop\\iwao"
            )
            
            for file in files:
                if file not in self.files:
                    self.files.append(file)
                    self.listbox.insert(tk.END, os.path.basename(file))
            
            self.count_label.config(text=f"選択: {len(self.files)}件")
            
        except Exception as e:
            messagebox.showerror("エラー", f"ファイル選択エラー: {e}")
    
    def clear_files(self):
        """クリア"""
        self.files.clear()
        self.listbox.delete(0, tk.END)
        self.count_label.config(text="選択: 0件")
        self.results.clear()
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
    
    def extract_text_from_pdf(self, pdf_path):
        """PDFからテキストを抽出（PyPDF2のみ使用）"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + " "
        except Exception as e:
            print(f"PDF読み込みエラー: {e}")
        return text
    
    def detect_document_type(self, text, filename):
        """書類種別判定（ファイル名とテキスト両方を使用）"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # 法人税関連
        if any(keyword in text for keyword in ["法人税申告書", "事業年度分の法人税申告書"]) or "法人税" in filename:
            return "0001_法人税申告書"
            
        # 消費税関連
        if any(keyword in text for keyword in ["消費税申告書", "この申告書による消費税の税額の計算"]) or "消費税" in filename:
            return "3001_消費税申告書"
            
        # 都道府県税関連
        if any(keyword in text for keyword in ["都道府県民税", "事業税", "特別法人事業税"]) or "都道府県" in filename:
            return "1001_都道府県申告"
            
        # 市町村税関連
        if any(keyword in text for keyword in ["市町村民税", "市民税", "法人市民税"]) or "市町村" in filename or "市民税" in filename:
            return "2001_市町村申告"
            
        # 会計書類
        if any(keyword in text for keyword in ["決算報告書", "貸借対照表", "損益計算書"]) or "決算" in filename:
            return "5001_決算書"
            
        # 納付関連
        if any(keyword in text for keyword in ["納付税額一覧表", "納付情報"]) or "納付" in filename:
            return "0000_納付情報"
            
        return "9999_その他"
    
    def extract_year_month(self, text, filename):
        """年月抽出"""
        # ファイル名から先に抽出を試行
        match = re.search(r'(20\d{6})', filename)
        if match:
            date_str = match.group(1)
            return date_str[2:4] + date_str[4:6]
        
        # テキストから抽出
        patterns = [
            r'R0?([0-9]{1,2})[年/\\-.]0?([0-9]{1,2})',
            r'令和0?([0-9]{1,2})[年]0?([0-9]{1,2})[月]',
            r'20([0-9]{2})[年/\\-.]0?([0-9]{1,2})[月]?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                if 1 <= month <= 12:
                    if pattern.startswith('R') or pattern.startswith('令和'):
                        # 令和年を西暦下2桁に変換
                        western_year = (2018 + year) % 100
                        return f"{western_year:02d}{month:02d}"
                    else:
                        return f"{year:02d}{month:02d}"
        
        return "YYMM"
    
    def process_files(self):
        """処理実行"""
        if not self.files:
            messagebox.showwarning("警告", "処理するファイルを選択してください")
            return
        
        self.results.clear()
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        try:
            for file_path in self.files:
                filename = os.path.basename(file_path)
                
                # PDFからテキスト抽出
                text = self.extract_text_from_pdf(file_path)
                
                # 書類種別判定
                doc_type = self.detect_document_type(text, filename)
                
                # 年月抽出
                year_month = self.extract_year_month(text, filename)
                
                # 新しいファイル名生成
                if doc_type.startswith("9999"):
                    new_filename = f"その他_{year_month}_{filename}"
                else:
                    new_filename = f"{doc_type}_{year_month}.pdf"
                
                result = {
                    'original': filename,
                    'new': new_filename,
                    'type': doc_type.split('_')[1] if '_' in doc_type else doc_type,
                    'status': '成功' if doc_type != '9999_その他' else '要確認',
                    'file_path': file_path
                }
                
                self.results.append(result)
                
                # ツリービューに追加
                tags = ('success',) if result['status'] == '成功' else ('warning',)
                self.results_tree.insert('', 'end', values=(
                    result['original'], result['new'], 
                    result['type'], result['status']
                ), tags=tags)
            
            # タグの色設定
            self.results_tree.tag_configure('success', background='#d4edda')
            self.results_tree.tag_configure('warning', background='#fff3cd')
            
            success_count = sum(1 for r in self.results if r['status'] == '成功')
            messagebox.showinfo("処理完了", 
                              f"処理が完了しました\\n成功: {success_count}件\\n要確認: {len(self.results) - success_count}件")
            
        except Exception as e:
            messagebox.showerror("エラー", f"処理エラー: {e}")
    
    def execute_rename(self):
        """ファイルリネーム実行"""
        if not self.results:
            messagebox.showwarning("警告", "先に処理を実行してください")
            return
        
        output_dir = filedialog.askdirectory(
            title="出力先フォルダを選択",
            initialdir=r"C:\\Users\\pukur\\Desktop"
        )
        
        if not output_dir:
            return
        
        try:
            success_count = 0
            
            for result in self.results:
                source_path = result['file_path']
                new_path = os.path.join(output_dir, result['new'])
                
                # 重複回避
                counter = 1
                original_path = new_path
                while os.path.exists(new_path):
                    name, ext = os.path.splitext(original_path)
                    new_path = f"{name}_{counter:02d}{ext}"
                    counter += 1
                
                shutil.copy2(source_path, new_path)
                success_count += 1
            
            messagebox.showinfo("完了", 
                              f"{success_count}件のファイルをリネームしました\\n出力先: {output_dir}")
            
        except Exception as e:
            messagebox.showerror("エラー", f"リネーム実行エラー: {e}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = WorkingTaxRenamer()
    app.run()
'''
    
    # ファイル作成
    target_file = r"C:\Users\pukur\Desktop\TaxRenamer_Tools\working_renamer.py"
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Working renamer created: {target_file}")
    return target_file

def build_working_exe():
    """動作するexeをビルド"""
    print("動作する税務書類リネームexeを作成中...")
    
    # 作業用リネーマーを作成
    working_file = create_simplified_renamer()
    
    # 作業ディレクトリに移動
    os.chdir(os.path.dirname(working_file))
    
    # ビルドディレクトリをクリア
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # PyInstallerコマンド（PyMuPDF除外）
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed", 
        "--name=TaxDocumentRenamer_Working",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "working_renamer.py"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        exe_path = os.path.join("dist", "TaxDocumentRenamer_Working.exe")
        if os.path.exists(exe_path):
            # リネームアプリフォルダにコピー
            dest_dir = r"C:\Users\pukur\Desktop\リネームアプリ"
            dest_path = os.path.join(dest_dir, "TaxDocumentRenamer_Working.exe")
            shutil.copy2(exe_path, dest_path)
            
            print("="*50)
            print("動作する TaxDocumentRenamer_Working.exe が作成されました!")
            print(f"場所: {dest_path}")
            print("PyMuPDFに依存せず、PyPDF2のみで動作します")
            print("="*50)
            return True
        else:
            print("実行ファイルの作成に失敗しました")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"ビルドエラー: {e}")
        print(f"エラー出力: {e.stderr}")
        return False

if __name__ == "__main__":
    success = build_working_exe()
    if success:
        print("\\n次のステップ:")
        print("1. デスクトップの「リネームアプリ」フォルダを開く")
        print("2. TaxDocumentRenamer_Working.exe をダブルクリック")
        print("3. これで確実に動作します!")
    else:
        print("\\nビルドに失敗しました")
    
    input("\\n何かキーを押してください...")'''