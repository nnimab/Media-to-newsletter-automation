# step2_3_processor.py
import os
import re # 加在這裡以防 Step3 忘記匯入

# 匯入重構後的函數
try:
    from Step2分類 import perform_classification
    step2_available = True
except ImportError as e:
    print(f"無法匯入 Step2分類: {e}") # 初始匯入時打印錯誤
    step2_available = False

try:
    from Step3合併txt import perform_merging
    step3_available = True
except ImportError as e:
    print(f"無法匯入 Step3合併txt: {e}") # 初始匯入時打印錯誤
    step3_available = False


def run_classification_and_merging(
    transcription_folder,
    label_folder,
    url_config_path,
    output_queue_folder,
    unpaired_folder,
    api_key,
    classification_criteria,
    merging_strategy,
    log_callback=print
):
    """
    協調執行分類和合併步驟。

    Returns:
        bool: True 如果整個過程成功完成，False 如果有錯誤。
    """
    if not step2_available:
        log_callback("【嚴重錯誤】Step 2 (分類) 模組無法載入，處理中止。")
        return False
    if not step3_available:
        log_callback("【嚴重錯誤】Step 3 (合併) 模組無法載入，處理中止。")
        return False

    log_callback("--- 開始 Step 2/3 處理流程 ---")

    # 1. 執行分類
    labels_dict = perform_classification(
        transcription_folder=transcription_folder,
        label_folder=label_folder,
        url_config_path=url_config_path,
        api_key=api_key,
        classification_criteria=classification_criteria,
        log_callback=log_callback
    )

    if labels_dict is None:
        log_callback("【錯誤】分類步驟執行失敗，中止 Step 2/3 流程。")
        return False

    if not labels_dict:
         log_callback("【警告】分類步驟未產生任何標籤結果 (可能資料夾為空或所有檔案讀取失敗)。")
         # 根據需求，這裡可以選擇繼續執行合併（例如不合併策略），或直接返回 True
         # 暫定為繼續，讓 perform_merging 處理空字典的情況

    # 2. 執行合併
    merge_success = perform_merging(
        labels_dict=labels_dict,
        transcription_folder=transcription_folder,
        output_queue_folder=output_queue_folder,
        unpaired_folder=unpaired_folder,
        merging_strategy=merging_strategy,
        log_callback=log_callback
    )

    if not merge_success:
         log_callback("【錯誤】合併步驟執行過程中發生錯誤。")
         # 即使合併出錯，分類可能已成功，所以仍回傳 False 表示流程未完全成功

    log_callback("--- Step 2/3 處理流程結束 ---")
    return merge_success # 回傳合併步驟的結果

# --- 可選：用於測試的區塊 ---
if __name__ == "__main__":
    print("** 正在執行 Step 2/3 Processor 測試 **")

    # --- 測試設定 (與 Step2/Step3 測試一致) ---
    test_transcription_folder = r"G:\我的雲端硬碟\自動化生成文案\Transcriptions"
    test_label_folder = r"G:\我的雲端硬碟\自動化生成文案\Label_test"
    test_url_config_path = r"G:\我的雲端硬碟\自動化生成文案\video_urls_test.json"
    test_output_queue_folder = r"G:\我的雲端硬碟\自動化生成文案\待轉文案_test"
    test_unpaired_folder = r"G:\我的雲端硬碟\自動化生成文案\漏單_test"
    test_api_key = "YOUR_API_KEY" # <--- 填入您的 API 金鑰

    # --- 選擇測試條件 ---
    # test_criteria = "教學/示範 & 長度 (需 API)"
    # test_criteria = "主要內容主題 (需 API)"
    test_criteria = "影片長度 (無需 API)"

    # test_strategy = "不合併"
    test_strategy = "依據分類合併"
    # test_strategy = "兩兩配對 (僅適用原始分類)"

    print(f"測試分類條件: {test_criteria}")
    print(f"測試合併策略: {test_strategy}")

    if ("API" in test_criteria and test_api_key == "YOUR_API_KEY"):
         print("\n!!警告!! 測試需要 API 金鑰，請在程式碼中設定 test_api_key")
    else:
        success = run_classification_and_merging(
            transcription_folder=test_transcription_folder,
            label_folder=test_label_folder,
            url_config_path=test_url_config_path,
            output_queue_folder=test_output_queue_folder,
            unpaired_folder=test_unpaired_folder,
            api_key=test_api_key,
            classification_criteria=test_criteria,
            merging_strategy=test_strategy,
            log_callback=print
        )

        if success:
            print("\n--- Step 2/3 Processor 測試執行完畢 (可能包含警告) ---")
        else:
            print("\n--- Step 2/3 Processor 測試執行過程中發生錯誤 ---") 