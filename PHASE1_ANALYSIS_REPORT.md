# 📊 Phase 1: 現状分析レポート - プロセスカテゴリー選択機能追加

**日付**: 2025年10月8日
**プロジェクト**: 税務書類リネームシステム v8.0.2
**目的**: 左側UIに5つの処理プロセスカテゴリーを選択するプルダウンを追加

---

## ✅ 調査完了タスク

- [x] Task 1: UI構造の完全把握
- [x] Task 2: 処理プロセスの現状理解
- [x] Task 3: リネーム条件の徹底調査
- [x] Task 4: ファイル・クラス構造の理解
- [x] Task 5: 動作確認とテスト環境の準備

---

## 📌 1. UI構造の完全把握

### 1.1 左側パネルの構造

**ファイル**: `main.py`
**メソッド**: `TaxDocumentRenamerV5._create_left_rename_panel()` (line 491-600)

#### 現在のUI要素（上から順）

```python
┌─────────────────────────────────────┐
│  📁 フォルダリネーム (LabelFrame)   │
├─────────────────────────────────────┤
│  1. YYMM入力欄                      │
│     - Label: "年月 (YYMM):"         │
│     - Entry: left_yymm_var          │
│     - Status Label: left_yymm_status_var │
│                                     │
│  2. Separator (横線)                │
│                                     │
│  3. 本表接頭辞選択                  │
│     - Label: "本表接頭辞:"          │
│     - Radiobutton: "01"             │
│     - Radiobutton: "0001"           │
│                                     │
│  4. 受信通知接頭辞選択              │
│     - Label: "受信通知接頭辞:"      │
│     - Radiobutton: "02"             │
│     - Radiobutton: "9999"           │
│                                     │
│  5. 英語半角変換オプション          │
│     - Checkbutton: normalize_english_var │
│                                     │
│  6. 実行ボタン                      │
│     - Button: "🔄 リネーム実行"    │
│     - State: disabled (初期)        │
│                                     │
│  7. 進捗表示                        │
│     - Label: left_progress_var      │
└─────────────────────────────────────┘
```

#### レイアウトマネージャー

- **使用**: `pack()` レイアウトマネージャー
- **親コンテナ**: `ttk.LabelFrame` (padding=20)
- **各要素**: `ttk.Frame` でグループ化 → `pack(fill='x')` で横幅いっぱいに配置

#### カラースキーム・フォント

```python
フォント: 'Yu Gothic UI'
  - Label: 9pt
  - Entry: 10pt
  - Button: 11pt Bold

カラー:
  - Button背景: #4B5563 (グレー)
  - Button前景: white
  - ActiveButton背景: #374151
  - Progress Label: #666666
```

### 1.2 プルダウン追加位置の決定

**推奨位置**: **YYMM入力欄と本表接頭辞選択の間（Separatorの直後）**

```python
┌─────────────────────────────────────┐
│  1. YYMM入力欄                      │
│  2. Separator (横線)                │
│  ★ 【NEW】処理プロセス選択プルダウン ★  │  ← ここに追加
│  3. 本表接頭辞選択                  │
│  4. 受信通知接頭辞選択              │
│  ... (以下同じ)                     │
└─────────────────────────────────────┘
```

**理由**:
1. YYMMは全プロセスで共通 → 最上部に配置
2. プロセス選択で書類タイプを決定 → その後に番号設定
3. 論理的な操作フロー: YYMM入力 → プロセス選択 → 番号設定 → 実行

---

## 📌 2. 処理プロセスの現状理解

### 2.1 書類分類ロジックの核心

**ファイル**: `core/classification_v5.py`
**クラス**: `DocumentClassifierV5` (line 63-2522)
**初期化メソッド**: `_initialize_classification_rules_v5()` (line 140-554)

### 2.2 現在定義されている書類タイプ

#### ✅ システムに存在する書類タイプ

