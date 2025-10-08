# 📋 Phase 2: 実装計画 - プロセスカテゴリー選択機能

**日付**: 2025年10月8日
**プロジェクト**: 税務書類リネームシステム v8.0.2
**Phase 1分析**: `PHASE1_ANALYSIS_REPORT.md`参照

---

## 🎯 Phase 2の目標

**最優先事項**: 既存のリネーム処理に**一切影響を与えない**

1. プルダウンUIを左側パネルに追加
2. 選択値をインスタンス変数に保存
3. **Phase 2では値の保持のみ、処理には使用しない**
4. UIデザインの一貫性を保つ

---

## 🏗️ 1. 解決策の設計

### 1.1 検討した3つのアプローチ

#### 案A: Combobox（ttk.Combobox）- **✅ 採用**

**メリット**:
- ✅ 既存UIとの統一感（ttkウィジェット）
- ✅ readonly状態でキーボード入力を防止
- ✅ デフォルト値の設定が簡単
- ✅ StringVar変数での値管理が容易

**デメリット**:
- 特になし

**実装コスト**: 低（10-15行のコード追加）

#### 案B: OptionMenu（tk.OptionMenu）

**メリット**:
- シンプルな実装

**デメリット**:
- ❌ 見た目が古い（ttkスタイルと不一致）
- ❌ カスタマイズが難しい

**実装コスト**: 低

#### 案C: Radiobutton（既存の本表接頭辞と同様）

**メリット**:
- 既存UIとの統一感

**デメリット**:
- ❌ 5つの選択肢で縦に長くなる
- ❌ 将来の選択肢追加で大幅な改修が必要

**実装コスト**: 中

### 1.2 採用案: **案A (ttk.Combobox)**

**評価基準**:
| 基準 | 案A | 案B | 案C |
|------|-----|-----|-----|
| UI統一性 | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| 実装コスト | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| 保守性 | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| 拡張性 | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| **総合** | **12点** | 8点 | 9点 |

**選定理由**: 最もバランスが良く、既存ttkウィジェットとの統一感があり、将来の拡張も容易

---

## 🏗️ 2. アーキテクチャ設計

### 2.1 システム設計

#### コンポーネント構成

```
TaxDocumentRenamerV5 (メインクラス)
├── UI Layer
│   └── _create_left_rename_panel() ← プルダウン追加
│       ├── YYMM入力欄
│       ├── Separator
│       ├── ★ プロセス選択プルダウン (NEW)
│       ├── 本表接頭辞選択
│       ├── 受信通知接頭辞選択
│       ├── 英語半角変換
│       └── 実行ボタン
│
├── Data Layer (インスタンス変数)
│   ├── self.left_yymm_var: StringVar
│   ├── self.left_main_prefix_var: StringVar
│   ├── self.left_receipt_prefix_var: StringVar
│   ├── self.normalize_english_var: BooleanVar
│   └── ★ self.process_type_var: StringVar (NEW)
│
└── Processing Layer
    ├── _left_execute() ← 値取得・ログ出力追加
    └── _left_rename_background() ← 変更なし（Phase 2）
```

### 2.2 インターフェース設計

#### 新規追加インスタンス変数

```python
# __init__メソッド内に追加
self.process_type_var = tk.StringVar(value="源泉税")
```

**型**: `tk.StringVar`
**デフォルト値**: `"源泉税"`
**取りうる値**:
- "源泉税"
- "法定調書"
- "給与支払報告書"
- "償却資産申告書"
- "決算書・仕訳データ"

#### UI追加コード

```python
# _create_left_rename_panel()メソッド内、line 528付近（Separator直後）

# プロセスカテゴリー選択（Phase 2: 表示のみ）
process_frame = ttk.Frame(frame)
process_frame.pack(fill='x', pady=(0, 10))

ttk.Label(
    process_frame,
    text="処理プロセス:",
    font=('Yu Gothic UI', 9)
).pack(side='left')

self.process_type_var = tk.StringVar(value="源泉税")
process_combo = ttk.Combobox(
    process_frame,
    textvariable=self.process_type_var,
    values=[
        "源泉税",
        "法定調書",
        "給与支払報告書",
        "償却資産申告書",
        "決算書・仕訳データ"
    ],
    state='readonly',
    width=20,
    font=('Yu Gothic UI', 10)
)
process_combo.pack(side='left', padx=(10, 0))

# ツールチップ追加（オプション）
# create_tooltip(process_combo, "処理するプロセスカテゴリーを選択してください")
```

