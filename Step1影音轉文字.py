import os
import subprocess
import whisper
import time # 引入 time 模組
import sys # <--- 加入 sys 模組

# 定義要處理的影片檔案格式 (保持不變)
VALID_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".mp4 的副本"]

# 定義函式以取得影片長度（秒數）
def get_video_duration(video_path, log_callback):
    """使用 ffprobe 取得影片長度，並透過 log_callback 回報錯誤。"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", video_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True # 如果 ffprobe 失敗會拋出 CalledProcessError
        )
        duration = float(result.stdout.strip())
        return duration
    except FileNotFoundError:
        log_callback(f"【錯誤】找不到 ffprobe 命令。請確保 FFmpeg 已安裝並加入系統 PATH。")
        return None
    except subprocess.CalledProcessError as e:
        log_callback(f"【錯誤】執行 ffprobe 失敗 {video_path}: {e.stderr}")
        return None
    except Exception as e:
        log_callback(f"【錯誤】取得影片長度失敗 {video_path}: {e}")
        return None

# 定義函式進行語音轉文字
def transcribe_video(model, video_path, log_callback):
    """使用 Whisper 模型轉錄影片，並透過 log_callback 回報錯誤。"""
    try:
        result = model.transcribe(video_path, language='zh') # 明確指定語言為中文
        transcription = result.get('text', '')
        if not transcription.strip():
             log_callback(f"【警告】影片轉錄結果為空，請確認影片內容：{os.path.basename(video_path)}")
        return transcription
    except Exception as e:
        log_callback(f"【錯誤】影片轉錄失敗 {os.path.basename(video_path)}: {e}")
        return ""

# ---- 主要處理函數 ----
def process_videos(video_folder, output_folder, model_size="large", log_callback=print):
    """
    處理指定資料夾中的影片檔案，進行轉錄並儲存結果。

    Args:
        video_folder (str): 包含影片檔案的資料夾路徑。
        output_folder (str): 儲存轉錄文字檔的資料夾路徑。
        model_size (str): 要使用的 Whisper 模型大小 (e.g., "tiny", "base", "small", "medium", "large")。
        log_callback (callable): 用於記錄訊息的回呼函數，預設為 print。
    """
    log_callback(f"--- 開始處理 Step 1：影音轉文字 ---")
    log_callback(f"影片來源資料夾: {video_folder}")
    log_callback(f"轉錄輸出資料夾: {output_folder}")
    log_callback(f"使用 Whisper 模型: {model_size}")

    if not os.path.isdir(video_folder):
        log_callback(f"【錯誤】影片來源資料夾不存在: {video_folder}")
        return
    if not os.path.isdir(output_folder):
        log_callback(f"【錯誤】轉錄輸出資料夾不存在: {output_folder}")
        # 或者嘗試建立它？ os.makedirs(output_folder, exist_ok=True)
        # 這裡先回報錯誤讓使用者確認路徑
        return

    # 載入 Whisper 模型
    log_callback("載入 Whisper 模型中...")
    model = None # 先初始化 model 為 None
    # 判斷執行環境並組合模型路徑
    if getattr(sys, 'frozen', False):
        # 打包後的環境，模型路徑在 exe 檔案同目錄
        app_dir = os.path.dirname(sys.executable)
        model_path = os.path.join(app_dir, f"{model_size}.pt")
        log_callback(f"【日誌】打包環境：嘗試從應用程式目錄載入模型: {model_path}")
    else:
        # 開發環境，直接使用模型名稱（讓 Whisper 從快取找）或相對路徑
        # 為了與打包環境一致，也檢查腳本同目錄
        script_dir = os.path.dirname(__file__)
        model_path = os.path.join(script_dir, f"{model_size}.pt")
        log_callback(f"【日誌】開發環境：嘗試從腳本目錄載入模型: {model_path}")
        # 如果腳本目錄沒有，則 model_path 設為 None，讓 Whisper 從快取找
        if not os.path.exists(model_path):
             model_path = None # 設為 None 以便後續從快取載入
             log_callback(f"【日誌】開發環境：腳本目錄未找到模型，將嘗試從快取載入。")

    # 嘗試載入模型
    try:
        if model_path and os.path.exists(model_path):
            model = whisper.load_model(model_path) # 從指定路徑載入
            log_callback(f"【日誌】成功從指定路徑載入模型: {model_path}")
        else:
            # 如果沒有指定路徑或檔案不存在，嘗試讓 Whisper 自動處理（下載或從快取載入）
            log_callback(f"【日誌】嘗試讓 Whisper 自動載入模型 '{model_size}' (可能從快取或下載)...")
            model = whisper.load_model(model_size)
            log_callback(f"【日誌】Whisper 自動載入模型 '{model_size}' 成功！")

    except Exception as e:
        log_callback(f"【嚴重錯誤】載入 Whisper 模型 '{model_size}' 失敗: {e}")
        log_callback("請檢查：")
        log_callback("1. 模型檔案是否已複製到應用程式目錄 (打包後) 或腳本目錄 (開發中)。")
        log_callback("2. 或者，網路連線是否正常以便自動下載/從快取載入。")
        log_callback("3. whisper 套件是否已正確安裝。")
        return # 載入失敗，無法繼續

    # 確保 model 確實被載入
    if model is None:
         log_callback(f"【嚴重錯誤】未能成功載入 Whisper 模型 '{model_size}'。")
         return # 無法繼續

    processed_count = 0
    skipped_count = 0
    total_files = 0

    # --- 新增：先找出所有符合條件的檔案 --- (Moved listing logic up)
    files_to_process = []
    try:
        all_files_in_folder = os.listdir(video_folder)
    except Exception as e:
        log_callback(f"【錯誤】讀取影片來源資料夾內容失敗: {e}")
        return # 無法讀取資料夾，直接返回

    for filename in all_files_in_folder:
        lower_filename = filename.lower()
        if any(lower_filename.endswith(ext) for ext in VALID_EXTENSIONS):
            files_to_process.append(filename)
            total_files += 1 # 在這裡計算總數

    # --- 新增：檢查是否有找到檔案 --- (Check added)
    if total_files == 0:
        log_callback(f"【日誌】在資料夾 '{video_folder}' 中未找到任何符合格式 {VALID_EXTENSIONS} 的影片檔案。")
        log_callback(f"--- Step 1 處理完成 (無檔案可處理) ---")
        return # 沒有檔案可處理，直接返回
    else:
        log_callback(f"【日誌】找到 {total_files} 個符合格式的檔案，準備開始處理...")
    # --- 結束新增檢查 ---

    # 開始遍歷影片資料夾 (現在使用 files_to_process 列表)
    for filename in files_to_process: # <-- Use the pre-filtered list
        # 轉成小寫以便比對 - 不再需要，已在前面處理
        # lower_filename = filename.lower()
        # if any(lower_filename.endswith(ext) for ext in VALID_EXTENSIONS):
            # total_files += 1 # 計算移到前面
            video_path = os.path.join(video_folder, filename)
            log_callback(f"\n====== 開始處理影片 {processed_count + skipped_count + 1}/{total_files}：{filename} ======") # <-- 更新進度顯示

            # 取得影片長度資訊
            duration = get_video_duration(video_path, log_callback)
            if duration is None:
                log_callback(f"【跳過】無法取得影片長度，跳過此影片：{filename}")
                skipped_count += 1
                continue
            log_callback(f"【日誌】影片長度：{duration:.2f} 秒")

            # 呼叫 Whisper 進行語音轉文字
            start_time = time.time()
            log_callback("【日誌】開始轉錄...")
            transcription = transcribe_video(model, video_path, log_callback)
            end_time = time.time()
            log_callback(f"【日誌】影片轉錄完成，耗時: {end_time - start_time:.2f} 秒。")


            # 整合轉錄結果與影片長度資訊
            output_text = f"影片檔名：{filename}\n影片長度：{duration:.2f} 秒\n---------------\n轉錄內容：\n{transcription}"

            # 設定輸出檔案名稱（與原影片同名，副檔名更換為 .txt）
            output_filename = os.path.splitext(filename)[0] + ".txt"
            output_path = os.path.join(output_folder, output_filename)

            # 儲存轉錄結果到文字檔
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(output_text)
                log_callback(f"【日誌】已儲存轉錄結果至：{output_filename}")
                processed_count += 1
            except Exception as e:
                log_callback(f"【錯誤】儲存檔案失敗 {output_filename}: {e}")
                skipped_count += 1
        # else:
            # 可以選擇性地記錄非影片檔案
            # log_callback(f"【忽略】非目標影片格式檔案: {filename}")

    log_callback(f"\n--- Step 1 處理完成 ---")
    log_callback(f"總共找到 {total_files} 個符合格式的檔案。")
    log_callback(f"成功處理: {processed_count} 個檔案。")
    log_callback(f"跳過/失敗: {skipped_count} 個檔案。")

# --- 可選：允許腳本獨立執行 (用於測試) ---
if __name__ == "__main__":
    # 這裡可以設定測試用的路徑
    test_video_folder = r"G:\我的雲端硬碟\自動化生成文案\input_videos" # 請換成您的測試路徑
    test_output_folder = r"G:\我的雲端硬碟\自動化生成文案\Transcriptions_test" # 請換成您的測試路徑
    os.makedirs(test_output_folder, exist_ok=True)

    print(f"** 正在以獨立模式執行 Step1 測試 **")
    print(f"測試影片來源: {test_video_folder}")
    print(f"測試輸出位置: {test_output_folder}")

    # 使用 print 作為回呼函數進行測試
    process_videos(test_video_folder, test_output_folder, model_size="large", log_callback=print)