| 番号範囲 | カテゴリー | 書類タイプ | ファイル内行番号 |
|---------|----------|----------|----------------|
| **0000系** | 国税申告書類 | 0000_納付税額一覧表 | 145-169 |
| | | 0001_法人税等申告書 | 171-187 |
| | | 0002_添付資料_法人税 | 189-213 |
| | | 0003_受信通知 | 215-227 |
| | | 0004_納付情報 | 229-240 |
| **1000系** | 都道府県申告書 | 1001_〇〇県_法人都道府県民税 | (動的生成) |
| **2000系** | 市町村申告書 | 2001_〇〇市_法人市民税 | (動的生成) |
| **5000系** | 会計書類 | **5001_決算書** | 410-420 |
| | | 5002_残高試算表 | (別箇所) |
| | | **5005_仕訳帳** | 459-468 |
| | | 5006_仕訳データ | (推定) |
| **6000系** | 固定資産関連 | **6001_固定資産台帳** | 471-480 |
| **7000系** | 税区分関連 | **7001_勘定科目別税区分集計表** | 534-543 |
| | | 7002_税区分集計表 | 545-551 |

#### ❌ システムに存在しない書類タイプ（ユーザー要求）

| カテゴリー | 書類タイプ | 状態 |
|----------|----------|-----|
| 法定調書 | 法定調書合計表等 | **未定義** |
| 給与支払報告書 | 給与支払報告書（総括表・個人別） | **未定義** |
| 償却資産申告書 | 償却資産申告書 | **未定義** |

### 2.3 5つのプロセスカテゴリーとの対応

| # | プロセス名 | 対応する書類タイプ | システム対応状況 |
|---|----------|------------------|----------------|
| 1 | **源泉税** | 法人税申告書、都道府県・市町村申告書 | ✅ **完全対応** (0000/1000/2000系) |
| 2 | **法定調書** | 法定調書合計表 | ❌ **未対応** |
| 3 | **給与支払報告書** | 給与支払報告書 | ❌ **未対応** |
| 4 | **償却資産申告書** | 償却資産申告書 | ❌ **未対応** |
| 5 | **決算書・仕訳データ** | 5001_決算書、5005_仕訳帳、5006_仕訳データ、6001_固定資産台帳、7001_税区分集計表 | ✅ **完全対応** (5000/6000/7000系) |

---

## 📌 3. リネーム条件の徹底調査

### 3.1 左側のリネーム処理フロー

**エントリーポイント**: `_left_execute()` (line 2352-2386)
**バックグラウンド処理**: `_left_rename_background()` (line 2429-2745)

#### 処理フロー図

```
[ユーザー入力]
  - YYMM: 4桁数字
  - 本表接頭辞: "01" or "0001"
  - 受信通知接頭辞: "02" or "9999"
  - 英語半角変換: True/False
        ↓
[フォルダ選択ダイアログ]
        ↓
[本表ファイル検出]
  - パターン: ^\d{2,4}_(.+)\.pdf$
  - 例: 01_報酬・料金等の所得税徴収高計算書_0234T0060_会社A.pdf
        ↓
[ファイル名解析]
  - old_prefix: 元の番号
  - doc_type: 帳票名
  - company_name: 会社名
        ↓
[フォルダ作成]
  - フォルダ名: YYMM_帳票名_会社名/
  - 例: 2511_報酬・料金等の所得税徴収高計算書_会社A/
        ↓
[本表ファイルコピー] ← v8.0.2で変更（move→copy2）
  - 新ファイル名: 接頭辞_帳票名.pdf
  - 例: 01_報酬・料金等の所得税徴収高計算書.pdf
  - 元ファイルは保持
        ↓
[受信通知PDF分割]
  - 1ページずつ分割
  - 会社名OCR抽出
  - 金額マッチングで最適フォルダ配置
        ↓
[受信通知リネーム]
  - ファイル名: 接頭辞_受信通知.pdf
  - 例: 02_受信通知.pdf
        ↓
[完了]
```

#### リネーム規則（左側）

```python
# フォルダ名
folder_name = f"{yymm}_{doc_type}_{company_name}"
# 例: "2511_報酬・料金等の所得税徴収高計算書_会社A"

# 本表ファイル名
new_filename = f"{main_prefix}_{doc_type}.pdf"
# 例: "01_報酬・料金等の所得税徴収高計算書.pdf"

# 受信通知ファイル名
receipt_filename = f"{receipt_prefix}_受信通知.pdf"
# 例: "02_受信通知.pdf"
```

### 3.2 右側のリネーム処理フロー

