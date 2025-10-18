"""
アイコンの背景色を最適な色に変更するスクリプト
現在のアイコンの色使いを分析して、最も似合う背景色を適用します
"""

from PIL import Image
import numpy as np

def analyze_and_change_background(input_path, output_path):
    """アイコンの背景色を分析して最適な色に変更"""

    # 画像を開く
    img = Image.open(input_path)
    img = img.convert('RGBA')  # RGBA形式に変換

    # numpy配列に変換
    data = np.array(img)

    print(f"元の画像サイズ: {img.size}")
    print(f"元の画像モード: {img.mode}")

    # 現在の背景色を検出（左上の角のピクセルを使用）
    original_bg = tuple(data[0, 0])
    print(f"現在の背景色（推定）: RGB{original_bg[:3]}")

    # 背景色の候補を決定
    # 現在のアイコンはライトブルー系なので、それに合う色を選択
    # オプション1: 清潔感のある白 (255, 255, 255)
    # オプション2: ソフトなライトグレー (245, 245, 245)
    # オプション3: より落ち着いたグレー (240, 240, 240)

    # 税務書類アプリなので、プロフェッショナルかつクリーンな印象の白を選択
    new_bg_color = (255, 255, 255, 255)  # 白

    print(f"新しい背景色: RGB{new_bg_color[:3]}")

    # 背景色の範囲を定義（現在の背景色に近い色をすべて検出）
    # RGBの各チャンネルで±30の範囲を背景とみなす
    tolerance = 30
    bg_mask = (
        (np.abs(data[:, :, 0].astype(int) - original_bg[0]) <= tolerance) &
        (np.abs(data[:, :, 1].astype(int) - original_bg[1]) <= tolerance) &
        (np.abs(data[:, :, 2].astype(int) - original_bg[2]) <= tolerance)
    )

    # 背景部分を新しい色に置き換え
    data[bg_mask] = new_bg_color

    # 画像に戻す
    new_img = Image.fromarray(data, 'RGBA')

    # PNG形式で保存
    new_img.save(output_path, 'PNG')
    print(f"\n背景色を変更して保存しました: {output_path}")

    # .icoファイルも生成（Windowsアプリ用）
    ico_path = output_path.replace('.png', '.ico')
    # 複数サイズのアイコンを生成
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    new_img.save(ico_path, format='ICO', sizes=sizes)
    print(f".icoファイルも生成しました: {ico_path}")

if __name__ == "__main__":
    input_path = "assets/app_icon.png"
    output_path = "assets/app_icon_new.png"

    analyze_and_change_background(input_path, output_path)

    print("\n完了！新しいアイコンを確認してください。")
    print("問題なければ、以下のコマンドで元のファイルを置き換えてください:")
    print(f"  copy {output_path} {input_path}")
