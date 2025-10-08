# 📋 新Phase 1 - Task 6: 統合処理フロー設計

**日付**: 2025年10月8日
**設計対象**: 5プロセス全体の処理分岐・統合
**基盤**: 既存`_left_rename_background()`メソッド

---

## 🎯 設計目標

### 必須要件
1. **既存機能の完全保護**
   - `_left_rename_background()`の既存ロジックは一切変更しない
   - 接尾辞置換・全角英字半角変換・元ファイル保持機能を保持

2. **プロセス別処理分岐の実装**
   - プルダウン選択値による5プロセスの分岐
   - 各プロセス固有のロジック実装

3. **ラッパー方式による拡張**
   - 新規プロセスは既存機能をラップして呼び出す
   - 既存機能との競合を回避

---

## 📐 全体アーキテクチャ設計

### 処理フロー概要図

```
[ユーザー: プロセス選択]
    ↓
[ユーザー: リネーム実行]
    ↓
[_left_execute() - main.py:2390]
    ↓
[process_type = self.process_type_var.get()]  # プルダウン値取得
    ↓
    ├─ process_type == "源泉税"
    │   → _process_gensen()
    │       → _left_rename_background() ← 既存処理をそのまま呼び出し
    │
    ├─ process_type == "法定調書"
    │   → _process_hoteichosho()
    │       → _left_rename_background() ← 既存処理をそのまま呼び出し
    │
    ├─ process_type == "申請届出"
    │   → _process_application()
    │       ├─ 届出名ベースマッチング（新規）
    │       └─ _left_rename_background() ← 既存処理呼び出し
    │
    ├─ process_type == "給与支払報告書"
    │   → _process_payroll_report()
    │       ├─ 会社名+市区町村マッチング（新規）
    │       └─ _left_rename_background() ← 既存処理呼び出し
    │
    └─ process_type == "償却資産申告書"
        → _process_depreciable_assets()
            ├─ 会社名+提出先マッチング（新規）
            └─ _left_rename_background() ← 既存処理呼び出し
```

---

## 🔧 実装設計詳細

### Phase 1: _left_execute()への処理分岐追加

**ファイル**: `main.py`
**箇所**: `_left_execute()`メソッド（現在 Line 2390-2428）

#### 修正前（現状）
```python
def _left_execute(self):
    """左側フォルダリネーム実行（完全独立）"""
    yymm_value = self.left_yymm_var.get()

    # Phase 3: プロセスタイプ取得（ログ出力のみ）
    process_type = self.process_type_var.get()
    self._log(f"[Phase 3] 選択されたプロセス: {process_type}")

    # ... 検証処理 ...

    # バックグラウンド処理開始
    thread = threading.Thread(
        target=self._left_rename_background,  # ← すべてのプロセスで同じ
        args=(folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english),
        daemon=True
    )
    thread.start()
```

#### 修正後（新Phase 2-3で実装）
```python
def _left_execute(self):
    """左側フォルダリネーム実行（完全独立）"""
    yymm_value = self.left_yymm_var.get()

    # Phase 3: プロセスタイプ取得
    process_type = self.process_type_var.get()
    self._log(f"[新Phase 2-3] 選択されたプロセス: {process_type}")

    # ... 検証処理 ...

    # 🆕 新Phase 2-3: プロセス別処理分岐
    if process_type == "源泉税":
        target_method = self._process_gensen
    elif process_type == "法定調書":
        target_method = self._process_hoteichosho
    elif process_type == "申請届出":
        target_method = self._process_application
    elif process_type == "給与支払報告書":
        target_method = self._process_payroll_report
    elif process_type == "償却資産申告書":
        target_method = self._process_depreciable_assets
    else:
        # フォールバック: デフォルトで既存処理
        target_method = self._left_rename_background

    # バックグラウンド処理開始
    thread = threading.Thread(
        target=target_method,
        args=(folder_path, yymm_value, main_prefix, receipt_prefix, normalize_english),
        daemon=True
    )
    thread.start()
```

---

### Phase 2: プロセス別メソッド実装

#### 2-1. 源泉税・法定調書（既存処理利用）

