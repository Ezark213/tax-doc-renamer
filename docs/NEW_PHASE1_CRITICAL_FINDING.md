# 🚨 新Phase 1 - 重大な発見: 処理分岐は未実装

**日付**: 2025年10月8日
**分析対象**: 税務書類リネームシステム v8.0.3

---

## ✅ 確定した事実

### 1. プルダウンUIの現状（Phase 3で実装済み）

**実装されているもの**:
- ✅ プルダウンUI（5つの選択肢）
  - 源泉税
  - 申請届出
  - 法定調書
  - 給与支払報告書
  - 償却資産申告書
- ✅ プルダウン値の取得（`self.process_type_var.get()`）
- ✅ ログ出力（選択されたプロセスを表示）

**実装されていないもの**:
- ❌ プルダウン値による処理分岐
- ❌ プロセスごとの異なる処理ロジック
- ❌ 「源泉税」「法定調書」「申請届出」等による処理の違い

### 2. 現在の処理の実態

**すべてのプロセスで同じ処理が実行される**:

```python
def _left_execute(self):
    # プルダウン値を取得
    process_type = self.process_type_var.get()
    self._log(f"[Phase 3] 選択されたプロセス: {process_type}")

    # ⚠️ ここで処理分岐していない！
    # すべてのプロセスで同じ _left_rename_background() が実行される
    thread = threading.Thread(
        target=self._left_rename_background,
        args=(folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english),
        daemon=True
    )
    thread.start()
```

**結論**:
- 「源泉税」を選択しても
- 「法定調書」を選択しても
- 「申請届出」を選択しても
- 「給与支払報告書」を選択しても
- 「償却資産申告書」を選択しても

**全く同じ処理**(`_left_rename_background()`)が実行される。

---

## 📊 現在の処理内容の分析

### `_left_rename_background()`が行っていること

**ステップ1**: 本表ファイルの収集
- パターン: `^\d{2,4}_.+\.pdf$`
- すべてのプロセスで同じパターンを使用

**ステップ2**: フォルダ作成+ファイルコピー
- フォルダ名: `YYMM_帳票名_会社名`
- ファイル名: `接頭辞_帳票名.pdf`
- すべてのプロセスで同じロジック

**ステップ3**: 受信通知の分割・配置
- 会社名ベースのマッチング
- すべてのプロセスで同じロジック

**重要**: この処理は**汎用的**で、特定のプロセス（源泉税、法定調書等）に特化していない。

---

## 🔍 「源泉税」「法定調書」は存在しない

### classification_v5.py の分析結果

定義されている書類タイプ:
- **0000番台**: 法人税関連（法人税申告書、受信通知、納付情報等）
- **1000番台**: 都道府県税関連
- **2000番台**: 市町村税関連
- **3000番台**: 消費税関連
- **5000番台**: 決算書関連
- **6000番台**: 固定資産台帳関連
- **7000番台**: 税区分集計表関連

**存在しないもの**:
- ❌ 「源泉税」の分類定義
- ❌ 「法定調書」の分類定義
- ❌ 「申請届出」の分類定義
- ❌ 「給与支払報告書」の分類定義
- ❌ 「償却資産申告書」の分類定義

**結論**:
- `classification_v5.py`は**右側の申告書リネーム機能**で使用されている
- **左側の処理**（`_left_rename_background()`）では使用されていない
- 左側と右側は**完全に独立した処理**

---

## 🎯 新Phase 1での理解の修正

### 誤った理解（修正前）

❌ 「源泉税」と「法定調書」の**既存処理**を保護する必要がある
❌ それらの処理ロジックを特定して変更禁止にする

### 正しい理解（修正後）

✅ 現在、プルダウンは**見た目だけ**で処理に影響していない
✅ **すべてのプロセスで同じ処理**が実行されている
✅ 新Phase 2-3で実装するのは：
  - **プロセス別の処理分岐ロジック**を新規追加
  - 各プロセスに応じた**異なる処理**を実装

---

## 📋 新Phase 2-3で実装すべき内容

### 実装必須: プロセス別処理分岐