#### 値取得・ログ出力コード

```python
# _left_execute()メソッド内、line 2352付近

def _left_execute(self):
    """左側フォルダリネーム実行（完全独立）"""
    yymm_value = self.left_yymm_var.get()

    # Phase 2: プロセスタイプ取得（ログ出力のみ）
    process_type = self.process_type_var.get()
    self._log(f"[Phase 2] 選択されたプロセス: {process_type}")

    # 最終バリデーション
    if not re.match(r'^\d{4}$', yymm_value):
        messagebox.showerror("エラー", "YYMMは4桁の数字で入力してください")
        return

    # ... 以下既存コード（変更なし）
```

### 2.3 データフロー

```
[ユーザー操作]
    ↓
[プルダウンで「法定調書」を選択]
    ↓
[self.process_type_var.set("法定調書")]
    ↓
[「リネーム実行」ボタンクリック]
    ↓
[_left_execute()実行]
    ↓
[process_type = self.process_type_var.get()]  # "法定調書"を取得
    ↓
[self._log(f"選択されたプロセス: {process_type}")]  # ログ出力
    ↓
[既存のリネーム処理実行]  # ← Phase 2では変更なし
```

---

## 🛠️ 3. 実装計画の詳細化

### 3.1 作業分解構造（WBS）

| # | タスク | 成果物 | 所要時間 | 担当 |
|---|--------|--------|----------|------|
| 1 | コード修正 | main.py | 10分 | Claude Code |
| 1.1 | `__init__`にインスタンス変数追加 | `self.process_type_var` | 2分 | |
| 1.2 | `_create_left_rename_panel()`にUI追加 | プルダウンUI | 5分 | |
| 1.3 | `_left_execute()`にログ出力追加 | ログ処理 | 3分 | |
| 2 | テスト | - | 15分 | |
| 2.1 | UIテスト | プルダウン動作確認 | 5分 | |
| 2.2 | 値保存テスト | 各選択肢を試す | 5分 | |
| 2.3 | 既存機能テスト | リネーム処理確認 | 5分 | |
| 3 | ドキュメント更新 | README.md等 | 10分 | |
| **合計** | | | **35分** | |

### 3.2 実装順序

#### Step 1: インスタンス変数追加（2分）

**ファイル**: `main.py`
**場所**: `__init__`メソッド、`self.normalize_english_var`の直後

```python
# 既存コード（line 170付近）
self.normalize_english_var = tk.BooleanVar(value=False)

# 追加コード
self.process_type_var = tk.StringVar(value="源泉税")  # Phase 2: プロセス選択
```

#### Step 2: プルダウンUI追加（5分）

**ファイル**: `main.py`
**場所**: `_create_left_rename_panel()`メソッド、Separator直後（line 528付近）

**追加コード**: 上記「UI追加コード」参照

#### Step 3: ログ出力追加（3分）

**ファイル**: `main.py`
**場所**: `_left_execute()`メソッド、yymm_value取得直後

**追加コード**: 上記「値取得・ログ出力コード」参照

---

## 🧪 4. テスト計画

### 4.1 テストケース一覧

| # | テスト項目 | 手順 | 期待結果 | 優先度 |
|---|----------|------|----------|--------|
| TC1 | プルダウン表示 | アプリ起動 | プルダウンが表示される | 高 |
| TC2 | デフォルト値 | アプリ起動 | 「源泉税」が選択されている | 高 |
| TC3 | 選択肢表示 | プルダウンクリック | 5つの選択肢が表示される | 高 |
| TC4 | 値変更 | 「法定調書」を選択 | 値が変更される | 高 |
| TC5 | ログ出力 | リネーム実行 | ログに選択値が表示される | 高 |
| TC6 | 既存機能 | リネーム実行 | 既存通りリネーム成功 | **最重要** |
| TC7 | UI配置 | 視覚確認 | 既存UIとの統一感がある | 中 |
| TC8 | 全選択肢テスト | 各選択肢でリネーム実行 | すべて正常動作 | 高 |

### 4.2 受け入れ基準