```python
def _process_gensen(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english=False):
    """
    源泉税プロセス処理

    処理内容:
    - 既存の_left_rename_background()をそのまま呼び出し
    - 会社名ベースのマッチングで対応可能

    変更禁止:
    - 既存ロジックは一切変更しない
    """
    self._log("[源泉税] 処理開始")

    # 既存処理をそのまま呼び出し
    self._left_rename_background(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)

    self._log("[源泉税] 処理完了")


def _process_hoteichosho(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english=False):
    """
    法定調書プロセス処理

    処理内容:
    - 既存の_left_rename_background()をそのまま呼び出し
    - 会社名ベースのマッチングで対応可能

    変更禁止:
    - 既存ロジックは一切変更しない
    """
    self._log("[法定調書] 処理開始")

    # 既存処理をそのまま呼び出し
    self._left_rename_background(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)

    self._log("[法定調書] 処理完了")
```

**重要ポイント**:
- ✅ 既存の`_left_rename_background()`を**そのまま呼び出す**だけ
- ✅ 既存機能（接尾辞置換・全角英字半角変換・元ファイル保持）を完全保持
- ✅ 変更なし = リスクゼロ

#### 2-2. 申請届出（届出名ベースマッチング）

```python
def _process_application(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english=False):
    """
    申請届出プロセス処理

    処理内容:
    1. 既存処理で本表ファイル→フォルダ作成（基本リネーム）
    2. 受信通知を届出名ベースでマッチング・分割配置（新規）

    ラッパー方式:
    - 既存処理を先に実行
    - 受信通知処理のみ新規ロジック使用
    """
    self._log("[申請届出] 処理開始")

    # 🔧 Step 1: 既存の基本リネーム処理実行
    # （本表ファイル収集・フォルダ作成・ファイルコピー）
    self._left_rename_background_without_receipt(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)

    # 🆕 Step 2: 申請届出専用の受信通知処理
    self._process_application_receipts(folder_path, receipt_prefix)

    self._log("[申請届出] 処理完了")


def _left_rename_background_without_receipt(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english=False):
    """
    既存の_left_rename_background()から受信通知処理を除外したバージョン

    実装方法:
    - 既存コードのステップ1-2のみ実行（受信通知処理をスキップ）
    - またはフラグを追加して受信通知処理を制御
    """
    # 既存ロジックのステップ1-2のみ実行
    # （詳細は既存コード参照: main.py:2474-2568）
    pass


def _process_application_receipts(self, folder_path, receipt_prefix):
    """
    申請届出の受信通知処理（新規実装）

    処理フロー:
    1. 国税受信通知.pdfを検出
    2. ページごとに分割
    3. 各ページから届出名抽出（OCR）
    4. 届出名ベースでフォルダマッチング
    5. マッチしたフォルダに配置
    6. 地方税受信通知.pdfも同様処理
    """
    self._log("[申請届出] 受信通知処理開始")

    # 国税受信通知の検出
    national_receipt_path = os.path.join(folder_path, "国税受信通知.pdf")
    local_receipt_path = os.path.join(folder_path, "地方税受信通知.pdf")

    # フォルダリスト取得
    created_folders = self._get_created_folders(folder_path)

    # 国税受信通知処理
    if os.path.exists(national_receipt_path):
        self._split_and_match_application_receipt(
            national_receipt_path,
            created_folders,
            receipt_prefix,
            "国税"
        )

    # 地方税受信通知処理
    if os.path.exists(local_receipt_path):
        self._split_and_match_application_receipt(
            local_receipt_path,
            created_folders,
            receipt_prefix,
            "地方税"
        )

    self._log("[申請届出] 受信通知処理完了")


def _split_and_match_application_receipt(self, receipt_pdf_path, created_folders, receipt_prefix, receipt_type):
    """
    申請届出受信通知の分割・マッチング

    Args:
        receipt_pdf_path: 受信通知PDFパス
        created_folders: 作成済みフォルダリスト
        receipt_prefix: 受信通知の接頭辞（"02" or "9999"）
        receipt_type: "国税" or "地方税"
    """
    import fitz

    doc = fitz.open(receipt_pdf_path)
    total_pages = len(doc)

    for page_num in range(total_pages):
        # 届出名抽出（OCR）
        application_name = self._extract_application_name_from_receipt(receipt_pdf_path, page_num)

        if not application_name:
            self._log(f"[申請届出] Page {page_num+1}: 届出名抽出失敗")
            continue

        self._log(f"[申請届出] Page {page_num+1}: 届出名={application_name}")

        # フォルダマッチング（届出名ベース）
        matched_folder = self._match_application_folder(application_name, created_folders)

        if matched_folder:
            # ページを分割して配置
            self._save_receipt_page_to_folder(
                receipt_pdf_path,
                page_num,
                matched_folder,
                receipt_prefix,
                receipt_type
            )
            self._log(f"[申請届出] Page {page_num+1}: マッチ成功 → {matched_folder}")
        else:
            self._log(f"[申請届出] Page {page_num+1}: マッチングフォルダ見つからず")

    doc.close()


def _extract_application_name_from_receipt(self, pdf_path, page_num):
    """
    受信通知PDFから届出名を抽出

    Returns:
        str: 正規化された届出名
    """
    import fitz

    doc = fitz.open(pdf_path)
    page = doc[page_num]
    text = page.get_text()
    doc.close()

    # 国税パターン: "種目："
    match = re.search(r'種目[:：]\s*(.+)', text)
    if match:
        raw_name = match.group(1).strip()
        return self._normalize_application_name(raw_name)

    # 地方税パターン: "手続名："
    match = re.search(r'手続名[:：]\s*(.+)', text)
    if match:
        raw_name = match.group(1).strip()
        return self._normalize_application_name(raw_name)

    return None


def _normalize_application_name(self, raw_name):
    """
    届出名の正規化

    正規化ルール:
    1. 空白・改行除去
    2. 全角英数字を半角に変換
    3. 略称化（必要に応じて）
    """
    # 空白・改行除去
    normalized = re.sub(r'\s+', '', raw_name)

    # 全角英数字を半角に変換
    normalized = self._normalize_fullwidth_english(normalized)

    return normalized


def _match_application_folder(self, receipt_app_name, created_folders):
    """
    受信通知の届出名とフォルダ名をマッチング

    Args:
        receipt_app_name: 受信通知から抽出した届出名
        created_folders: 作成済みフォルダリスト
            例: ["2508_法人設立届出_株式会社Ａｍｐｌｉｕｍ", ...]

    Returns:
        str: マッチしたフォルダ名（見つからない場合はNone）
    """
    from difflib import SequenceMatcher

    best_match = None
    best_score = 0

    for folder_info in created_folders:
        folder_name = folder_info['folder_name']

        # フォルダ名から届出名部分を抽出
        # パターン: YYMM_届出名_会社名
        parts = folder_name.split('_')
        if len(parts) >= 3:
            folder_app_name = '_'.join(parts[1:-1])  # 届出名部分
        else:
            continue

        # 類似度計算
        score = SequenceMatcher(None, receipt_app_name, folder_app_name).ratio()

        if score > 0.7 and score > best_score:
            best_match = folder_info
            best_score = score

    return best_match
```