```python
def _left_execute(self):
    process_type = self.process_type_var.get()
    self._log(f"[Phase 3] 選択されたプロセス: {process_type}")

    # 🆕 新Phase 2-3で実装必要
    if process_type == "源泉税":
        # 源泉税の処理
        self._process_gensen(folder_path, yymm_value, ...)
    elif process_type == "法定調書":
        # 法定調書の処理
        self._process_hoteichosho(folder_path, yymm_value, ...)
    elif process_type == "申請届出":
        # 申請届出の処理（受信通知分割・マッチング）
        self._process_application(folder_path, yymm_value, ...)
    elif process_type == "給与支払報告書":
        # 給与支払報告書の処理（受信通知分割・マッチング）
        self._process_payroll_report(folder_path, yymm_value, ...)
    elif process_type == "償却資産申告書":
        # 償却資産申告書の処理（受信通知分割・マッチング）
        self._process_depreciable_assets(folder_path, yymm_value, ...)
```

### 各プロセスの実装方針

#### 「源泉税」「法定調書」

**現在の`_left_rename_background()`をそのまま使用**:
- 既に汎用的な実装がある
- 会社名ベースのマッチングで対応可能

**実装方針**:
```python
def _process_gensen(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english):
    # 既存の _left_rename_background() をそのまま呼び出す
    self._left_rename_background(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)
```

**変更禁止**:
- ✅ `_left_rename_background()`の既存ロジックは変更しない
- ✅ 既存の基本リネーム機能（接尾辞置換等）は保持

#### 「申請届出」「給与支払報告書」「償却資産申告書」

**新規実装が必要**:
1. 受信通知の分割ロジック（届出の種類別・会社別）
2. マッチングロジック（届出名称・会社名）
3. リネーム処理（プロセス別のルール）

**実装方針**: ラッパー方式
```python
def _process_application(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english):
    # 1. 受信通知の分割・マッチング（新規）
    matched_files = self._split_and_match_application_receipts(...)

    # 2. 既存の基本リネーム機能を呼び出し（保持）
    self._left_rename_background(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)
```

---

## ✅ Task 1 完了: 既存システム影響範囲の完全把握

### 確定した事実

1. **プルダウンUIは実装済み**だが、**処理分岐は未実装**
2. **すべてのプロセスで同じ処理**が実行される現状
3. **「源泉税」「法定調書」の専用処理は存在しない**
4. **既存の`_left_rename_background()`は汎用的**で、すべてのプロセスに適用可能
5. **左側と右側は完全に独立**（`classification_v5.py`は右側専用）

### 保護すべき既存機能

**`_left_rename_background()`内の既存機能**:
- ✅ 接尾辞置換機能（`main_prefix`指定）
- ✅ 全角英字半角変換機能（`normalize_english`オプション）
- ✅ フォルダ選択リネーム機能（フォルダ名生成ロジック）
- ✅ 元ファイル保持機能（`shutil.copy2`使用）
- ✅ 会社名ベースの受信通知マッチング

**変更禁止の方針**:
- ❌ `_left_rename_background()`メソッドの既存ロジックは変更しない
- ✅ 新規プロセスは**追加実装**のみ
- ✅ ラッパー方式で既存機能を呼び出す

### 右側パネルの影響

**調査結果**:
- ✅ 右側パネルは`classification_v5.py`を使用
- ✅ 左側とは**完全に独立**した処理
- ✅ **左側の変更が右側に影響しない**ことを確認

**変更禁止**:
- ❌ 右側パネルの処理には一切手を加えない
- ❌ `classification_v5.py`は変更しない

---

## 🔜 次のステップ: 新Phase 1 残りのタスク

### Task 2-6: サンプルファイルの分析

ユーザー提供のサンプルファイルを分析：
1. ①申請届出サンプル（株式会社Ａｍｐｌｉｕｍ）
2. ②給与支払報告書サンプル（7社）
3. ③償却資産申告書サンプル（7社）

各サンプルのOCR分析を行い、新規3プロセスの実装に必要な情報を抽出。

---

**分析完了日時**: 2025年10月8日
**重要度**: 🚨 **最重要** - プロジェクト全体の方針に影響
