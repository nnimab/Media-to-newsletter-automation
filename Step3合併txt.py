import os
import json
import shutil
from collections import defaultdict
import re # 需要 re
import docx # 導入docx處理庫 (如果需要讀取)

# 設定各資料夾路徑 (修正轉義序列問題，使用原始字串r或雙反斜線)
transcription_folder = r'G:\我的雲端硬碟\自動化生成文案\Transcriptions'
output_queue_folder = r'G:\我的雲端硬碟\自動化生成文案\待轉文案'
unpaired_folder = r'G:\我的雲端硬碟\自動化生成文案\漏單'
labels_file = r'G:\我的雲端硬碟\自動化生成文案\label\labels.json'

# --- Helper Functions (與 Step2 共用，也可獨立定義或匯入) ---
def read_docx_content(filepath, log_callback):
    """讀取docx檔案內容"""
    try:
        doc = docx.Document(filepath)
        full_text = [para.text for para in doc.paragraphs]
        return '\n'.join(full_text)
    except Exception as e:
        log_callback(f"【錯誤】讀取 DOCX 檔案失敗 {os.path.basename(filepath)}: {e}")
        return None

def read_file_content(filepath, log_callback):
    """通用檔案讀取函數 (支援 txt 和 docx)"""
    try:
        if filepath.lower().endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        elif filepath.lower().endswith('.docx'):
            return read_docx_content(filepath, log_callback) # 使用上面的函數
        else:
            # 在合併階段通常不應有其他類型，但以防萬一
            log_callback(f"【警告】讀取時遇到不支援的檔案類型: {os.path.basename(filepath)}")
            return None
    except Exception as e:
        log_callback(f"【錯誤】讀取檔案內容失敗 {os.path.basename(filepath)}: {e}")
        return None

def sanitize_filename(name):
    """移除或替換不適用於檔案名稱的字元"""
    # 移除常見的非法字元: < > : " / \ | ? *
    # 將空格替換成底線
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    # 避免檔名過長 (可選)
    return name[:100] # 限制長度

