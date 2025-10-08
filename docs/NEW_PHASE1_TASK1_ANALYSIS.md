# 📋 新Phase 1 - Task 1: 既存システム影響範囲分析レポート

**日付**: 2025年10月8日
**分析対象**: 税務書類リネームシステム v8.0.3
**目的**: プロセス別処理ロジック実装前の既存システム完全把握

---

## 🎯 Task 1-1: プルダウン選択値の処理分岐箇所特定 ✅ 完了

### 発見事項

#### 1. プルダウン値の取得箇所
**ファイル**: `main.py`
**行番号**: 2395
**実装コード**:
```python
# Phase 3: プロセスタイプ取得（ログ出力のみ）
process_type = self.process_type_var.get()
self._log(f"[Phase 3] 選択されたプロセス: {process_type}")
```

**重要な発見**:
- ✅ プルダウン値は正常に取得されている
- ⚠️ **現在はログ出力のみで、処理分岐には使用されていない**
- ✅ Phase 3の実装計画通り（UI表示のみ、処理ロジック未実装）

#### 2. 処理分岐の現状

**現状**: **処理分岐は存在しない**

`process_type`変数の使用箇所を調査した結果:
- Line 182: インスタンス変数宣言
- Line 534: UI初期化（デフォルト値："源泉税"）
- Line 537: UIバインディング
- Line 2395: 値取得
- Line 2396: ログ出力

**結論**:
- ❌ `if process_type == "源泉税":` のような分岐は**存在しない**
- ❌ `process_type`による処理の切り替えは**未実装**
- ✅ これは**新Phase 2-3で実装する必要がある**

#### 3. 実際の処理実行箇所

**エントリーポイント**:
- **関数**: `_left_execute()`
- **ファイル**: `main.py`
- **行番号**: 2390-2428

**実際の処理実行メソッド**:
- **関数**: `_left_rename_background()`
- **ファイル**: `main.py`
- **行番号**: 2463-2780（約318行）
- **呼び出し**: Line 2424（スレッド起動）

**重要**: この`_left_rename_background()`メソッドが**現在すべてのプロセスに対して実行される共通処理**

---

## 🔍 Task 1-2: `_left_rename_background()` メソッドの構造分析 ✅ 完了

### メソッドの全体構造

**シグネチャ**:
```python
def _left_rename_background(self, folder_path, yymm, main_prefix, receipt_prefix, normalize_english=False):
```

**パラメータ**:
- `folder_path`: リネーム対象フォルダのパス
- `yymm`: 年月（4桁、例: "2501"）
- `main_prefix`: 本表ファイルの接頭辞（"01", "0001"等）
- `receipt_prefix`: 受信通知の接頭辞（"02", "9999"）
- `normalize_english`: 全角英字を半角に変換するかどうか

**重要**: **`process_type`パラメータは渡されていない**
→ 新Phase 2で追加する必要あり

### 処理フローの詳細

#### ステップ1: 本表ファイルの収集 (Line 2474-2499)

```python
# 本表ファイルパターン: 2桁または4桁の数字_で始まる
main_file_pattern = re.compile(r'^(\d{2,4})_(.+)\.pdf$')

for filename in os.listdir(folder_path):
    # 本表ファイル: 数字_で始まるPDFファイル
    match = main_file_pattern.match(filename)
    if match:
        main_files.append((filename, file_path, match))
    # 受信通知ファイル
    elif filename == "受信通知.pdf":
        receipt_pdf_path = file_path
```

**処理内容**:
- 正規表現で本表ファイルを識別
- `受信通知.pdf`を別途特定
- ファイルリストを作成

**対応プロセス**: すべて（源泉税、申請届出、法定調書、給与支払報告書、償却資産申告書）

#### ステップ2: フォルダ作成とファイルコピー (Line 2501-2568)

