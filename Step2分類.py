import os
import json
import requests
import re # 用於從文字中提取影片長度
import docx # 導入docx處理庫

# Gemini API Endpoint (模型可以根據需求調整)
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-pro-exp-02-05:generateContent?key={api_key}"
HEADERS = {"Content-Type": "application/json"}

# --- Prompts for Gemini ---
PROMPT_ORIGINAL = """
請根據以下內容進行分類。內容包含影片資訊和轉錄文字：
{transcription}

請依據影片的文字內容及影片長度資訊進行分類，除了影片長度以外，其他的你要根據影片文字稿的內容自行判斷並分類(不用特別嚴格)，並僅回傳一個分類結果，格式必須嚴格遵守如下格式：
分類1: 影片有教學，但影片長度不足2分鐘
分類2: 影片有教學（內容完整，可獨立使用）
分類3: 示範/播放輔助影片且影片長度超過2分鐘
分類4: 示範/播放輔助影片且影片長度不超過2分鐘

請只回傳以上其中一個分類結果，且必須包含分類號碼，例如 "分類2: 影片有教學（內容完整，可獨立使用）"。不要包含其他多餘的說明。
"""

PROMPT_TOPIC = """
請仔細閱讀以下影片轉錄內容，判斷其主要內容主題。
內容包含影片資訊和轉錄文字：
{transcription}

請總結出一個簡短且能代表核心內容的主題標籤（例如："銷售技巧入門"、"冥想引導"、"產品開箱評測 - XXX型號"、"市場趨勢分析" 等）。
請只回傳主題標籤本身，不要包含任何其他說明或前綴文字。
"""

# --- Helper Functions ---

def read_docx(filepath, log_callback):
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
            return read_docx(filepath, log_callback)
        else:
            log_callback(f"【警告】不支援的檔案類型，將跳過: {os.path.basename(filepath)}")
            return None
    except Exception as e:
        log_callback(f"【錯誤】讀取檔案失敗 {os.path.basename(filepath)}: {e}")
        return None

def extract_duration_from_text(text):
    """從文字內容中提取影片長度 (秒)"""
    # 尋找 "影片長度：... 秒" 格式
    match = re.search(r"影片長度：\s*([\d.]+)\s*秒", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def call_gemini_api(api_key, prompt_text, log_callback):
    """呼叫 Gemini API 並處理回應"""
    if not api_key:
        log_callback("【錯誤】未提供 Gemini API 金鑰。")
        return None

    endpoint = GEMINI_API_ENDPOINT.format(api_key=api_key)
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

    try:
        log_callback("【日誌】呼叫 Gemini API 中...")
        response = requests.post(endpoint, headers=HEADERS, data=json.dumps(payload), timeout=60) # 增加超時設定

        if response.status_code == 403:
             log_callback("【錯誤】Gemini API 金鑰無效或權限不足。請檢查您的 API 金鑰設定。")
             return None
        elif response.status_code != 200:
            log_callback(f"【錯誤】API 回傳狀態碼 {response.status_code}: {response.text}")
            return None

        response_json = response.json()
        candidates = response_json.get("candidates", [])

        if not candidates:
            # 有時 API 成功但可能因內容政策等原因沒有 candidates
            finish_reason = response_json.get("promptFeedback", {}).get("blockReason")
            if finish_reason:
                 log_callback(f"【警告】API 回應缺少內容，原因: {finish_reason}")
            else:
                log_callback(f"【錯誤】API 回傳結果中沒有候選資料：{response_json}")
            return None

        # 解析日誌資訊 (可選)
        usage = response_json.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", "N/A")
        candidate_tokens = usage.get("candidatesTokenCount", "N/A")
        log_callback(f"【日誌】API 使用量 - 提示 tokens: {prompt_tokens}, 回應 tokens: {candidate_tokens}")

        candidate_content = candidates[0].get("content", {})
        parts = candidate_content.get("parts", [])
        if not parts or not parts[0].get("text", "").strip():
            finish_reason = candidates[0].get("finishReason", "N/A")
            log_callback(f"【錯誤】API 回傳結果中分類文字為空。完成原因: {finish_reason}")
            return None

        result_text = parts[0].get("text", "").strip()
        log_callback(f"【日誌】取得 API 分類/主題結果：{result_text}")
        return result_text

    except requests.exceptions.RequestException as e:
        log_callback(f"【錯誤】呼叫 API 時網路連線錯誤：{e}")
        return None
    except Exception as e:
        log_callback(f"【錯誤】呼叫 API 或解析回應時發生未知錯誤：{e}")
        return None


def generate_url_config(processed_files_info, config_path, log_callback):
    """生成或更新包含已分類影片的 URL 配置 JSON 檔案"""
    existing_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
            log_callback(f"【日誌】已讀取現有 URL 配置檔案，包含 {len(existing_config)} 個影片")
        except Exception as e:
            log_callback(f"【警告】讀取現有 URL 配置檔案失敗: {e}，將創建新檔案")

    new_entries = 0
    updated_entries = 0
    for file_info in processed_files_info:
        video_name = file_info["name"]
        category = file_info["category"]

        if video_name not in existing_config:
            existing_config[video_name] = {
                "url": "",
                "category": category,
                "processed": False # 標記 Step 4 是否處理過
            }
            new_entries += 1
        elif existing_config[video_name]["category"] != category:
             # 如果檔案已存在但分類變了，更新分類
             existing_config[video_name]["category"] = category
             existing_config[video_name]["processed"] = False # 分類變了，重新標記為未處理
             updated_entries +=1

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, ensure_ascii=False, indent=2)
        log_callback(f"【日誌】URL 配置檔案已更新/儲存至 {config_path} (新增 {new_entries}，更新 {updated_entries}，總共 {len(existing_config)})")
        if new_entries > 0:
            log_callback("【提示】請記得為新加入的影片手動編輯 URL")
    except Exception as e:
         log_callback(f"【錯誤】儲存 URL 配置檔案失敗: {e}")

