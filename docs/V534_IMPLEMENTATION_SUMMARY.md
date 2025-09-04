# v5.3.4「表示整合性 + 地方税コード最終化 + ノイズ抑制」実装完了

## 実装概要

v5.3.4では、表示整合性の修正、地方税の県別コードマッピングの実装、ドメイン外ノイズの抑制、明示的リセットログの追加を行いました。

## 修正内容

### 1. 表示整合性の修正 ✅

**問題**: 「詳細分類結果」で 2001_市民税 が表示され続ける

**解決策**: main.py:1314-1329 で詳細分類結果表示ロジックを修正
- `original_doc_type_code` を優先表示に変更
- 自治体変更版は別途表示するように修正
- 表示/ログ/ファイル名の三者一致を実現

```python
# 表示は最終使用コード（ファイル名と一致）を使用
display_document_type = classification_result.original_doc_type_code if (
    hasattr(classification_result, 'original_doc_type_code') and 
    classification_result.original_doc_type_code
) else classification_result.document_type

self._log(f"📋 分類結果: {display_document_type}")

# 自治体変更版がある場合のみ表示
if (hasattr(classification_result, 'original_doc_type_code') and 
    classification_result.original_doc_type_code and
    classification_result.original_doc_type_code != classification_result.document_type):
    self._log(f"📍 自治体変更版: {classification_result.document_type}")
```

### 2. 地方税コード最終化の実装 ✅

**問題**: 地方税（都道府県）の最終コードが 1001 固定

**解決策**: classification_v5.py に prefecture-specific code mapping を実装

#### 新機能: `resolve_local_tax_class` 関数
```python
def resolve_local_tax_class(self, base_class: str, prefecture: Optional[str] = None, 
                           city: Optional[str] = None) -> str:
    """LOCAL_TAX ドメインの場合のみ、自治体別の最終クラスコードを確定"""
```

#### 都道府県コードマッピング
```python
self.prefecture_code_map = {
    "東京都": "1001",
    "愛知県": "1011", 
    "福岡県": "1021",
    "大阪府": "1031",
    "神奈川県": "1041"
}
```

**結果**: 
- 愛知県 → 1011_愛知県_法人都道府県民税・事業税・特別法人事業税_2507.pdf
- 福岡県 → 1021_福岡県_法人都道府県民税・事業税・特別法人事業税_2507.pdf
- 東京都 → 1001_東京都_法人都道府県民税・事業税・特別法人事業税_2507.pdf

### 3. ノイズ抑制の実装 ✅

**問題**: 国税/会計でも「自治体変更版: 2001_…」がログ出力される

**解決策**: ドメイン門番機能を実装

#### 新機能: `code_domain` 関数
```python
def code_domain(self, code: str) -> str:
    """コードドメイン判定 - ノイズ抑制のための門番"""
    domain_map = {
        "0": "NATIONAL_TAX",      # 国税
        "1": "LOCAL_TAX",         # 地方税（都道府県）
        "2": "LOCAL_TAX",         # 地方税（市町村）
        "3": "CONSUMPTION_TAX",   # 消費税
        "5": "ACCOUNTING",        # 会計書類
        "6": "ASSETS",           # 資産
        "7": "SUMMARY"           # 集計・その他
    }
```

#### オーバーレイ候補生成の更新
LOCAL_TAX以外では自治体変更版の生成をスキップ:
```python
# ドメインチェック：LOCAL_TAX以外では自治体変更版をスキップ
domain = self.code_domain(base_result.document_type)
if domain != "LOCAL_TAX":
    self._log(f"overlay=SKIPPED(domain={domain})")
else:
    # LOCAL_TAXの場合のみ自治体処理を実行
```

**結果**: 国税/会計/資産/集計では「overlay=SKIPPED(domain=...)」と1行で簡潔にログ出力

### 4. 明示的リセットログの追加 ✅

**問題**: Split処理の開始が不明確

**解決策**: 分割処理開始時に明示的リセットログを追加

```python
# v5.3.4 Split reset logging
self._log(f"[reset] __split_ 処理開始 - 分割状態リセット")
self._log(f"[reset] __split_ 一括処理開始 - 処理状態リセット")
```

## テスト結果 ✅

`test_v534_noise_suppression.py` で全機能をテスト:

```
v5.3.4 ノイズ抑制・リセットログ統合テスト開始
============================================================
テスト結果サマリー
============================================================
ドメイン判定: PASS
地方税コード解決: PASS
ノイズ抑制: PASS
リセットログ: PASS

合計: 4/4 テスト通過
全テスト成功！v5.3.4 の修正が正常に動作しています。
```

## 受け入れ基準の確認 ✅

### A. 国税・会計・資産・集計（非分割/分割）
- **表示/ログ/ファイル名** がすべて一致 ✅
- **「自治体変更版: …」は一切出力されない** ✅ → `overlay=SKIPPED(domain=...)` のみ
- **「詳細分類結果」の書類種別も一致し、2001 へは変化しない** ✅

### B. 地方税（都道府県）
- **愛知県の県税**: 1011_愛知県_法人都道府県民税・事業税・特別法人事業税_2507.pdf ✅
- **福岡県の県税**: 1021_福岡県_法人都道府県民税・事業税・特別法人事業税_2507.pdf ✅
- **東京都の県税**: 1001_東京都_法人都道府県民税・事業税・特別法人事業税_2507.pdf ✅

### C. リセットログ
- **分割処理開始時にリセットログが必ず1回出る** ✅

## 実装ファイル

1. **main.py**: 表示整合性修正、リセットログ追加
2. **core/classification_v5.py**: ドメイン門番、地方税コード解決機能
3. **test_v534_noise_suppression.py**: 統合テスト

## まとめ

v5.3.4 の全目標を達成:
- ✅ 画面・ログ・最終ファイル名の三者でクラス表示が一致
- ✅ 地方税の県別最終クラスコード確定（1011_愛知県、1021_福岡県等）
- ✅ LOCAL_TAX以外での自治体変更版ノイズを完全抑制
- ✅ 分割処理開始時の明示的リセットログ

全ての受け入れ基準をクリアし、テストも全て通過しています。