```python
for original_filename, original_file_path, match in main_files:
    # ファイル名から番号と残りの部分を抽出
    old_prefix = match.group(1)  # 元の番号
    rest_name = match.group(2)   # 残りの部分

    # 英語半角変換
    if normalize_english:
        rest_name = self._normalize_fullwidth_english(rest_name)

    # rest_nameから帳票名と会社名を抽出
    parts = rest_name.split('_')
    if len(parts) >= 3:
        doc_type = '_'.join(parts[:-2])  # 帳票名
        company_name = parts[-1]          # 会社名
        folder_base_name = f"{doc_type}_{company_name}"
    else:
        folder_base_name = rest_name
        doc_type = rest_name

    # 新しいファイル名: 選択した接頭辞_帳票名.pdf（会社名除去）
    new_filename = f"{main_prefix}_{doc_type}.pdf"

    # フォルダ名: YYMM_帳票名_会社名
    folder_name = f"{yymm}_{folder_base_name}"
    new_folder_path = os.path.join(folder_path, folder_name)

    # フォルダ作成
    os.makedirs(new_folder_path, exist_ok=True)

    # 本表ファイルをコピーしてフォルダ内に配置（元ファイルは残す）
    dest_file_path = os.path.join(new_folder_path, new_filename)
    shutil.copy2(original_file_path, dest_file_path)
```

**処理内容**:
1. ファイル名のパース（顧問先番号の除去）
2. 全角英字の半角変換（オプション）
3. フォルダ名の生成: `YYMM_帳票名_会社名`
4. 本表ファイル名の生成: `接頭辞_帳票名.pdf`
5. フォルダ作成
6. ファイルコピー（`shutil.copy2`で元ファイル保持）

**対応プロセス**: すべて（源泉税、申請届出、法定調書、給与支払報告書、償却資産申告書）

**重要な既存機能**:
- ✅ 接尾辞置換機能（`main_prefix`による接頭辞指定）
- ✅ 全角英字半角変換機能（`normalize_english`オプション）
- ✅ フォルダ選択リネーム機能（フォルダ名生成ロジック）
- ✅ 元ファイル保持機能（`shutil.copy2`使用）

**変更禁止**: これらの既存機能は全て保持必須

#### ステップ3: 受信通知PDFの分割・配置 (Line 2569-2780)

**処理開始条件**:
```python
if receipt_pdf_path and created_folders:
```

**サブステップ3-1**: 一時分割 (Line 2586-2611)

```python
# 一時フォルダ作成
temp_dir = tempfile.mkdtemp(prefix="receipt_temp_")

# 全ページを連番付きで一時分割
for page_num in range(total_pages):
    # ページを抽出
    page_doc = fitz.open()
    page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

    # 連番付きファイル名で一時保存
    temp_filename = f"{receipt_prefix}_受信通知_{page_num + 1:02d}.pdf"
    temp_path = os.path.join(temp_dir, temp_filename)
    page_doc.save(temp_path)

    # 会社名抽出
    receipt_company = matcher.extract_company_name_from_receipt(receipt_pdf_path, page_num)
```

**処理内容**:
1. 受信通知PDFを1ページずつ分割
2. 連番付きで一時保存
3. 各ページから会社名を抽出（OCR）

**使用クラス**: `CompanyNameMatcher` (helpers/company_name_matcher.py)

**サブステップ3-2**: マッチングと配置 (Line 2613-2750)

```python
for temp_path, page_num, receipt_company in temp_receipt_files:
    # すべてのマッチするフォルダを取得
    matched_folders = matcher.match_all_folders(receipt_company, folder_names, threshold=0.7)

    if len(matched_folders) == 1:
        # 単一フォルダ: 連番保持で即配置
        # フォルダ情報取得
        # 受信通知リネーム
        final_filename = self._get_final_receipt_name(receipt_prefix, folder_info['folder_path'], folder_name)
        shutil.move(receipt_dest_path, final_dest_path)

    else:
        # 複数フォルダ: 金額マッチングで最適フォルダ選択
        # (詳細な金額マッチングロジック)
```