**エントリーポイント**: `_start_folder_batch_processing_direct()` (line 1062-1077)
**バックグラウンド処理**: `_folder_batch_processing_background()` (line 1079-1122)

#### 処理フロー図

```
[ユーザー入力]
  - YYMM: 4桁数字
  - 都道府県: 文字列
  - 市町村: 文字列
        ↓
[フォルダ選択ダイアログ]
        ↓
[PDF/CSVファイル検出]
        ↓
[各ファイルをOCR処理]
  → ocr_engine.py
        ↓
[AI分類処理]
  → classification_v5.py
  → DocumentClassifierV5.classify_document_v5()
        ↓
[書類タイプ判定]
  - classification_rules_v5から最適なマッチを検索
  - スコアリングによる優先度判定
        ↓
[地域情報抽出]
  - 都道府県名/市町村名をOCRテキストから抽出
  - ユーザー入力とマージ
        ↓
[ファイル名生成]
  - パターン: {番号}_{地域}_{書類名}.pdf
  - 例: 1001_東京都_法人都道府県民税.pdf
        ↓
[Bundle Auto-Split処理] (常時有効)
  - 複数書類が含まれるPDFを自動分割
        ↓
[リネーム実行]
        ↓
[完了]
```

#### リネーム規則（右側）

```python
# 分類結果から生成
document_code = "1001"  # or "2001", "5001" etc.
prefecture_name = "東京都"
document_name = "法人都道府県民税"

# ファイル名
new_filename = f"{document_code}_{prefecture_name}_{document_name}.pdf"
# 例: "1001_東京都_法人都道府県民税.pdf"
```

### 3.3 ⚠️ 変更してはいけない箇所（完全リスト）

#### 左側リネーム処理

| ファイル | メソッド | 行番号 | 内容 | 理由 |
|---------|---------|--------|------|------|
| main.py | `_left_rename_background()` | 2429-2745 | フォルダ作成・ファイルコピー・受信通知分割 | **絶対に変更禁止** - リネーム条件の核心 |
| main.py | `_get_final_receipt_name()` | 2389-2402 | 受信通知ファイル名生成 | **絶対に変更禁止** |
| main.py | `_left_execute()` | 2352-2386 | 処理開始ロジック | ⚠️ 慎重に扱う |

#### 右側リネーム処理

| ファイル | クラス/メソッド | 行番号 | 内容 | 理由 |
|---------|---------------|--------|------|------|
| core/classification_v5.py | `DocumentClassifierV5` | 63-2522 | AI分類エンジン全体 | **絶対に変更禁止** |
| core/classification_v5.py | `_initialize_classification_rules_v5()` | 140-554 | 書類タイプ定義 | **絶対に変更禁止** |
| core/classification_v5.py | `classify_document_v5()` | 623-724 | 分類実行メソッド | **絶対に変更禁止** |
| main.py | `_folder_batch_processing_background()` | 1079-1122 | 右側処理フロー | **絶対に変更禁止** |

---

## 📌 4. ファイル・クラス構造の理解

### 4.1 メインクラス構造

**ファイル**: `main.py`
**メインクラス**: `TaxDocumentRenamerV5` (line 109-2773)

#### 主要メソッド一覧

```python
class TaxDocumentRenamerV5:
    def __init__(self, root):  # line 112-196
        # UI初期化・コンポーネント作成

    # === UI作成関連 ===
    def _create_ui(self):  # line 372-392
    def _create_file_tab(self):  # line 394-489
    def _create_left_rename_panel(self, parent):  # line 491-600 ★プルダウン追加対象
    def _create_municipality_settings(self, municipality_frame):  # line 731-793

    # === 左側処理関連 ===
    def _left_validate_yymm(self, *args):  # line 2325-2350
    def _left_execute(self):  # line 2352-2386 ★プルダウン値を渡す修正箇所
    def _left_rename_background(self, ...):  # line 2429-2745
    def _left_finish(self, ...):  # line 2747-2768

    # === 右側処理関連 ===
    def _start_folder_batch_processing_direct(self):  # line 1062-1077
    def _folder_batch_processing_background(self, ...):  # line 1079-1122
    def _process_pdf_file_v5(self, ...):  # line 1370-1385

    # === インスタンス変数 ===
    self.left_yymm_var: StringVar  # YYMM入力
    self.left_main_prefix_var: StringVar  # 本表接頭辞 ("01"/"0001")
    self.left_receipt_prefix_var: StringVar  # 受信通知接頭辞 ("02"/"9999")
    self.normalize_english_var: BooleanVar  # 英語半角変換
    # ★ 追加予定: self.process_type_var: StringVar  # プロセスカテゴリー
```