# --- Main Merging Function ---
def perform_merging(labels_dict, transcription_folder, output_queue_folder, unpaired_folder, merging_strategy, log_callback=print):
    """
    根據分類結果和合併策略執行檔案合併。

    Args:
        labels_dict (dict): {filename: classification_result} 分類結果字典。
        transcription_folder (str): 包含原始轉錄稿的資料夾。
        output_queue_folder (str): 儲存合併後 (或未合併) 檔案的資料夾。
        unpaired_folder (str): 儲存 \"兩兩配對\" 模式下漏單檔案的資料夾。
        merging_strategy (str): 合併策略選項。
        log_callback (callable): 日誌回呼函數。

    Returns:
        bool: True 如果處理過程沒有發生嚴重錯誤，False 如果有。
    """
    log_callback(f"--- 開始執行合併 (策略: {merging_strategy}) ---")
    log_callback(f"讀取原始檔案來源: {transcription_folder}")
    log_callback(f"合併/輸出檔案至: {output_queue_folder}")
    if merging_strategy == "兩兩配對 (僅適用原始分類)":
        log_callback(f"漏單檔案輸出至: {unpaired_folder}")

    # 確保輸出資料夾存在
    os.makedirs(output_queue_folder, exist_ok=True)
    os.makedirs(unpaired_folder, exist_ok=True) # 即使不用也確保存在

    if not labels_dict:
        log_callback("【警告】沒有有效的分類結果可供合併。")
        # 如果沒有分類結果，是否直接複製所有檔案？ (視為\"不合併\")
        # 這裡暫定為不執行任何操作
        return True # 沒有錯誤，只是沒事做

    success = True # 追蹤是否有錯誤發生

    # --- 根據策略執行 ---
    if merging_strategy == "不合併":
        log_callback("【日誌】策略為 '不合併'，將直接複製所有檔案至輸出佇列...")
        copied_count = 0
        error_count = 0
        for filename in labels_dict.keys(): # 遍歷所有被分類的檔案
            src_path = os.path.join(transcription_folder, filename)
            base_name = os.path.splitext(filename)[0]
            dest_filename = f"{base_name}.txt" # 統一輸出為 txt
            dest_path = os.path.join(output_queue_folder, dest_filename)

            try:
                content = read_file_content(src_path, log_callback)
                if content is not None:
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    copied_count += 1
                else:
                     error_count += 1 # 讀取失敗
            except Exception as e:
                log_callback(f"【錯誤】複製/寫入檔案失敗 {filename} -> {dest_filename}: {e}")
                error_count += 1
                success = False
        log_callback(f"【日誌】'不合併' 處理完成。成功複製: {copied_count}, 失敗: {error_count}")

    elif merging_strategy == "依據分類合併":
        log_callback("【日誌】策略為 '依據分類合併'...")
        # 按分類標籤將檔案分組
        files_by_category = defaultdict(list)
        for filename, category in labels_dict.items():
            files_by_category[category].append(filename)

        merged_count = 0
        error_count = 0
        log_callback(f"【日誌】共找到 {len(files_by_category)} 個分類標籤進行合併。")

        for category, filenames in files_by_category.items():
            if not filenames: continue

            # 清理分類名稱作為檔名
            safe_category_name = sanitize_filename(category)
            merged_filename = f"合併_{safe_category_name}.txt"
            dest_path = os.path.join(output_queue_folder, merged_filename)
            log_callback(f"--- 合併分類: '{category}' (共 {len(filenames)} 個檔案) -> {merged_filename} ---")

            merged_content_parts = [f"===== 合併分類: {category} ====="]
            files_processed_in_group = 0

            filenames.sort() # 在合併前排序檔案
            for filename in filenames:
                src_path = os.path.join(transcription_folder, filename)
                content = read_file_content(src_path, log_callback)
                if content is not None:
                    header = f"\n\n----- 來源檔案: {filename} -----\n"
                    merged_content_parts.append(header + content)
                    files_processed_in_group += 1
                else:
                    log_callback(f"【警告】讀取檔案 {filename} 失敗，將從合併中排除。")
                    success = False # 標記有非嚴重錯誤

            # 將所有部分合併並寫入檔案
            if len(merged_content_parts) > 1: # 如果至少有一個檔案讀取成功 (除了標題)
                try:
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write("\n".join(merged_content_parts))
                    log_callback(f"【日誌】分類 '{category}' 已合併並儲存。")
                    merged_count += 1
                except Exception as e:
                    log_callback(f"【錯誤】寫入合併檔案 {merged_filename} 失敗: {e}")
                    error_count += 1
                    success = False
            else:
                 log_callback(f"【警告】分類 '{category}' 中的所有檔案都讀取失敗，未生成合併檔案。")
                 error_count += 1 # 雖然沒寫檔，但視為錯誤
                 success = False

        log_callback(f"【日誌】'依據分類合併' 處理完成。成功合併: {merged_count} 個分類, 發生錯誤/警告: {error_count} 次。")


    elif merging_strategy == "兩兩配對 (僅適用原始分類)":
        log_callback("【日誌】策略為 '兩兩配對 (僅適用原始分類)'...")
        # --- 沿用您原始 Step 3 的邏輯 ---
        independent_files = []
        paired_files = []
        for filename, classification in labels_dict.items():
            # 假設原始分類2是獨立的
            if classification.strip().startswith("分類2:"):
                 independent_files.append(filename)
            else:
                paired_files.append(filename)

        independent_files.sort()
        paired_files.sort()

        log_callback(f"【日誌】獨立使用檔案數量: {len(independent_files)}")
        log_callback(f"【日誌】需要配對檔案數量: {len(paired_files)}")

        processed_count = 0
        error_count = 0

        # 1. 處理獨立檔案
        for filename in independent_files:
            src_path = os.path.join(transcription_folder, filename)
            base_name = os.path.splitext(filename)[0]
            txt_filename = f"{base_name}.txt"
            dest_path = os.path.join(output_queue_folder, txt_filename)
            try:
                content = read_file_content(src_path, log_callback)
                if content is not None:
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    log_callback(f"【日誌】處理獨立檔案並儲存為 txt：{filename} -> {txt_filename}")
                    processed_count += 1
                else:
                     error_count += 1; success = False
            except Exception as e:
                log_callback(f"【錯誤】處理獨立檔案 {filename} 失敗: {e}")
                error_count += 1; success = False

        # 2. 處理需配對檔案
        separator = "\n\n===== 分割線 =====\n\n"
        num_paired = len(paired_files)
        i = 0
        while i < num_paired:
            # 漏單處理
            if i == num_paired - 1:
                leftover_filename = paired_files[i]
                src_path = os.path.join(transcription_folder, leftover_filename)
                base_name = os.path.splitext(leftover_filename)[0]
                txt_filename = f"{base_name}.txt"
                dest_path = os.path.join(unpaired_folder, txt_filename)
                try:
                    content = read_file_content(src_path, log_callback)
                    if content is not None:
                        with open(dest_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        log_callback(f"【日誌】將漏單檔案處理並儲存為 txt 至漏單資料夾：{leftover_filename} -> {txt_filename}")
                        processed_count += 1 # 也算處理成功
                    else:
                        error_count += 1; success = False
                except Exception as e:
                    log_callback(f"【錯誤】處理漏單檔案 {leftover_filename} 失敗: {e}")
                    error_count += 1; success = False
                break # 結束 while 循環

            # 配對處理
            file1 = paired_files[i]
            file2 = paired_files[i+1]
            src_path1 = os.path.join(transcription_folder, file1)
            src_path2 = os.path.join(transcription_folder, file2)
            content1, content2 = None, None
            try:
                content1 = read_file_content(src_path1, log_callback)
                content2 = read_file_content(src_path2, log_callback)
            except Exception as e: # 這裡其實 read_file_content 內部會處理，但多一層保險
                 log_callback(f"【錯誤】讀取配對檔案失敗: {file1} 或 {file2}: {e}")
                 error_count += 2; success = False
                 i += 2
                 continue

            if content1 is None or content2 is None:
                log_callback(f"【警告】讀取配對檔案 {file1} 或 {file2} 內容失敗，跳過此配對。")
                error_count += (1 if content1 is None else 0) + (1 if content2 is None else 0)
                success = False
                i += 2
                continue

            header = f"來源檔案：{file1}, {file2}\n\n"
            merged_content = header + content1 + separator + content2
            base1 = os.path.splitext(file1)[0]
            base2 = os.path.splitext(file2)[0]
            merged_filename = f"{base1}+{base2}.txt"
            dest_path = os.path.join(output_queue_folder, merged_filename)
            try:
                with open(dest_path, 'w', encoding='utf-8') as out_f:
                    out_f.write(merged_content)
                log_callback(f"【日誌】成功合併檔案：{merged_filename}")
                processed_count += 1 # 合併算一次成功
            except Exception as e:
                log_callback(f"【錯誤】寫入合併檔案 {merged_filename} 失敗: {e}")
                error_count += 1; success = False
            i += 2
        log_callback(f"【日誌】'兩兩配對' 處理完成。成功處理/合併: {processed_count} 次, 發生錯誤/警告: {error_count} 次。")


    else:
        log_callback(f"【錯誤】未知的合併策略: {merging_strategy}")
        success = False

    log_callback(f"--- 合併處理完成 ---")
    return success


# --- 可選：允許腳本獨立執行 (用於測試) ---
if __name__ == "__main__":
    import re # 需要 re 來 sanitize

    # --- 測試設定 ---
    # 假設 labels_test.json 是由 Step 2 測試產生的
    test_labels_path = r"G:\我的雲端硬碟\自動化生成文案\Label_test\labels.json"
    test_transcription_folder = r"G:\我的雲端硬碟\自動化生成文案\Transcriptions"
    test_output_queue_folder = r"G:\我的雲端硬碟\自動化生成文案\待轉文案_test"
    test_unpaired_folder = r"G:\我的雲端硬碟\自動化生成文案\漏單_test"

    os.makedirs(test_output_queue_folder, exist_ok=True)
    os.makedirs(test_unpaired_folder, exist_ok=True)

    # --- 讀取測試標籤 ---
    test_labels = {}
    try:
        with open(test_labels_path, 'r', encoding='utf-8') as f:
            test_labels = json.load(f)
        print(f"成功讀取測試標籤檔案: {test_labels_path} ({len(test_labels)} 個項目)")
    except Exception as e:
        print(f"讀取測試標籤檔案失敗: {e}")
        test_labels = {} # 使用空字典繼續

    if not test_labels:
        print("沒有標籤資料，無法執行合併測試。")
    else:
        # --- 選擇要測試的合併策略 ---
        # strategy_to_test = "不合併"
        strategy_to_test = "依據分類合併"
        # strategy_to_test = "兩兩配對 (僅適用原始分類)" # 需確保 labels.json 內容是原始分類格式

        print(f"\n** 正在以獨立模式執行 Step3 合併測試 **")
        print(f"測試合併策略: {strategy_to_test}")
        print(f"測試轉錄稿來源: {test_transcription_folder}")
        print(f"測試輸出佇列: {test_output_queue_folder}")
        if strategy_to_test == "兩兩配對 (僅適用原始分類)":
             print(f"測試漏單資料夾: {test_unpaired_folder}")

        # 使用 print 作為回呼函數進行測試
        success = perform_merging(
            labels_dict=test_labels,
            transcription_folder=test_transcription_folder,
            output_queue_folder=test_output_queue_folder,
            unpaired_folder=test_unpaired_folder,
            merging_strategy=strategy_to_test,
            log_callback=print
        )

        if success:
            print("\n合併測試執行完畢 (可能包含非嚴重警告，請檢查日誌)。")
        else:
            print("\n合併測試執行過程中發生錯誤。")

        print(f"\n請檢查輸出資料夾：")
        print(f"- 合併/複製結果: {test_output_queue_folder}")
        if strategy_to_test == "兩兩配對 (僅適用原始分類)":
            print(f"- 漏單檔案: {test_unpaired_folder}")