# --- Main Classification Function ---
def perform_classification(transcription_folder, label_folder, url_config_path, api_key, classification_criteria, log_callback=print):
    """
    執行轉錄稿的分類。

    Args:
        transcription_folder (str): 包含轉錄稿 (.txt, .docx) 的資料夾。
        label_folder (str): 儲存 labels.json 的資料夾。
        url_config_path (str): video_urls.json 的完整路徑。
        api_key (str): Gemini API 金鑰 (如果選擇的條件需要)。
        classification_criteria (str): 分類條件選項。
        log_callback (callable): 日誌回呼函數。

    Returns:
        dict: 包含 {filename: classification_result} 的字典，如果成功。
              如果發生嚴重錯誤則回傳 None。
    """
    log_callback(f"--- 開始執行分類 (條件: {classification_criteria}) ---")
    log_callback(f"讀取轉錄稿來源: {transcription_folder}")

    if not os.path.isdir(transcription_folder):
        log_callback(f"【錯誤】轉錄稿資料夾不存在: {transcription_folder}")
        return None

    os.makedirs(label_folder, exist_ok=True) # 確保標籤輸出目錄存在
    labels_output_path = os.path.join(label_folder, "labels.json")

    labels_dict = {}
    processed_files_info = [] # 用於生成 URL 配置
    needs_api = classification_criteria in ["教學/示範 & 長度 (需 API)", "主要內容主題 (需 API)"]

    if needs_api and not api_key:
         log_callback("【錯誤】選擇的分類條件需要 API 金鑰，但未提供。")
         return None

    files_to_process = [f for f in os.listdir(transcription_folder) if f.lower().endswith((".txt", ".docx"))]
    total_files = len(files_to_process)
    log_callback(f"【日誌】找到 {total_files} 個轉錄檔案，開始處理...")

    for idx, filename in enumerate(files_to_process, start=1):
        file_path = os.path.join(transcription_folder, filename)
        log_callback(f"\n====== 處理檔案 {idx}/{total_files}：{filename} ======")

        content = read_file_content(file_path, log_callback)
        if content is None:
            continue # 讀取失敗，跳過

        classification_result = "分類失敗" # 預設值

        # --- 根據條件進行分類 ---
        if classification_criteria == "影片長度 (無需 API)":
            duration = extract_duration_from_text(content)
            if duration is not None:
                if duration < 120:
                    classification_result = "長度<2分鐘"
                else:
                    classification_result = "長度>=2分鐘"
                log_callback(f"【日誌】根據影片長度 ({duration:.2f} 秒) 分類為: {classification_result}")
            else:
                log_callback(f"【警告】無法從檔案內容提取影片長度，無法進行基於長度的分類。")
                classification_result = "長度未知"

        elif needs_api:
            if classification_criteria == "教學/示範 & 長度 (需 API)":
                prompt_text = PROMPT_ORIGINAL.format(transcription=content)
            elif classification_criteria == "主要內容主題 (需 API)":
                prompt_text = PROMPT_TOPIC.format(transcription=content)
            else: # 未知的 API 類型 (理論上不應發生)
                 log_callback(f"【錯誤】未知的 API 分類條件: {classification_criteria}")
                 continue

            api_result = call_gemini_api(api_key, prompt_text, log_callback)
            if api_result is not None:
                classification_result = api_result
            else:
                # API 呼叫失敗或結果為空，保留 "分類失敗"
                pass
        else:
             log_callback(f"【錯誤】未知的分類條件: {classification_criteria}")
             continue # 跳過這個檔案

        # --- 儲存結果 ---
        labels_dict[filename] = classification_result
        video_name = os.path.splitext(filename)[0]
        processed_files_info.append({
            "name": video_name,
            "category": classification_result
        })

    # --- 分類循環結束 ---

    # 儲存分類標籤到 labels.json
    try:
        with open(labels_output_path, "w", encoding="utf-8") as f:
            json.dump(labels_dict, f, ensure_ascii=False, indent=2)
        log_callback(f"\n【日誌】已將分類標籤儲存至：{labels_output_path}")
    except Exception as e:
        log_callback(f"【錯誤】儲存分類標籤至檔案時失敗：{e}")
        # 即使儲存失敗，我們仍然可以回傳記憶體中的 labels_dict 供合併使用

    # 生成/更新 URL 配置檔案
    generate_url_config(processed_files_info, url_config_path, log_callback)

    log_callback(f"--- 分類處理完成 ---")
    return labels_dict