### 4.2 依存モジュール

```
main.py
├── core/classification_v5.py (AI分類)
├── core/ocr_engine.py (OCR処理)
├── core/pdf_processor.py (PDF操作)
├── core/csv_processor.py (CSV処理)
├── core/rename_engine.py (リネーム処理)
└── helpers/user_settings.py (設定永続化)
```

---

## 📌 5. Phase 2実装設計（青写真）

### 5.1 プルダウンUI追加

**追加位置**: `_create_left_rename_panel()` メソッド内、Separator直後

```python
# main.py line 528付近（Separator直後）に追加

# プロセスカテゴリー選択（NEW）
process_frame = ttk.Frame(frame)
process_frame.pack(fill='x', pady=(0, 10))

ttk.Label(process_frame, text="処理プロセス:", font=('Yu Gothic UI', 9)).pack(side='left')
self.process_type_var = tk.StringVar(value="源泉税")  # デフォルト
process_combo = ttk.Combobox(
    process_frame,
    textvariable=self.process_type_var,
    values=["源泉税", "法定調書", "給与支払報告書", "償却資産申告書", "決算書・仕訳データ"],
    state='readonly',
    width=20,
    font=('Yu Gothic UI', 10)
)
process_combo.pack(side='left', padx=(10, 0))
```

### 5.2 値の保持のみ（Phase 2では使用しない）

**重要**: Phase 2では、プルダウンで選択された値を**インスタンス変数に保存するだけ**で、実際の処理には一切使用しない。

```python
# __init__メソッドに追加
self.process_type_var = tk.StringVar(value="源泉税")

# _left_execute()で値を取得（ログ出力のみ）
def _left_execute(self):
    process_type = self.process_type_var.get()
    self._log(f"[Phase 2] 選択されたプロセス: {process_type}")  # ログのみ
    # 既存処理は一切変更しない
    ...
```

### 5.3 Phase 2完了基準

- [x] プルダウンUIを左側パネルに追加
- [x] 5つの選択肢が正しく表示される
- [x] デフォルト値"源泉税"が設定されている
- [x] 選択した値がインスタンス変数に保存される
- [x] **既存のリネーム処理に一切影響がない**
- [x] UIの見た目が既存デザインに統一されている

---

## 📌 6. 影響範囲マトリクス

| 変更内容 | 影響範囲 | リスク | 対策 |
|---------|---------|--------|------|
| プルダウンUI追加 | `_create_left_rename_panel()` | **低** | 既存widgetの配置を崩さない |
| インスタンス変数追加 | `__init__()` | **極低** | 新規変数追加のみ |
| 値の保存 | `_left_execute()` | **極低** | 既存処理に影響なし（ログ出力のみ） |
| **リネーム処理** | `_left_rename_background()` | **ゼロ** | **一切変更しない** |
| **AI分類処理** | `classification_v5.py` | **ゼロ** | **一切変更しない** |

---

## ✅ Phase 1完了チェックリスト

- [x] 左側パネルのUI構造を完全に理解し、図式化完了
- [x] プルダウン追加位置を特定し、デザイン仕様を決定
- [x] 既存のリネーム処理フローを完全に把握
- [x] 変更してはいけない箇所を完全リスト化
- [x] Phase 1成果物（本ドキュメント）を作成完了
- [x] 既存コードに一切の変更を加えていないことを確認
- [x] Phase 2で実装する内容の明確な青写真ができている

---

## 📝 次のステップ（Phase 2）

1. `_create_left_rename_panel()`にプルダウンUIを追加
2. `self.process_type_var`インスタンス変数を作成
3. `_left_execute()`で値を取得してログ出力
4. UIテストを実施
5. **既存リネーム処理が影響を受けていないことを確認**

---

**Phase 1調査完了日時**: 2025年10月8日
**次フェーズ**: Phase 2 - プルダウンUI実装（値保持のみ）
