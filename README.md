# 🧾 税務書類リネームシステム v6.0.0-COMPLETE-PHASE3

[![税務書類](https://img.shields.io/badge/%E7%A8%8E%E5%8B%99%E6%9B%B8%E9%A1%9E-v6.0.0--complete--phase3-brightgreen.svg)](https://github.com/Ezark213/tax-doc-renamer)
[![Python](https://img.shields.io/badge/Python-3.13+-green.svg)](https://www.python.org)
[![Enterprise](https://img.shields.io/badge/Enterprise-Production%20Ready-blue.svg)](https://github.com/Ezark213/tax-doc-renamer)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-AI%20Integrated-purple.svg)](https://claude.ai/code)
[![Phase3完了](https://img.shields.io/badge/Phase3-%E5%AE%8C%E4%BA%86-success.svg)](https://github.com/Ezark213/tax-doc-renamer)
[![最新更新](https://img.shields.io/badge/%E6%9C%80%E6%96%B0%E6%9B%B4%E6%96%B0-2025.09.30-red.svg)](https://github.com/Ezark213/tax-doc-renamer)

**エンタープライズ本番環境対応の日本税務書類自動分類・リネームシステムです。**
Phase3完了により、4つの重要バグ修正と設定永続化システムが実装され、最高品質のユーザー体験を実現します。

## 🚀 **v6.0.0-COMPLETE-PHASE3 - Phase3: 4大バグ修正完全実装版！（2025年9月30日）**

### 🎯 **Phase3完了: 4つの重要バグ修正実装**

#### 🔧 **Bug #1: 不要なYYMM表示削除**
- ✅ **問題解決**: `✓正常：2508→2508（6001,6002,6003,0000）`の冗長表示を修正
- ✅ **実装内容**: 同値時は`✓正常: 2508`の簡潔表示に改善
- ✅ **効果**: UIの簡素化・ユーザビリティ向上

#### 🗑️ **Bug #2: キーワード辞書エクスポート機能削除**
- ✅ **問題解決**: 開発者向け機能の誤配布を除去
- ✅ **実装内容**: `_export_keyword_dictionary`メソッド完全削除
- ✅ **効果**: エンドユーザー向けインターフェースの純化

#### 📁 **Bug #3: snapshots一時ディレクトリ化**
- ✅ **問題解決**: 固定snapshotsフォルダの自動作成を停止
- ✅ **実装内容**: 一時ディレクトリ使用+atexit自動クリーンアップ
- ✅ **効果**: ディスク容量節約・環境クリーン化

#### 💾 **Bug #4: 設定値永続化システム**
- ✅ **問題解決**: YYMM値・市町村設定の未保存問題を解決
- ✅ **実装内容**: `helpers/user_settings.py`新規作成・JSON永続化
- ✅ **効果**: ユーザー体験向上・設定保持機能実現

### 🧪 **完全検証済み - 統合テスト結果**
- ✅ **アプリケーション正常起動・動作確認**
- ✅ **設定値保存・読み込み機能確認**
- ✅ **一時ディレクトリ自動管理確認**
- ✅ **UI改善効果確認**
- ✅ **既存機能への影響なし確認**

### 📦 **新規実装ファイル**
- **`helpers/user_settings.py`**: 設定永続化システム（新規作成）
- **`config/user_settings.json`**: 自動生成設定ファイル
- **テスト環境**: 一時ディレクトリ自動管理システム

---

## 📋 主要機能

### 🎯 **左側機能（NEW）**
- **数字プレフィックス置換**: 4桁数字_を自動検出してYYMM_に置換
- **完全独立処理**: 右側エンジンに依存しない専用ロジック
- **UI結果表示**: 処理結果を右側と同じ一覧表に表示
- **エラー処理**: 重複回避・例外ハンドリング完備

### 🎯 **右側機能（継承）**
- **AI自動分類**: OCRでPDF内容を読み取り30種類以上の書類を自動分類
- **連番対応**: 地方税受信通知の連番システム（1003→1013→1023）
- **動的命名**: 自治体名を自動検出して適切なファイル名を生成
- **Bundle分割**: 束ねPDFを自動検出・個別ファイル分割

## 🚀 クイックスタート

### 📦 インストール
```bash
git clone https://github.com/Ezark213/tax-doc-renamer.git
cd tax-doc-renamer
pip install -r requirements.txt
python main.py
```

### ⚡ 使用方法
1. **左側機能**: YYMM入力 → フォルダ選択 → 数字プレフィックス置換
2. **右側機能**: YYMM入力 → PDFドラッグ&ドロップ → AI自動分類

## 📁 プロジェクト構造

```
tax-doc-renamer/
├── 🎯 main.py                    # メインアプリケーション（Phase3完全版）
├── 🏗️ core/                     # コアモジュール
│   ├── classification_v5.py      # AI分類エンジン
│   ├── rename_engine.py           # リネーム処理
│   └── ocr_engine.py             # OCR処理エンジン
├── 🛠️ helpers/                   # ヘルパーモジュール（NEW）
│   └── user_settings.py          # 設定永続化システム
├── ⚙️ config/                    # 設定ファイル（NEW）
│   ├── ui_config.yaml            # UI設定
│   └── user_settings.json        # ユーザー設定（自動生成）
├── 🎨 ui/                        # ユーザーインターフェース
├── 🧪 tests/                     # テストスイート
├── 📚 docs/                      # 技術文書
├── 📦 old/                       # アーカイブファイル（整理済み）
├── 📄 requirements.txt           # Python依存関係
├── 📋 README.md                  # プロジェクト説明（このファイル）
├── 📝 CLAUDE.md                  # 開発記録・作業ログ
└── 🏷️ VERSION.txt                # バージョン情報
```

## 📊 システム要件

- **OS**: Windows 10/11 (64bit)、macOS、Linux
- **Python**: 3.8+ 
- **メモリ**: 4GB以上推奨
- **ストレージ**: 200MB以上の空き容量

## 🔗 関連リンク

- [技術仕様書](docs/SYSTEM_REQUIREMENTS.md)
- [過去バージョン履歴](docs/README_ARCHIVE_v5.5.0.md)
- [開発記録](CLAUDE.md)

## 📄 ライセンス

このプロジェクトはMITライセンスの下でライセンスされています。

## 📞 サポート

問題が発生した場合は、[Issues](https://github.com/Ezark213/tax-doc-renamer/issues)で報告してください。

---

**🎯 税務書類リネームシステム v6.0.0-COMPLETE**
**左側リネーム機能完全実装・AttributeError完全解決・UI統合完成版**

🚀 **Complete Version!** 左右独立機能・全エラー解決・統合UI完成

**📅 最終更新: 2025年9月30日**
**🚀 Phase3完了: 4大バグ修正・完全整理版**

## 📊 **Phase3成果サマリー**

### ✅ **完了した改善項目**
- **Bug修正**: 4つの重要バグ完全解決
- **設定永続化**: JSON基盤の設定保存システム実装
- **ディレクトリ整理**: プロジェクト構造の大幅クリーンアップ
- **ドキュメント整備**: README.md完全更新・統合
- **GitHub更新**: ブランチ作成・プッシュ・PR準備完了

### 📈 **品質向上指標**
- **ユーザビリティ**: 不要表示削除・UI簡素化
- **保守性**: 設定永続化・自動クリーンアップ
- **可読性**: プロジェクト構造整理・ドキュメント統合
- **安定性**: 統合テスト実施・動作確認完了

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>