#### 2-3. 給与支払報告書（会社名+市区町村マッチング）

```python
def _process_payroll_report(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english=False):
    """
    給与支払報告書プロセス処理

    処理内容:
    1. 既存処理で本表ファイル→フォルダ作成
    2. 受信通知を会社名+市区町村ベースでマッチング・分割配置（新規）
    """
    self._log("[給与支払報告書] 処理開始")

    # Step 1: 既存の基本リネーム処理
    self._left_rename_background_without_receipt(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)

    # Step 2: 給与支払報告書専用の受信通知処理
    self._process_payroll_receipts(folder_path, receipt_prefix)

    self._log("[給与支払報告書] 処理完了")


def _process_payroll_receipts(self, folder_path, receipt_prefix):
    """
    給与支払報告書の受信通知処理

    処理フロー:
    1. 01_受信通知.pdfを検出
    2. ページごとに分割
    3. 各ページから会社名・市区町村名抽出（OCR）
    4. 会社名+市区町村でフォルダマッチング
    5. マッチしたフォルダに配置
    """
    receipt_pdf_path = os.path.join(folder_path, "01_受信通知.pdf")

    if not os.path.exists(receipt_pdf_path):
        self._log("[給与支払報告書] 受信通知PDFが見つかりません")
        return

    created_folders = self._get_created_folders(folder_path)

    import fitz
    doc = fitz.open(receipt_pdf_path)
    total_pages = len(doc)

    for page_num in range(total_pages):
        # 会社名・市区町村名抽出（OCR）
        company_name, municipality = self._extract_company_and_municipality_from_receipt(receipt_pdf_path, page_num)

        if not company_name:
            continue

        self._log(f"[給与支払報告書] Page {page_num+1}: 会社={company_name}, 市区町村={municipality}")

        # フォルダマッチング（会社名+市区町村ベース）
        matched_folder = self._match_payroll_folder(company_name, municipality, created_folders)

        if matched_folder:
            self._save_receipt_page_to_folder(receipt_pdf_path, page_num, matched_folder, receipt_prefix, "給与支払")
            self._log(f"[給与支払報告書] Page {page_num+1}: マッチ成功")
        else:
            self._log(f"[給与支払報告書] Page {page_num+1}: マッチング失敗")

    doc.close()


def _extract_company_and_municipality_from_receipt(self, pdf_path, page_num):
    """
    受信通知から会社名と市区町村名を抽出

    Returns:
        tuple: (company_name, municipality)
    """
    import fitz

    doc = fitz.open(pdf_path)
    page = doc[page_num]
    text = page.get_text()
    doc.close()

    # 会社名抽出
    company_match = re.search(r'納税者の\s*氏名又は名称[:：]\s*(.+)', text)
    company_name = company_match.group(1).strip() if company_match else None

    # 市区町村名抽出（発行元から）
    municipality_match = re.search(r'発行元[:：]\s*(.+?)[（\(]?', text)
    if municipality_match:
        municipality = self._extract_municipality_name(municipality_match.group(1))
    else:
        # 提出先から抽出
        municipality_match = re.search(r'提出先名[:：]\s*(.+?)[市区町村長]', text)
        municipality = municipality_match.group(1) if municipality_match else None

    return company_name, municipality


def _match_payroll_folder(self, receipt_company, receipt_municipality, created_folders):
    """
    会社名+市区町村でフォルダマッチング
    """
    from difflib import SequenceMatcher

    for folder_info in created_folders:
        folder_name = folder_info['folder_name']

        # フォルダ名から会社名・市区町村抽出
        folder_company = self._extract_company_from_folder_name(folder_name)
        folder_municipality = self._extract_municipality_from_folder_name(folder_name)

        # 会社名の類似度
        company_score = SequenceMatcher(None, receipt_company, folder_company).ratio()

        # 市区町村の一致判定
        municipality_match = receipt_municipality in folder_municipality or folder_municipality in receipt_municipality

        if company_score >= 0.7 and municipality_match:
            return folder_info

    return None
```