**処理内容**:
1. 会社名マッチング（類似度0.7以上）
2. 単一マッチ: 即座に配置
3. 複数マッチ: 金額マッチングで最適フォルダ選択
4. 受信通知リネーム: `接頭辞_受信通知.pdf`

**対応プロセス**: **現在は源泉税のみを想定**（会社名ベースのマッチング）

**新規3プロセスへの対応必要性**:
- ⚠️ **申請届出**: 会社名ではなく**届出の種類**でマッチング必要
- ⚠️ **給与支払報告書**: 会社名マッチングは使えるが、市区町村情報も必要
- ⚠️ **償却資産申告書**: 会社名マッチングは使えるが、市区町村情報も必要

---

## 🚨 重要な発見: 源泉税と法定調書の処理は特定できない

### 調査結果

`_left_rename_background()`メソッド内で**源泉税専用**または**法定調書専用**のロジックを探しましたが、**見つかりませんでした**。

**推測される理由**:
1. 現在の実装は**すべてのプロセスに対して汎用的**に動作している
2. **源泉税と法定調書の区別は、右側の申告書リネーム機能で行われている可能性**
3. 左側は単純に「番号_で始まる本表ファイル」と「受信通知.pdf」を処理しているだけ

### 次のステップ

**Task 1-3**: 右側の申告書リネーム機能を調査し、源泉税・法定調書の処理がそちらで行われているか確認する必要がある。

---

## 📊 現在の処理フロー図

```
[ユーザー: プルダウンで処理プロセス選択]
    ↓
[ユーザー: リネーム実行ボタンクリック]
    ↓
[_left_execute() 実行]  # Line 2390
    ↓
[process_type = self.process_type_var.get()]  # Line 2395
    ↓
[self._log(f"選択されたプロセス: {process_type}")]  # Line 2396
    ↓
[フォルダ選択ダイアログ表示]  # Line 2409
    ↓
[_left_rename_background() スレッド起動]  # Line 2423-2428
    ↓
    ├─ ステップ1: 本表ファイル収集 (Line 2474-2499)
    │   - パターン: ^\d{2,4}_.+\.pdf$
    │   - 受信通知.pdfを特定
    ↓
    ├─ ステップ2: フォルダ作成+ファイルコピー (Line 2501-2568)
    │   - フォルダ名: YYMM_帳票名_会社名
    │   - ファイル名: 接頭辞_帳票名.pdf
    │   - shutil.copy2（元ファイル保持）
    ↓
    └─ ステップ3: 受信通知分割・配置 (Line 2569-2780)
        - ページごとに分割
        - 会社名抽出（OCR）
        - 会社名マッチング（類似度0.7）
        - 金額マッチング（複数候補時）
        - 受信通知リネーム: 接頭辞_受信通知.pdf
```

**重要**: `process_type`は取得されるが、**処理には一切使用されていない**

---

## ✅ Task 1-1 & 1-2 完了基準

- [x] プルダウン値の取得箇所を特定
- [x] 処理分岐の有無を確認（結果: **分岐なし**）
- [x] `_left_rename_background()`メソッドの全体構造を把握
- [x] 現在の処理フロー（ステップ1-3）を完全に理解
- [x] 既存の基本リネーム機能を特定
  - 接尾辞置換機能
  - 全角英字半角変換機能
  - フォルダ選択リネーム機能
  - 元ファイル保持機能
- [x] **既存機能は全て保持必須**であることを確認

---

## 🔜 次のタスク

### Task 1-3: 源泉税・法定調書処理の特定

**調査対象**:
1. 右側パネルの「申告書リネーム」機能
2. `classification_v5.py`の分類ルール
3. OCRパターンマッチングで源泉税・法定調書を判定している箇所

**目的**:
- 源泉税と法定調書がどこで区別されているか特定
- それらの処理ロジックを完全に把握
- **変更禁止箇所を明確にマーク**

---

**分析日時**: 2025年10月8日
**次回更新**: Task 1-3完了時
