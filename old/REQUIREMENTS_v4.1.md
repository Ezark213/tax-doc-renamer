# 税務書類リネームシステム v4.1 緊急修正要件定義書

## 📖 概要
v4.0テスト結果を基にした緊急修正版。PDF分割機能とOCR自治体認識の完全実装に焦点を当てた修正リリース。

---

## 🚨 緊急修正項目

### 1. 国税受信通知一式の完全分割実装

#### 現状の問題
- 4枚+空白5枚のファイルが単一ファイルとして処理されている
- PDF分割機能が全く動作していない

#### 要求仕様
```python
def split_national_tax_bundle(pdf_path: str, output_dir: str, year_month: str) -> List[SplitResult]:
    """
    国税受信通知一式を4つに自動分割
    
    Input: 9ページのPDF（4書類 + 5空白ページ）
    Output: 4つの個別PDFファイル
    
    分割対象:
    - Page 1: 0003_受信通知_法人税_YYMM.pdf
    - Page 2: 0004_納付情報_法人税_YYMM.pdf  
    - Page 3: 3003_受信通知_消費税_YYMM.pdf
    - Page 4: 3004_納付情報_消費税_YYMM.pdf
    - Pages 5-9: 空白ページ（除去）
    """
```

#### 判定アルゴリズム
1. **空白ページ検出**: テキスト量50文字未満を空白とみなす
2. **書類種別判定**: 「法人税」「消費税」「受信通知」「納付情報」キーワード検出
3. **順序保証**: 固定順序での分割（法人税→消費税、受信通知→納付情報）

---

### 2. 自治体OCR認識エンジンの完全再実装

#### 現状の問題
- 自治体認識が全てNoneになっている
- OCR処理が正常に動作していない
- 手動入力とのマッチングが機能していない

#### 要求仕様
```python
class EnhancedOCREngine:
    """強化されたOCR・自治体認識エンジン"""
    
    def extract_municipality_with_coordinates(self, pdf_path: str, page: int = 0) -> MunicipalityResult:
        """
        PDF指定座標からの自治体情報抽出
        
        処理範囲: ページ上部1/3、左右中央2/3
        座標: (page_width * 0.17, 0, page_width * 0.83, page_height * 0.33)
        
        検出パターン:
        - "○○県知事" → 都道府県名抽出
        - "○○市長" → 市町村名抽出  
        - "○○都" → 東京都判定
        
        Returns:
            MunicipalityResult(
                prefecture: str,
                municipality: str,
                confidence: float,
                raw_ocr_text: str,
                detection_region: Tuple[int, int, int, int]
            )
        """
```

#### OCR前処理強化
```python
def preprocess_ocr_image(image: Image) -> Image:
    """OCR精度向上のための画像前処理"""
    # 1. グレースケール変換
    # 2. コントラスト調整
    # 3. ノイズ除去
    # 4. 解像度向上（2倍スケール）
    return enhanced_image
```

#### マッチングアルゴリズム強化
```python
def match_with_input_sets(ocr_result: str, input_sets: List[MunicipalitySet]) -> Optional[int]:
    """
    OCR結果と手動入力セットの高精度マッチング
    
    マッチング方式:
    1. 完全一致優先
    2. 部分一致（県・市町村名部分）
    3. 読み仮名対応
    4. 略称対応（例：横浜→横浜市）
    
    Returns:
        マッチしたセット番号（1001, 1011, 1021...）
    """
```

---

### 3. 地方税受信通知一式の1ページごと分割実装

#### 現状の問題
- 受信通知が納付情報にくっついている
- 1ページごと分割が実行されていない
- 連番ルールが正しく適用されていない

#### 要求仕様
```python
def split_local_tax_bundle_by_page(pdf_path: str, output_dir: str, year_month: str) -> List[SplitResult]:
    """
    地方税受信通知一式を1ページごとに分割
    
    Input: N ページのPDF
    Output: N個の個別PDFファイル
    
    命名規則:
    都道府県受信通知: 1003, 1013, 1023, 1033, 1043, 1053...
    都道府県納付情報: 1004 (最後のページ)
    市町村受信通知: 2003, 2013, 2023, 2033, 2043...  
    市町村納付情報: 2004 (最後のページ)
    """
```