#### 2-4. 償却資産申告書（会社名+提出先マッチング）

```python
def _process_depreciable_assets(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english=False):
    """
    償却資産申告書プロセス処理

    処理内容:
    1. 既存処理で本表ファイル→フォルダ作成
    2. 受信通知を会社名+提出先ベースでマッチング・分割配置（新規）
    """
    self._log("[償却資産申告書] 処理開始")

    # Step 1: 既存の基本リネーム処理
    self._left_rename_background_without_receipt(folder_path, yymm, main_prefix, receipt_prefix, normalize_english)

    # Step 2: 償却資産申告書専用の受信通知処理
    self._process_depreciable_receipts(folder_path, receipt_prefix)

    self._log("[償却資産申告書] 処理完了")


def _process_depreciable_receipts(self, folder_path, receipt_prefix):
    """
    償却資産申告書の受信通知処理

    給与支払報告書と類似（市区町村→提出先に置き換え）
    """
    receipt_pdf_path = os.path.join(folder_path, "01_受信通知.pdf")

    if not os.path.exists(receipt_pdf_path):
        self._log("[償却資産申告書] 受信通知PDFが見つかりません")
        return

    created_folders = self._get_created_folders(folder_path)

    import fitz
    doc = fitz.open(receipt_pdf_path)
    total_pages = len(doc)

    for page_num in range(total_pages):
        # 会社名・提出先抽出（OCR）
        company_name, office = self._extract_company_and_office_from_receipt(receipt_pdf_path, page_num)

        if not company_name:
            continue

        self._log(f"[償却資産申告書] Page {page_num+1}: 会社={company_name}, 提出先={office}")

        # フォルダマッチング（会社名+提出先ベース）
        matched_folder = self._match_depreciable_folder(company_name, office, created_folders)

        if matched_folder:
            self._save_receipt_page_to_folder(receipt_pdf_path, page_num, matched_folder, receipt_prefix, "償却資産")
            self._log(f"[償却資産申告書] Page {page_num+1}: マッチ成功")
        else:
            self._log(f"[償却資産申告書] Page {page_num+1}: マッチング失敗")

    doc.close()
```