# --- 可選：允許腳本獨立執行 (用於測試) ---
if __name__ == "__main__":
    # --- 測試設定 ---
    test_transcription_folder = r"G:\我的雲端硬碟\自動化生成文案\Transcriptions" # 輸入
    test_label_folder = r"G:\我的雲端硬碟\自動化生成文案\Label_test"          # 輸出 label.json 的目錄
    test_url_config_path = r"G:\我的雲端硬碟\自動化生成文案\video_urls_test.json" # 輸出 video_urls.json 的完整路徑
    test_api_key = "YOUR_API_KEY" # <--- 在這裡填入您的測試 API 金鑰 (或從環境變數讀取)

    os.makedirs(test_label_folder, exist_ok=True)

    # --- 選擇要測試的分類條件 ---
    # criteria_to_test = "教學/示範 & 長度 (需 API)"
    # criteria_to_test = "主要內容主題 (需 API)"
    criteria_to_test = "影片長度 (無需 API)"

    print(f"\n** 正在以獨立模式執行 Step2 分類測試 **")
    print(f"測試分類條件: {criteria_to_test}")
    print(f"測試轉錄稿來源: {test_transcription_folder}")
    print(f"測試標籤輸出目錄: {test_label_folder}")
    print(f"測試 URL 設定檔路徑: {test_url_config_path}")

    if "API" in criteria_to_test and test_api_key == "YOUR_API_KEY":
         print("\n!!警告!! 測試需要 API 金鑰，請在程式碼中設定 test_api_key")
    else:
        # 使用 print 作為回呼函數進行測試
        result = perform_classification(
            transcription_folder=test_transcription_folder,
            label_folder=test_label_folder,
            url_config_path=test_url_config_path,
            api_key=test_api_key,
            classification_criteria=criteria_to_test,
            log_callback=print
        )

        if result is not None:
             print("\n測試分類結果 (部分):")
             count = 0
             for filename, label in result.items():
                 print(f"- {filename}: {label}")
                 count += 1
                 if count >= 5: # 只顯示前 5 個
                     break
             print(f"(總共 {len(result)} 個檔案)")
        else:
             print("\n測試執行分類時發生錯誤。")