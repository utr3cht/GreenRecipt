!pip install yomitoku fastapi uvicorn pyngrok nest-asyncio
import nest_asyncio
from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
import uvicorn
import asyncio
import requests
from PIL import Image, ImageOps
import io
import cv2
import numpy as np
import warnings
import os
import tempfile

# 1. Colab環境チェック & ライブラリインストール
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    print("Colab環境を検出しました。必要なライブラリをインストールします...")
    get_ipython().system('pip install -q "yomitoku[pdf]" python-multipart pyngrok')
    print("ライブラリのインストールが完了しました。")

# 2. ライブラリインポート
try:
    from yomitoku.document_analyzer import DocumentAnalyzer
    from yomitoku.data.functions import load_pdf
    from pyngrok import ngrok, conf
except ImportError as e:
    print(f"ライブラリのインポートに失敗しました: {e}")
    raise

app = FastAPI()

try:
    warnings.filterwarnings('ignore', category=UserWarning, module='onnxruntime')
    analyzer = DocumentAnalyzer(device="cuda")
except Exception as e:
    print(f"DocumentAnalyzerの初期化に失敗しました: {e}")
    analyzer = None

#座標に基づいてテキストを「見た目通りの行」に結合する関数
def extract_text_preserving_layout(results):
    if not results:
        return ""

    elements = []

    # 結果から「段落」または「行」を取得
    source_list = []
    if hasattr(results, "lines") and results.lines:
        source_list = results.lines
    elif hasattr(results, "paragraphs") and results.paragraphs:
        source_list = results.paragraphs
    else:
        return str(results)

    # 座標とテキストを抽出してリスト化
    for item in source_list:
        text = ""
        box = None

        # テキストの取得
        if hasattr(item, "content"): text = item.content
        elif hasattr(item, "contents"): text = item.contents
        elif hasattr(item, "text"): text = item.text

        # 座標の取得 (box属性 または points属性)
        if hasattr(item, "box"):
            box = item.box # [x1, y1, x2, y2] を期待
        elif hasattr(item, "points"):
            # ポリゴン座標の場合は [min_x, min_y, max_x, max_y] に変換
            pts = np.array(item.points)
            if pts.size > 0:
                box = [np.min(pts[:, 0]), np.min(pts[:, 1]), np.max(pts[:, 0]), np.max(pts[:, 1])]

        if text and box is not None:
            # boxがリストや配列なら、中心Y座標を計算
            try:
                center_y = (box[1] + box[3]) / 2
                height = box[3] - box[1]
                elements.append({"text": text, "box": box, "cy": center_y, "h": height, "x": box[0]})
            except:
                # 座標計算できない場合はスキップ
                continue

    if not elements:
        return ""

    # 1. Y座標（上から下）でソート
    elements.sort(key=lambda e: e["cy"])

    merged_lines = []
    current_line_elements = []

    for e in elements:
        if not current_line_elements:
            current_line_elements.append(e)
            continue

        last_e = current_line_elements[-1]

        #  判定ロジック: 高さが重なっているなら「同じ行」とみなす
        # (中心Y座標の差が、文字の高さの半分以下なら同じ行とする)
        if abs(e["cy"] - last_e["cy"]) < (last_e["h"] * 0.6):
            current_line_elements.append(e)
        else:
            # 新しい行へ移る前に、現在の行を確定
            # X座標（左から右）でソート
            current_line_elements.sort(key=lambda x: x["x"])

            # テキストを結合（空白を入れてレイアウトを維持）
            line_str = "  ".join([el["text"] for el in current_line_elements])
            merged_lines.append(line_str)

            # 新しい行を開始
            current_line_elements = [e]

    # 最後の行を処理
    if current_line_elements:
        current_line_elements.sort(key=lambda x: x["x"])
        line_str = "  ".join([el["text"] for el in current_line_elements])
        merged_lines.append(line_str)

    return "\n".join(merged_lines)

@app.get("/")
def read_root():
    return {"message": "Yomitoku API on Colab (Ready)"}

@app.post("/ocr")
async def run_ocr(file: UploadFile = File(...)):
    if analyzer is None:
        raise HTTPException(status_code=503, detail="OCRサービスが初期化されていません。")

    try:
        image_bytes = await file.read()
        all_ocr_text = ""

        # 1. PDFの場合
        if file.content_type == "application/pdf":
            print(f"[DEBUG] PDF処理: {file.filename}")
            imgs = []
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
                temp_pdf.write(image_bytes)
                temp_pdf.flush()
                imgs = load_pdf(temp_pdf.name)

            if not imgs:
                raise HTTPException(status_code=400, detail="PDFの読み込みに失敗しました。")

            loop = asyncio.get_event_loop()
            page_texts = []

            for i, img in enumerate(imgs):
                print(f"[DEBUG] Page {i+1} 処理中...")
                results, _, _ = await loop.run_in_executor(None, analyzer, img)

                #  レイアウト維持関数を使用
                page_text = extract_text_preserving_layout(results)
                if not page_text: page_text = ""
                page_texts.append(page_text)

            all_ocr_text = "\n\n".join(page_texts)

        # 2. 画像の場合
        else:
            print(f"[DEBUG] 画像処理: {file.filename}")
            pil_image = Image.open(io.BytesIO(image_bytes))
            pil_image = ImageOps.exif_transpose(pil_image)
            pil_image = pil_image.convert("RGB")
            img = np.array(pil_image)[:, :, ::-1].copy()

            loop = asyncio.get_event_loop()
            results, _, _ = await loop.run_in_executor(None, analyzer, img)

            #  レイアウト維持関数を使用
            all_ocr_text = extract_text_preserving_layout(results)

            if not all_ocr_text:
                all_ocr_text = "テキストが検出されませんでした。"

        # 結果をファイルに保存 (確認用)
        with open("/content/result.txt", "w", encoding="utf-8") as f:
            f.write(all_ocr_text)
        print(f"[DEBUG] 保存完了: /content/result.txt")

        return {"result": all_ocr_text}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OCR Error: {e}")

# ngrok設定
from google.colab import userdata
NGROK_AUTHTOKEN = userdata.get('NGROK_AUTHTOKEN')
NGROK_HOSTNAME = userdata.get('NGROK_HOSTNAME')

if NGROK_AUTHTOKEN:
    conf.get_default().auth_token = NGROK_AUTHTOKEN
    conf.get_default().region = "jp"
    nest_asyncio.apply()
    try:
        public_url = ngrok.connect(8000, hostname=NGROK_HOSTNAME)
        print(f"公開URL: {public_url}")
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    except Exception as e:
        print(f"起動エラー: {e}")
else:
    print("ngrok Authtokenが設定されていません。")