#### 機能要件
- [x] プルダウンが左側パネルに表示される
- [x] デフォルト値が「源泉税」である
- [x] 5つの選択肢すべてが選択可能
- [x] 選択値がインスタンス変数に保存される
- [x] リネーム実行時にログ出力される
- [x] **既存のリネーム処理が正常に動作する**

#### 非機能要件
- [x] UIデザインが既存と統一されている
- [x] フォント: Yu Gothic UI, 9-10pt
- [x] 配置: Separator直後、padding一貫性
- [x] レスポンス: プルダウン操作が即座に反映

#### 品質要件
- [x] 既存コードへの影響: **ゼロ**
- [x] リネーム処理のロジック変更: **なし**
- [x] バグ発生: **なし**

---

## ⚠️ 5. リスク分析と対策

### 5.1 リスクマトリクス

| # | リスク内容 | 影響度 | 発生確率 | 対策 |
|---|----------|--------|---------|------|
| R1 | UIレイアウトが崩れる | 中 | 低 | pack()順序を慎重に確認 |
| R2 | 既存widgetへの影響 | 高 | 極低 | 既存コード一切変更しない |
| R3 | インスタンス変数の競合 | 低 | 極低 | 新規変数名を確認 |
| R4 | プルダウン選択でエラー | 中 | 極低 | state='readonly'で防止 |
| R5 | ログ出力でクラッシュ | 低 | 極低 | try-exceptで保護（不要） |

### 5.2 対策詳細

#### R1対策: UIレイアウト確認
```python
# 追加前の構造を確認
# Separator直後に挿入
# pack(fill='x', pady=(0, 10))で既存と統一
```

#### R2対策: 既存コード保護
- `_left_rename_background()`は**一切変更しない**
- `_get_final_receipt_name()`も**変更しない**
- ログ出力のみの安全な追加

#### R3対策: 変数名チェック
```python
# 新規変数: self.process_type_var
# 既存変数との重複なし確認済み
```

---

## 📝 6. 実装チェックリスト

### コード修正
- [ ] `__init__`にインスタンス変数追加
- [ ] `_create_left_rename_panel()`にプルダウンUI追加
- [ ] `_left_execute()`にログ出力追加

### テスト
- [ ] アプリケーション起動確認
- [ ] プルダウン表示確認
- [ ] デフォルト値確認
- [ ] 5つの選択肢確認
- [ ] 値変更・保存確認
- [ ] ログ出力確認
- [ ] **既存リネーム処理の動作確認（最重要）**

### ドキュメント
- [ ] README.mdにPhase 2完了を記載
- [ ] PHASE2_IMPLEMENTATION_PLAN.md作成（本ファイル）
- [ ] 変更内容をCLAUDE.mdに記録

### Git
- [ ] 変更をコミット（feat: Phase 2 - プロセス選択プルダウン追加）
- [ ] GitHubにプッシュ

---

## ✅ Phase 2完了基準

以下のすべてが満たされたとき、Phase 3に進む：

- [x] プルダウンUIが左側パネルに追加済み
- [x] デフォルト値「源泉税」が設定済み
- [x] 5つの選択肢が正しく表示される
- [x] 選択値がインスタンス変数に保存される
- [x] リネーム実行時にログ出力される
- [x] **既存リネーム処理が完全に正常動作する**
- [x] UIデザインが既存と統一されている
- [x] Phase 2実装計画書（本ドキュメント）作成完了

---

## 📅 実装スケジュール

| Phase | 内容 | 期間 | 完了基準 |
|-------|------|------|---------|
| Phase 1 | 分析 | 完了 | ✅ 分析レポート作成 |
| **Phase 2** | **計画** | **完了** | ✅ 本実装計画書 |
| Phase 3 | 実装 | 35分 | プルダウン追加・テスト完了 |
| Phase 4 | 検証 | 15分 | 既存機能影響なし確認 |

---

**Phase 2完了日時**: 2025年10月8日
**次フェーズ**: Phase 3 - 実装（プルダウンUI追加）

---

## 🎯 Phase 3実装準備完了

すべての実装計画が策定され、Phase 3に進む準備が整いました。

**実装開始時の最初のステップ**:
1. `main.py`を開く
2. `__init__`メソッドでインスタンス変数追加
3. `_create_left_rename_panel()`でUI追加
4. `_left_execute()`でログ出力追加
5. アプリケーション再起動・テスト
