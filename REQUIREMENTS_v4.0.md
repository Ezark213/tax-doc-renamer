# 税務書類リネームシステム v4.0 要件定義書

## 📖 プロジェクト概要
PDFおよびCSVファイルから税務書類を**完全自動分類・分割・リネーム**し、標準化されたファイル名で整理する高精度システム

---

## 🎯 v4.0 主要改善目標

### 1. 完全自動PDF分割システム
- **国税受信通知一式**: 4種類書類の自動分割
- **地方税受信通知一式**: 7種類書類の自動分割  
- **空白ページ除去**: 自動検出・除去機能
- **分割精度**: 95%以上の分割成功率

### 2. 高精度自治体認識システム
- **OCR強化**: PDF 1ページ目中央上部の重点処理
- **文字列マッチング**: 手動入力との高精度照合
- **連番自動付与**: マッチング結果による自動連番
- **認識精度**: 90%以上の自治体名認識率

### 3. 完全CSV対応システム  
- **フォーマット対応**: 各種CSV形式の自動判定
- **エラーハンドリング**: 読み込みエラーの完全対応
- **内容解析**: CSV内容による書類種別判定

### 4. 直感的UI改善
- **ドラッグ&ドロップ**: ファイル・フォルダ選択対応
- **プログレスバー**: 詳細な進行状況表示
- **リアルタイム表示**: 処理中の状況表示

---

## 🏗️ システムアーキテクチャ v4.0

### コアモジュール構成
```
TaxDocumentRenamer_v4/
├── core/
│   ├── pdf_processor.py      # PDF分割・処理エンジン
│   ├── ocr_engine.py         # OCR処理・自治体認識エンジン  
│   ├── csv_processor.py      # CSV処理エンジン
│   ├── classification.py     # 書類分類エンジン
│   ├── naming_engine.py      # ファイル命名エンジン
│   └── municipality_matcher.py # 自治体マッチングエンジン
├── ui/
│   ├── main_window.py        # メインウィンドウ
│   ├── drag_drop.py          # ドラッグ&ドロップ処理
│   └── progress_display.py   # 進行状況表示
├── config/
│   ├── document_rules.py     # 書類分類ルール
│   ├── municipality_data.py  # 自治体マスタデータ
│   └── naming_rules.py       # 命名規則定義
├── tests/
│   ├── test_pdf_processor.py
│   ├── test_ocr_engine.py
│   └── test_integration.py
└── main.py                   # アプリケーションエントリーポイント
```

---

## 📋 詳細機能仕様

### 1. PDF分割処理エンジン

#### 国税受信通知一式分割
**入力**: 複数書類が含まれる単一PDF（4書類+空白ページ）
```python
def split_national_tax_notifications(pdf_path: str) -> List[SplitResult]:
    """
    国税受信通知一式を4つに自動分割
    
    分割対象:
    - 0003_受信通知_法人税_YYMM.pdf
    - 0004_納付情報_法人税_YYMM.pdf
    - 3003_受信通知_消費税_YYMM.pdf  
    - 3004_納付情報_消費税_YYMM.pdf
    """
    pass
```

#### 地方税受信通知一式分割  
**入力**: 複数書類が含まれる単一PDF（7書類）
```python
def split_local_tax_notifications(pdf_path: str) -> List[SplitResult]:
    """
    地方税受信通知一式を7つに自動分割
    
    分割対象:
    - 1003_受信通知_都道府県_YYMM.pdf（1番目）
    - 1013_受信通知_都道府県_YYMM.pdf（2番目）
    - 1004_納付情報_都道府県_YYMM.pdf
    - 2003_受信通知_市町村_YYMM.pdf（1番目）  
    - 2013_受信通知_市町村_YYMM.pdf（2番目）
    - 2023_受信通知_市町村_YYMM.pdf（3番目）
    - 2004_納付情報_市町村_YYMM.pdf
    """
    pass
```

#### 分割判定アルゴリズム
1. **ページ内容解析**: PyMuPDFによるテキスト抽出
2. **キーワード検出**: 「受信通知」「納付情報」等の識別
3. **書類境界検出**: 空白ページや区切り線の検出
4. **自動分割実行**: 検出された境界でPDF分割

---

### 2. 高精度OCR・自治体認識エンジン