#### ページ分類アルゴリズム
```python
def classify_local_tax_page(page_content: str) -> PageType:
    """
    地方税ページの種別分類
    
    判定ルール:
    1. "納付情報" in content → 納付情報ページ
    2. "都道府県" in content → 都道府県受信通知
    3. "市町村" or "市" in content → 市町村受信通知
    4. その他 → 受信通知（種別未確定）
    
    Returns:
        PageType.PREFECTURE_NOTIFICATION |
        PageType.PREFECTURE_PAYMENT |
        PageType.MUNICIPALITY_NOTIFICATION |
        PageType.MUNICIPALITY_PAYMENT
    """
```

---

## 🔧 技術実装要件

### PDF分割エンジン改善
```python
class AdvancedPDFProcessor:
    """高度PDF分割処理クラス"""
    
    def split_by_page_range(self, pdf_path: str, ranges: List[Tuple[int, int]], output_names: List[str]) -> List[str]:
        """指定ページ範囲での分割"""
        
    def detect_blank_pages(self, pdf_path: str, threshold: int = 50) -> List[int]:
        """空白ページの自動検出"""
        
    def extract_page_content(self, pdf_path: str, page: int) -> str:
        """指定ページのテキスト内容抽出"""
        
    def create_single_page_pdf(self, source_pdf: str, page: int, output_path: str) -> bool:
        """1ページのみのPDF作成"""
```

### OCR処理強化
```python
class CoordinateOCR:
    """座標指定OCR処理クラス"""
    
    def __init__(self):
        self.tesseract_config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'
        self.target_region_ratio = (0.17, 0.0, 0.83, 0.33)  # 中央上部
        
    def extract_from_coordinates(self, pdf_path: str, page: int, region: Tuple[float, float, float, float]) -> OCRResult:
        """座標指定OCR実行"""
        
    def enhance_image_for_ocr(self, image: Image) -> Image:
        """OCR用画像最適化"""
        
    def debug_save_ocr_region(self, image: Image, region: Tuple, output_path: str):
        """デバッグ用：OCR対象領域の保存"""
```

---

## 📊 品質要件 v4.1

### 処理精度目標
- **PDF分割成功率**: 98%以上
- **自治体OCR認識率**: 90%以上（明確な文字）
- **自治体マッチング率**: 95%以上
- **1ページ分割精度**: 100%（機械的分割のため）

### パフォーマンス要件
- **分割処理時間**: 1ファイルあたり5秒以内
- **OCR処理時間**: 1ページあたり3秒以内
- **メモリ使用量**: 1GB以下

### エラーハンドリング
- **分割失敗**: 元ファイルをそのまま保持
- **OCR失敗**: Noneではなく詳細エラー情報を返す
- **マッチング失敗**: 類似度情報を提供

---

## 🧪 テスト要件 v4.1

### 単体テスト
```python
def test_national_tax_split():
    """国税受信通知4分割テスト"""
    result = split_national_tax_bundle("test_national.pdf", "output/", "2508")
    assert len(result) == 4
    assert "0003_受信通知_法人税_2508.pdf" in [r.filename for r in result]

def test_ocr_municipality_extraction():
    """自治体OCRテスト"""
    result = extract_municipality_with_coordinates("test_prefecture.pdf")
    assert result.prefecture is not None
    assert result.confidence > 0.7

def test_local_tax_page_split():
    """地方税1ページごと分割テスト"""
    result = split_local_tax_bundle_by_page("test_local.pdf", "output/", "2508")
    assert all(r.success for r in result)
```

### 統合テスト
- **実ファイルでの分割・分類・リネーム一連処理**
- **自治体セット1~5との正確なマッチング**
- **大量ファイル処理での安定性確認**

---

## 🚀 開発スケジュール v4.1

### Phase 1: 緊急修正（即座実装）
- ✅ PDF分割エンジンの完全再実装
- ✅ OCR・自治体認識の強化
- ✅ 1ページごと分割機能

### Phase 2: 品質保証（1日）
- ✅ 単体テスト・統合テスト実行
- ✅ 実ファイルでの動作確認
- ✅ エラーハンドリング強化

### Phase 3: リリース（即座）
- ✅ v4.1としてexe化
- ✅ 動作確認・配布

---

## 📋 成功基準 v4.1

1. **国税受信通知**: 4ファイルへの正確な分割が100%成功
2. **自治体認識**: 手動入力との正確なマッチングが90%以上成功
3. **地方税受信通知**: 1ページごと分割が100%成功
4. **連番処理**: 正しい連番付与が100%成功
5. **ユーザー体験**: 分割・認識過程の可視化

**最終目標**: PDF分割・自治体認識の完全自動化と高精度化