---

## 🛡️ 既存機能保護の確認

### 保護対象機能リスト

#### 1. 接尾辞置換機能
**既存コード**: `main.py:2502`
```python
new_filename = f"{main_prefix}_{doc_type}.pdf"
```

**保護方法**:
- ✅ `_left_rename_background_without_receipt()`で同じロジック使用
- ✅ パラメータ`main_prefix`をそのまま渡す

#### 2. 全角英字半角変換機能
**既存コード**: `main.py:2503-2505`
```python
if normalize_english:
    rest_name = self._normalize_fullwidth_english(rest_name)
```

**保護方法**:
- ✅ パラメータ`normalize_english`をそのまま渡す
- ✅ 既存の`_normalize_fullwidth_english()`メソッドを使用

#### 3. フォルダ選択リネーム機能
**既存コード**: `main.py:2517-2520`
```python
folder_name = f"{yymm}_{folder_base_name}"
new_folder_path = os.path.join(folder_path, folder_name)
```

**保護方法**:
- ✅ パラメータ`yymm`をそのまま渡す
- ✅ フォルダ名生成ロジックは変更しない

#### 4. 元ファイル保持機能
**既存コード**: `main.py:2527`
```python
shutil.copy2(original_file_path, dest_file_path)
```

**保護方法**:
- ✅ `shutil.copy2`をそのまま使用
- ✅ 元ファイルは削除しない

---

## 📝 実装チェックリスト

### Phase 1: 処理分岐実装
- [ ] `_left_execute()`にプロセス別分岐追加
- [ ] プロセス選択値の検証
- [ ] エラーハンドリング追加

### Phase 2: 源泉税・法定調書
- [ ] `_process_gensen()`実装
- [ ] `_process_hoteichosho()`実装
- [ ] 既存処理呼び出しの動作確認

### Phase 3: 申請届出
- [ ] `_process_application()`実装
- [ ] `_left_rename_background_without_receipt()`実装
- [ ] `_process_application_receipts()`実装
- [ ] `_extract_application_name_from_receipt()`実装
- [ ] `_match_application_folder()`実装

### Phase 4: 給与支払報告書
- [ ] `_process_payroll_report()`実装
- [ ] `_process_payroll_receipts()`実装
- [ ] `_extract_company_and_municipality_from_receipt()`実装
- [ ] `_match_payroll_folder()`実装

### Phase 5: 償却資産申告書
- [ ] `_process_depreciable_assets()`実装
- [ ] `_process_depreciable_receipts()`実装
- [ ] `_extract_company_and_office_from_receipt()`実装
- [ ] `_match_depreciable_folder()`実装

### Phase 6: ヘルパーメソッド実装
- [ ] `_get_created_folders()`実装
- [ ] `_save_receipt_page_to_folder()`実装
- [ ] `_extract_municipality_name()`実装
- [ ] その他ユーティリティメソッド

### Phase 7: テスト
- [ ] 源泉税の動作確認
- [ ] 法定調書の動作確認
- [ ] 申請届出の動作確認
- [ ] 給与支払報告書の動作確認
- [ ] 償却資産申告書の動作確認

---

## ✅ Task 6 完了基準

- [x] 5プロセス全体の処理分岐設計完了
- [x] 既存機能保護方法の明確化
- [x] ラッパー方式の詳細設計完了
- [x] 実装チェックリスト作成完了

---

**設計完了日時**: 2025年10月8日
**次のフェーズ**: 新Phase 2（実装計画）、新Phase 3（実装）