#### OCR処理強化
```python
def extract_municipality_info(pdf_path: str, page_num: int = 0) -> MunicipalityInfo:
    """
    PDF指定ページから自治体情報を抽出
    
    処理範囲: 1ページ目の中央上部（座標指定）
    検出対象: 「○○県知事」「○○市長」「○○都」等
    """
    # 処理領域を中央上部に限定（精度向上）
    crop_area = (x1, y1, x2, y2)  # 中央上部座標
    
    # 高精度OCR処理
    extracted_text = pytesseract.image_to_string(
        cropped_image, 
        lang='jpn',
        config='--psm 6 --oem 3'
    )
    
    return parse_municipality_keywords(extracted_text)
```

#### 自治体マッチング処理
```python
class MunicipalityMatcher:
    """自治体名と手動入力セットのマッチング処理"""
    
    def __init__(self, input_sets: List[MunicipalitySet]):
        self.input_sets = input_sets
        
    def match_prefecture(self, ocr_text: str) -> Optional[int]:
        """都道府県のマッチング"""
        for i, muni_set in enumerate(self.input_sets):
            if self._is_prefecture_match(ocr_text, muni_set.prefecture):
                return 1001 + (i * 10)  # 1001, 1011, 1021...
        return None
        
    def match_municipality(self, ocr_text: str) -> Optional[int]:
        """市町村のマッチング"""  
        for i, muni_set in enumerate(self.input_sets):
            if self._is_municipality_match(ocr_text, muni_set.municipality):
                return 2001 + (i * 10)  # 2001, 2011, 2021...
        return None
```

---

### 3. CSV処理エンジン強化

#### 対応CSVフォーマット
1. **仕訳帳CSV**: `仕訳帳_YYYYMMDD_HHMM.csv`
2. **総勘定元帳CSV**: `総勘定元帳_YYYYMMDD.csv`  
3. **残高試算表CSV**: `残高試算表_YYYYMMDD.csv`

#### CSV処理アルゴリズム
```python
class CSVProcessor:
    """CSV処理の完全対応"""
    
    def process_csv(self, csv_path: str) -> ProcessResult:
        """CSV処理のメイン処理"""
        try:
            # エンコーディング自動判定
            encoding = self.detect_encoding(csv_path)
            
            # pandas読み込み（エラーハンドリング強化）
            df = pd.read_csv(csv_path, encoding=encoding, error_bad_lines=False)
            
            # 内容解析による書類種別判定
            doc_type = self.classify_csv_content(df, csv_path)
            
            # 年月抽出（ファイル名 → 内容 → デフォルト）
            year_month = self.extract_year_month_from_csv(csv_path, df)
            
            return ProcessResult(doc_type=doc_type, year_month=year_month)
            
        except Exception as e:
            return ProcessResult(error=f"CSV処理エラー: {str(e)}")
```

---

### 4. 書類分類エンジン改善

#### 分類精度向上
**問題のあった分類の修正**:

1. **添付資料の正確な判定**:
   ```python
   ATTACHMENT_KEYWORDS = [
       "添付資料", "資料", "参考資料", "別添", 
       "消費税 資料", "法人税 資料", "申告資料"
   ]
   ```

2. **法人税申告書の正確な判定**:
   ```python
   CORPORATE_TAX_KEYWORDS = [
       "法人税申告書", "法人税及び地方法人税申告書",
       "内国法人の確定申告", "申告書第一表", "法人税 申告"
   ]
   ```

3. **税区分集計表の正確な分離**:
   ```python
   TAX_CLASSIFICATION_RULES = {
       "7001": ["勘定科目別税区分集計表", "勘定科目別", "科目別"],
       "7002": ["税区分集計表", "税区分", "区分集計"]  # 勘定科目別を含まない
   }
   ```

#### 分類優先度アルゴリズム
```python
def classify_document(text: str, filename: str) -> DocumentType:
    """書類分類の優先度付き判定"""
    
    # 1. 特定キーワードによる直接判定（最高優先度）
    for doc_type, keywords in SPECIFIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return doc_type
            
    # 2. ファイル名による補完判定（中優先度）  
    filename_type = classify_by_filename(filename)
    if filename_type:
        return filename_type
        
    # 3. 内容パターンによる推定（低優先度）
    return classify_by_content_pattern(text)
```

---

### 5. UI改善仕様

#### ドラッグ&ドロップ機能
```python
class DragDropHandler:
    """ドラッグ&ドロップ処理"""
    
    def __init__(self, target_widget):
        target_widget.drop_target_register(DND_FILES)
        target_widget.dnd_bind('<<Drop>>', self.on_drop)
        
    def on_drop(self, event):
        """ドロップイベント処理"""
        files = event.data.split()
        
        # PDF・CSVファイルのフィルタリング  
        valid_files = self.filter_supported_files(files)
        
        # ファイルリストに追加
        self.add_files_to_list(valid_files)
```

