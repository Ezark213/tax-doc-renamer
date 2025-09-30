# 🛡️ Windows Defender 除外設定ガイド

## はじめに
税務書類リネームシステム v5.4.1を安全に実行するため、Windows Defenderの除外設定を推奨します。

## 📋 除外設定手順

### 1. Windows Security設定を開く
```
Windows キー + I → 更新とセキュリティ → Windows Security → ウイルスと脅威の防止
```

### 2. 除外の追加
「ウイルスと脅威の防止の設定」→「設定の管理」→「除外の追加または削除」

### 3. 以下のパスを除外リストに追加

#### ✅ 必須除外パス
```
フォルダ: C:\Users\mayum\tax-doc-renamer
フォルダ: C:\Users\mayum\tax-doc-renamer\dist_secure
ファイル: C:\Users\mayum\tax-doc-renamer\dist_secure\TaxDocumentRenamer_v5.4.1_BalanceTrialFix.exe
```

#### 🔧 開発環境用（オプション）
```
フォルダ: C:\Users\mayum\tax-doc-renamer\build_secure
フォルダ: C:\Users\mayum\tax-doc-renamer\__pycache__
拡張子: .pyc （プロジェクトフォルダ内のみ）
```

### 4. リアルタイム保護の一時停止（ビルド時のみ）
ビルド実行時に誤検知が発生した場合、一時的にリアルタイム保護を無効化：
```
Windows Security → ウイルスと脅威の防止 → リアルタイム保護をオフ
```
⚠️ **ビルド完了後は必ず再有効化してください**

## 🔐 SmartScreen設定

### Microsoft Defender SmartScreen設定
```
Windows キー + I → アプリ → アプリと機能 → Microsoft Defender SmartScreen
```

初回実行時の対処：
1. 「WindowsによってPCが保護されました」が表示
2. 「詳細情報」をクリック
3. 「実行」ボタンをクリック

## 📊 ファイアウォール設定

### Windows Defenderファイアウォール
通常は設定不要ですが、ネットワークエラーが発生した場合：
```
コントロールパネル → システムとセキュリティ → Windows Defenderファイアウォール
→ アプリまたは機能をWindows Defenderファイアウォール経由で許可
```

## 🚨 セキュリティ注意事項

### ✅ 安全な実践
- 除外設定は必要最小限に留める
- 定期的にウイルススキャンを実行
- Windows Update を最新に保つ
- ファイルの出所を常に確認

### ❌ 危険な行為
- システム全体の保護を無効化
- 不明なソースからのファイル実行
- 除外リストに不要なパスを追加

## 📞 トラブルシューティング

### よくある問題

1. **「ウイルスが検出されました」エラー**
   - 上記の除外設定を実施
   - ファイルを隔離から復元

2. **「アプリが実行できません」エラー**
   - SmartScreen設定を確認
   - 管理者権限で実行

3. **「アクセスが拒否されました」エラー**
   - フォルダのアクセス許可を確認
   - 制御されたフォルダーアクセスを無効化（一時的）

## 📋 設定確認リスト

- [ ] tax-doc-renamerフォルダを除外リストに追加
- [ ] dist_secureフォルダを除外リストに追加  
- [ ] 生成されたexeファイルを除外リストに追加
- [ ] SmartScreen警告への対処法を理解
- [ ] ビルド後のリアルタイム保護再有効化を確認

## 🤖 自動化スクリプト（管理者権限必要）

```powershell
# PowerShell (管理者として実行)
Add-MpPreference -ExclusionPath "C:\Users\mayum\tax-doc-renamer"
Add-MpPreference -ExclusionPath "C:\Users\mayum\tax-doc-renamer\dist_secure"
```

---

**⚠️ セキュリティ免責事項**
この設定は税務書類リネームシステムの正常動作のためのものです。
システムのセキュリティレベルを下げる可能性があるため、使用後は設定を見直してください。