#### 進行状況表示強化
```python
class ProgressDisplay:
    """詳細な進行状況表示"""
    
    def update_progress(self, current: int, total: int, current_file: str, stage: str):
        """進行状況の更新"""
        progress = (current / total) * 100
        
        # プログレスバー更新
        self.progress_bar.set(progress)
        
        # 詳細情報表示
        self.status_label.set(f"処理中: {current_file} ({stage})")
        self.file_count_label.set(f"{current}/{total} ファイル")
```

---

## 🧪 テスト要件 v4.0

### 1. 単体テスト（ユニットテスト）
```python
class TestPDFSplitter(unittest.TestCase):
    """PDF分割機能のテスト"""
    
    def test_national_tax_split(self):
        """国税受信通知一式の分割テスト"""
        result = split_national_tax_notifications("test_national.pdf")
        self.assertEqual(len(result), 4)
        self.assertIn("0003_受信通知_法人税", result[0].filename)
        
    def test_local_tax_split(self):
        """地方税受信通知一式の分割テスト"""
        result = split_local_tax_notifications("test_local.pdf")
        self.assertEqual(len(result), 7)
```

### 2. 統合テスト（結合テスト）
- **実ファイルでの分割・分類・リネーム一連処理**
- **OCR→マッチング→連番付与の全工程テスト**
- **CSV処理→分類→リネームの全工程テスト**

### 3. 回帰テスト（既存機能保証）
- **v2.9で成功していた機能の動作保証**
- **基本的な書類分類の動作確認**

---

## 📊 品質要件 v4.0

### 処理精度目標
- **PDF分割精度**: 95%以上
- **自治体認識精度**: 90%以上  
- **書類分類精度**: 98%以上
- **CSV処理成功率**: 95%以上

### パフォーマンス目標
- **処理速度**: 30ファイル/分以上
- **メモリ使用量**: 500MB以下
- **起動時間**: 3秒以内

### 運用要件
- **Windows 10/11 対応**
- **Tesseract日本語パッケージ必須**
- **スタンドアローン動作（ネット接続不要）**
- **詳細ログ出力（デバッグ情報含む）**

---

## 🚀 開発フェーズ v4.0

### Phase 1: コア機能実装（2週間）
- ✅ プロジェクト構造設計・セットアップ
- ✅ PDF分割エンジン実装（国税・地方税）
- ✅ OCR・自治体認識エンジン実装  
- ✅ 基本的な単体テスト実装

### Phase 2: 分類・処理機能実装（1週間）
- ✅ 書類分類エンジン改善実装
- ✅ CSV処理エンジン実装
- ✅ ファイル命名エンジン実装

### Phase 3: UI・統合実装（1週間）  
- ✅ ドラッグ&ドロップUI実装
- ✅ 進行状況表示改善
- ✅ 統合テスト・デバッグ

### Phase 4: 最終テスト・配布（3日）
- ✅ 回帰テスト・品質保証
- ✅ 実行ファイル作成・配布準備

---

## 📚 関連ドキュメント v4.0

### 設計ドキュメント
- [ARCHITECTURE_v4.0.md](./ARCHITECTURE_v4.0.md) - システム設計書
- [API_SPECIFICATION_v4.0.md](./API_SPECIFICATION_v4.0.md) - API仕様書

### テスト関連  
- [TEST_PLAN_v4.0.md](./TEST_PLAN_v4.0.md) - テスト計画書
- [TEST_CASES_v4.0.md](./TEST_CASES_v4.0.md) - テストケース一覧

### 過去バージョン
- [ISSUES_v3.0_TestResults.md](./ISSUES_v3.0_TestResults.md) - v3.0テスト結果
- [REQUIREMENTS_v3.0.md](./REQUIREMENTS_v3.0.md) - v3.0要件定義
- [README.md](./README.md) - プロジェクト基本情報

---

## ✅ 成功基準 v4.0

1. **機能完全性**: 全7項目の修正点が完全に解決されている
2. **処理精度**: 設定された精度目標をすべて達成している  
3. **ユーザビリティ**: ドラッグ&ドロップによる直感的操作が可能
4. **安定性**: 長時間使用・大量ファイル処理でも安定動作
5. **拡張性**: 将来的な機能追加に対応できる設計

**最終目標**: 完全自動化された高精度税務書類処理システムの実現