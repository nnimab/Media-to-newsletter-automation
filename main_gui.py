import customtkinter as ctk
import tkinter as tk # 需要 tkinter 來使用 filedialog
from tkinter import filedialog, Toplevel # <-- 新增 Toplevel
import os
import threading # <--- 新增：匯入 threading 模組
import glob # <--- 新增：用於尋找模板檔案
import json # 需要 json 來儲存/載入 Prompt
import traceback # <-- 新增：為了更詳細的錯誤輸出
# ---- 匯入我們修改後的 Step 1 處理函數 ----
try:
    from Step1影音轉文字 import process_videos
    step1_available = True
except Exception as e: # <-- 改成捕捉所有 Exception
    step1_available = False
    print(f"【嚴重錯誤】載入 Step1 模組時發生錯誤: {e}") # <-- 印出具體錯誤
    print(traceback.format_exc()) # <-- 印出詳細錯誤追蹤
    # 如果匯入失敗，稍後在 log_message 中提示
# -----------------------------------------
# ---- 匯入 Step 2/3 Processor ----
try:
    from step2_3_processor import run_classification_and_merging, step2_available, step3_available
    step2_3_processor_available = step2_available and step3_available
except ImportError:
    step2_3_processor_available = False
    step2_available = False # 確保這些變數存在
    step3_available = False
# --------------------------------
# ---- 匯入 Step 4 ----
try:
    from Step4生成電子報 import generate_newsletter
    step4_available = True
except ImportError as e:
    print(f"無法匯入 Step4生成電子報: {e}")
    step4_available = False
# --------------------

# --- 檢查目錄結構和設定檔 ---
# 確保 templates 資料夾存在
templates_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
if not os.path.exists(templates_folder):
    os.makedirs(templates_folder)

# 設定檔路徑
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_settings.json")

# --- 獲取預設輸出資料夾 ---
def get_default_output_folder():
    """獲取預設的輸出資料夾，優先使用文檔路徑"""
    # 按優先順序查找可用的文檔目錄
    possible_docs = [
        os.path.join(os.path.expanduser("~"), "Documents", "電子報生成工具輸出"),
        os.path.join(os.path.expanduser("~"), "電子報生成工具輸出"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    ]
    
    for folder in possible_docs:
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
            return folder
        except:
            continue
    
    # 如果找不到合適的路徑，就用當前腳本路徑下的 output 資料夾
    default_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    if not os.path.exists(default_folder):
        os.makedirs(default_folder)
    return default_folder

# --- 預設路徑設定 ---
default_output_folder = get_default_output_folder()

# 基礎資料夾 (統一使用中文命名)
default_paths = {
    "video_input": os.path.join(default_output_folder, "影片資料夾"),
    "transcription_output": os.path.join(default_output_folder, "轉錄文字"),
    "label_output": os.path.join(default_output_folder, "分類標籤"),
    "queue_output": os.path.join(default_output_folder, "待處理文件"),
    "final_output": os.path.join(default_output_folder, "成品輸出"),
    "unpaired_output": os.path.join(default_output_folder, "未配對文件")
}

# URL 設定檔預設路徑
default_paths["url_config"] = os.path.join(default_output_folder, "影片網址.json")

# 確保這些資料夾存在
for path in default_paths.values():
    if ".json" not in path:  # 跳過 .json 檔案
        os.makedirs(path, exist_ok=True)

# 預設 HTML 模板 (查詢第一個可用的模板)
default_template_path = os.path.join(templates_folder, "範例模板.html")
if not os.path.exists(default_template_path):
    # 如果預設模板不存在，嘗試找第一個 .html 或留空
    found_templates = glob.glob(os.path.join(templates_folder, "*.html"))
    if found_templates:
        default_template_path = found_templates[0]
    else:
        default_template_path = "" # 留空，讓使用者選擇

# 將模板路徑加入 default_paths
default_paths["html_template"] = default_template_path

# --- 讀取或創建應用程式設定 ---
def load_settings():
    """從檔案讀取設定，如果檔案不存在則使用默認設定"""
    # --- 新增：模板自訂內容的預設值 ---
    default_template_customizations = {
        "logo_url": "",
        "seminar_title": "",
        "seminar_description": "",
        "seminar_button_text": "",
        "seminar_url": "",
        "course_section_title": "關注我們最新的課程資訊",
        "course_image_url": "https://us-ms.gr-cdn.com/getresponse-ISWeb/photos/97bbb3d8-cd8a-4a9f-bb3b-c52f8b8c9630.png",
        "course_title": "美國NGH催眠師證照班+高級班",
        "course_image_alt": "美國NGH催眠師證照班",
        "course_description": "",
        "courses_button_text": "",
        "courses_button_url": "",
        "footer_address": "Morningstar Chen Xing INC., 台北市中山區雙城街4巷2號7樓705室, 104, Taipei, Taiwan ROC"
    }
    # ------------------------------------
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
                
                # 合併預設路徑和保存的設定
                # 這樣如果設定檔中缺少某些設定，會從預設值補上
                # --- 修改：加入 template_customizations 的預設值 ---
                settings = {
                    **default_paths,
                    "api_key": "",
                    "api_model": "gemini-2.0-flash",
                    "template_customizations": default_template_customizations # 加入預設模板設定
                }
                settings.update(saved_settings)
                
                print(f"【系統】成功載入配置文件：{CONFIG_FILE_PATH}")
                return settings
        except Exception as e:
            print(f"【錯誤】讀取配置文件失敗: {e}，將使用預設配置")
            # 如果讀取失敗，使用預設配置
            
    # 預設配置
    # --- 修改：加入 template_customizations 的預設值 ---
    settings = {
        "api_key": "",
        "api_model": "gemini-2.0-flash",
        **default_paths,
        "template_customizations": default_template_customizations # 加入預設模板設定
    }
    return settings

def save_settings(settings_dict):
    """將設定儲存到檔案"""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, ensure_ascii=False, indent=4)
        print(f"【系統】配置已儲存至：{CONFIG_FILE_PATH}")
        return True
    except Exception as e:
        print(f"【錯誤】儲存配置失敗: {e}")
        return False

# 載入應用程式設定
app_settings = load_settings()

# --- GUI 設定 ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("電子報文章生成工具")
# app.geometry("800x950") # 初始大小先移除，讓 pack 自動調整，後面再設定最終大小

# --- Variables ---
# 分類與合併選項
classification_options = [
    "教學/示範 & 長度 (需 API)",
    "主要內容主題 (需 API)",
    "影片長度 (無需 API)"
]
merging_options = [
    "兩兩配對 (僅適用原始分類)",
    "依據分類合併",
    "不合併"
]
# 用於儲存下拉選單的變數
classification_var = tk.StringVar(value=classification_options[0])
merging_var = tk.StringVar(value=merging_options[1]) # 預設"依據分類合併"

# --- 新增：預設 Prompt 模板 ---
DEFAULT_PROMPTS = {
    "僅填入原文": "{original_content}", # 特殊標記，表示不呼叫 API
    "摘要重點": """請根據以下影片轉錄內容（可能包含原始檔名、影片長度和轉錄文字），提取核心要點並生成一段簡潔的摘要。摘要應包含最重要的資訊，適合放在電子報的開頭。
內容：
{original_content}

摘要：
""",
    "改寫成文章": """請將以下影片轉錄內容（可能包含原始檔名、影片長度和轉錄文字）改寫成一篇流暢、易於閱讀的電子報教學，請務必要包含多個小標題，內文，以及結尾。請保留核心資訊和教學內容（如果有），但用更自然的語氣書寫，輸出請直接給我內文，不要有任何的回復姓語言例如:
好的，這是一篇根據您提供的轉錄內容改寫的電子報文章段落等等。
內容：
{original_content}

改寫後的文章段落：
""",
    "自訂 Prompt": "" # 留空給使用者
}
prompt_options = list(DEFAULT_PROMPTS.keys())

# --- Variables ---
# ... (之前的 Variables) ...
prompt_template_var = tk.StringVar(value=prompt_options[2]) # 預設選"改寫成文章"
custom_prompt_path = tk.StringVar(value="") # 儲存自訂 prompt 檔案路徑

# --- Global variable for settings window to prevent multiple openings ---
settings_window = None
settings_entries = {} # Store entry widgets for the general settings window
template_settings_window = None # Global variable for template settings window
template_settings_entries = {} # Store entry widgets for the template settings window

# --- Global variables for log window ---
log_window = None
log_textbox = None # Make log_textbox global so it can be accessed by _update_log_textbox
log_messages_buffer = [] # 新增訊息緩衝區，用於儲存日誌視窗尚未打開時的訊息

# --- Functions ---
def select_folder(entry_widget: ctk.CTkEntry):
    """開啟資料夾選擇對話框並更新 Entry 元件"""
    # 使用 entry 元件目前的父目錄作為初始目錄，如果有效的話
    initial_dir = os.path.dirname(entry_widget.get()) if entry_widget.get() and os.path.isdir(os.path.dirname(entry_widget.get())) else None
    folder_selected = filedialog.askdirectory(initialdir=initial_dir)
    if folder_selected: # 如果使用者選擇了資料夾
        entry_widget.delete(0, tk.END) # 清除現有內容
        entry_widget.insert(0, folder_selected) # 插入新路徑

def select_file(entry_widget: ctk.CTkEntry):
    """開啟檔案儲存/選擇對話框並更新 Entry 元件 (用於 URL 設定檔)"""
    # 使用 entry 元件目前的父目錄作為初始目錄，如果有效的話
    initial_dir = os.path.dirname(entry_widget.get()) if entry_widget.get() and os.path.isdir(os.path.dirname(entry_widget.get())) else None
    file_selected = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        initialfile=os.path.basename(entry_widget.get()), # 從現有路徑取得預設檔名
        initialdir=initial_dir
    )
    if file_selected:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, file_selected)

def select_template_file_settings(entry_widget: ctk.CTkEntry):
    """開啟 HTML 檔案選擇對話框 (用於設定視窗)"""
    initial_dir = templates_folder # 預設開啟 templates 資料夾
    current_path = entry_widget.get()
    if current_path and os.path.exists(os.path.dirname(current_path)):
        initial_dir = os.path.dirname(current_path) # 如果輸入框有有效路徑，從那裡開始

    file_selected = filedialog.askopenfilename(
        title="選擇 HTML 模板檔案",
        filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
        initialdir=initial_dir
    )
    if file_selected:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, file_selected)

def run_step1_thread():
    """在單獨執行緒中執行 Step 1 處理"""
    # Log start inside the thread as well
    log_message("--- Step 1 執行緒已啟動 ---")
    print("--- Step 1 執行緒已啟動 ---")
    try:
        # 從 app_settings 獲取路徑
        video_input_path = app_settings.get("video_input", "")
        transcription_output_path = app_settings.get("transcription_output", "")

        # 驗證路徑是否存在
        if not video_input_path or not os.path.isdir(video_input_path):
            log_message(f"【錯誤】Step 1: 影片輸入資料夾未設定或不存在: {video_input_path}")
            print(f"【錯誤】Step 1: 影片輸入資料夾未設定或不存在: {video_input_path}")
            return # 執行緒提前結束
        if not transcription_output_path or not os.path.isdir(transcription_output_path):
            log_message(f"【錯誤】Step 1: 轉錄輸出資料夾未設定或不存在: {transcription_output_path}")
            print(f"【錯誤】Step 1: 轉錄輸出資料夾未設定或不存在: {transcription_output_path}")
            return # 執行緒提前結束

        # --- 呼叫 Step 1 處理函數 ---
        log_message(f"【日誌】Step 1: 即將呼叫 process_videos 函數...")
        print(f"【日誌】Step 1: 即將呼叫 process_videos 函數...")
        process_videos(
            video_folder=video_input_path,
            output_folder=transcription_output_path,
            model_size="base", # 暫時使用 base 模型
            log_callback=log_message # 確保傳遞了回呼函數
        )
        log_message(f"【日誌】Step 1: process_videos 函數執行完畢 (不代表成功)。")
        print(f"【日誌】Step 1: process_videos 函數執行完畢 (不代表成功)。")

    except Exception as e:
        # 捕獲 process_videos 中未預料的錯誤，或其他執行緒內的錯誤
        error_msg = f"【嚴重錯誤】執行 Step 1 執行緒時發生未預期錯誤: {e}"
        log_message(error_msg)
        print(error_msg) # 也打印到終端
        tb_msg = traceback.format_exc()
        log_message(tb_msg) # 將 traceback 也記錄到日誌視窗
        print(tb_msg) # 同時打印 traceback 到終端
    finally:
        # 無論成功或失敗，都要重新啟用按鈕
        log_message("--- Step 1 執行緒即將結束 (finally 區塊) ---")
        print("--- Step 1 執行緒即將結束 (finally 區塊) ---")
        app.after(0, lambda: step1_button.configure(state="normal", text="Step 1: 影音轉文字"))
        log_message("--- Step 1 執行緒結束 --- (按鈕已重設)")
        print("--- Step 1 執行緒結束 --- (按鈕已重設)")

def run_step1():
    # --- 在函數最開頭加入日誌 ---
    log_message("--- run_step1 函數被觸發 --- (準備啟動執行緒)")
    print("--- run_step1 函數被觸發 --- (準備啟動執行緒)")
    # ---------------------------

    log_message("準備啟動 Step 1: 影音轉文字 (背景執行)...")

    if not step1_available:
         log_message("【錯誤】無法找到 Step1 處理模組 (Step1影音轉文字.py)。")
         print("【錯誤】無法找到 Step1 處理模組 (Step1影音轉文字.py)。")
         return

    step1_button.configure(state="disabled", text="執行中...")
    log_message("【日誌】Step 1 按鈕已禁用，文字已更改。")
    print("【日誌】Step 1 按鈕已禁用，文字已更改。")
    thread = threading.Thread(target=run_step1_thread, daemon=True)
    thread.start()
    log_message("【日誌】Step 1 背景執行緒已啟動。")
    print("【日誌】Step 1 背景執行緒已啟動。")

def run_step2_3_thread():
    """在單獨執行緒中執行 Step 2/3 處理"""
    try:
        # 獲取選擇的條件和方案
        selected_classification = classification_var.get()
        selected_merging = merging_var.get()
        log_message(f"--- 開始 Step 2/3 流程 (背景執行) ---")
        log_message(f"選擇的分類條件: {selected_classification}")
        log_message(f"選擇的合併方案: {selected_merging}")

        # --- 從 app_settings 獲取參數 ---
        transcription_input_path = app_settings.get("transcription_output", "")
        label_output_path = app_settings.get("label_output", "")
        url_config_file_path = app_settings.get("url_config", "")
        queue_output_path = app_settings.get("queue_output", "")
        unpaired_output_path = app_settings.get("unpaired_output", "")
        api_key_value = app_settings.get("api_key", "")

        # --- 基本驗證 ---
        if not transcription_input_path or not os.path.isdir(transcription_input_path):
             log_message(f"【錯誤】Step 2/3: 轉錄輸入資料夾未設定或不存在: {transcription_input_path}")
             return
        if not label_output_path or not os.path.isdir(label_output_path):
             log_message(f"【錯誤】Step 2/3: 標籤檔儲存資料夾未設定或不存在: {label_output_path}")
             return
        if not queue_output_path or not os.path.isdir(queue_output_path):
             log_message(f"【錯誤】Step 2/3: 待轉文案輸出資料夾未設定或不存在: {queue_output_path}")
             return
        if not unpaired_output_path or not os.path.isdir(unpaired_output_path):
             log_message(f"【警告】Step 2/3: 漏單資料夾未設定或不存在: {unpaired_output_path}")
             # 漏單資料夾不存在通常不阻止流程，僅記錄警告
             # return
        # 檢查 URL 設定檔的 *目錄* 是否存在
        if not url_config_file_path:
            log_message("【錯誤】Step 2/3: URL 設定檔路徑未設定。")
            return
        url_config_dir = os.path.dirname(url_config_file_path)
        if not os.path.isdir(url_config_dir):
            log_message(f"【錯誤】Step 2/3: URL 設定檔所在目錄不存在: {url_config_dir}")
            return

        needs_api = selected_classification in ["教學/示範 & 長度 (需 API)", "主要內容主題 (需 API)"]
        if needs_api and not api_key_value:
            log_message("【錯誤】選擇的分類條件需要 API 金鑰，但未在設定中提供。")
            return

        # --- 呼叫協調函數 ---
        success = run_classification_and_merging(
            transcription_folder=transcription_input_path,
            label_folder=label_output_path,
            url_config_path=url_config_file_path,
            output_queue_folder=queue_output_path,
            unpaired_folder=unpaired_output_path,
            api_key=api_key_value,
            classification_criteria=selected_classification,
            merging_strategy=selected_merging,
            log_callback=log_message
        )

        if success:
             log_message("--- Step 2/3 流程執行完畢 (可能包含警告，請查看日誌) ---")
        else:
             log_message("【錯誤】Step 2/3 流程執行過程中發生錯誤。 ---")

    except Exception as e:
         # 捕獲 run_classification_and_merging 中未預料的錯誤
         log_message(f"【嚴重錯誤】執行 Step 2/3 時發生未預期錯誤: {e}")
         log_message(traceback.format_exc()) # 打印詳細錯誤堆疊
    finally:
        # 無論成功或失敗，都要重新啟用按鈕
        app.after(0, lambda: step2_3_button.configure(state="normal", text="Step 2/3: 執行分類與合併"))


def run_step2_3():
    log_message("準備啟動 Step 2/3: 分類與合併 (背景執行)...")

    if not step2_3_processor_available:
        log_message("【錯誤】無法載入 Step 2 或 Step 3 處理模組，請檢查檔案是否存在且無語法錯誤。")
        log_message(f"Step 2 模組載入狀態: {'成功' if step2_available else '失敗'}")
        log_message(f"Step 3 模組載入狀態: {'成功' if step3_available else '失敗'}")
        return

    step2_3_button.configure(state="disabled", text="執行中...")
    thread = threading.Thread(target=run_step2_3_thread, daemon=True)
    thread.start()

def run_step4_thread():
    """處理執行 Step 4: 生成電子報 (背景執行緒)"""
    try:
        # 獲取所有設定
        transcription_output = app_settings.get("transcription_output", "")  # Step 1 的輸出 (常常是 Step 4 的輸入)
        queue_output = app_settings.get("queue_output", "")  # Step 2/3 的輸出 (如果啟用分類與合併)
        final_output = app_settings.get("final_output", "")
        url_config = app_settings.get("url_config", "")
        html_template = app_settings.get("html_template", "")
        api_key = app_settings.get("api_key", "")
        api_model = app_settings.get("api_model", "gemini-2.0-flash")  # 獲取模型設定，預設是 gemini-2.0-flash
        include_video = app_settings.get("include_video", True)  # 獲取是否包含影片連結設定
        # 獲取 Prompt 設定
        prompt_template_name = app_settings.get("prompt_template", "改寫成文章")  # 從 app_settings 獲取
        prompt_content = app_settings.get("prompt_content", "")  # 從 app_settings 獲取
        
        # --- 新增：獲取模板自訂設定 ---
        template_customizations = app_settings.get("template_customizations", {})
        log_message(f"【日誌】載入模板自訂設定: {template_customizations}")
        # --------------------------
        
        # 如果內容為空，使用預設模板 (這是後備機制)
        if not prompt_content and prompt_template_name in DEFAULT_PROMPTS:
            prompt_content = DEFAULT_PROMPTS[prompt_template_name]
            log_message(f"【日誌】使用預設的 '{prompt_template_name}' Prompt 模板內容。")
        
        
        # 根據是否啟用分類與合併功能選擇輸入資料夾
        input_folder = ""
        if enable_step2_3_var.get() and queue_output and os.path.isdir(queue_output):
            input_folder = queue_output
            log_message(f"【日誌】已啟用分類與合併功能，使用待轉文案資料夾作為輸入: {input_folder}")
        else:
            input_folder = transcription_output
            log_message(f"【日誌】使用轉錄輸出資料夾作為輸入: {input_folder}")
        
        # 檢查必要輸入
        if not input_folder:
            log_message("【錯誤】無法確定輸入資料夾，請檢查設定。")
            return
        
        if not os.path.exists(input_folder):
            log_message(f"【錯誤】Step 4: 輸入資料夾不存在: {input_folder}")
            return
        
        if not final_output:
            log_message("【錯誤】請先設定最終文案輸出資料夾")
            return
        
        if not html_template:
            log_message("【錯誤】請先選擇 HTML 模板檔案")
            return

        if not os.path.exists(html_template):
            log_message(f"【錯誤】HTML 模板檔案不存在: {html_template}")
            return

        if prompt_template_name != "僅填入原文" and not api_key:
            log_message("【錯誤】選擇的 Prompt 需要 API 金鑰，但未提供。")
            return

        # Step 4: 生成電子報
        log_message("準備啟動 Step 4: 生成電子報 (背景執行)...")
        log_message("--- 開始 Step 4 流程 (背景執行)：生成電子報 ---")
        log_message(f"使用輸入資料夾: {input_folder}")
        
        # 使用緩衝區系統輸出日誌
        from Step4生成電子報 import generate_newsletter
        
        # 補充說明
        # input_folder = 選擇的輸入資料夾，可能是 Step 1 或 Step 2/3 的輸出
        # final_output = 最終 HTML 檔案輸出位置
        success = generate_newsletter(
            input_folder=input_folder,
            output_folder=final_output,
            url_config_path=url_config,
            html_template_path=html_template,
            api_key=api_key,
            prompt_template_name=prompt_template_name,
            prompt_template_content=prompt_content,
            log_callback=log_message,
            api_model=api_model,  # 傳遞自定義模型參數
            include_video=include_video,  # 傳遞是否包含影片連結設定
            template_customizations=template_customizations # <-- 新增：傳遞模板自訂設定
        )

        if success:
            log_message("--- Step 4 流程執行完畢。 ---")
        else:
             log_message("【錯誤】Step 4 流程執行過程中發生錯誤。 ---")
    except Exception as e:
        log_message(f"【嚴重錯誤】執行 Step 4 時發生未預期錯誤: {str(e)}")
        log_message(traceback.format_exc())
    finally:
        # 無論成功或失敗，都要重新啟用按鈕
        app.after(0, lambda: step4_button.configure(state="normal", text="Step 4: 生成電子報"))

def run_step4():
    log_message("準備啟動 Step 4: 生成電子報 (背景執行)...")

    if not step4_available:
        log_message("【錯誤】無法載入 Step 4 處理模組 (Step4生成電子報.py)。")
        return

    step4_button.configure(state="disabled", text="執行中...")
    thread = threading.Thread(target=run_step4_thread, daemon=True)
    thread.start()

# --- Function to toggle Step 2/3 options ---
def toggle_step2_3_options():
    if enable_step2_3_var.get(): # 如果勾選了核取方塊
        step2_3_options_frame.pack(fill="x", padx=10, pady=(0, 5), before=step4_button_frame) # 顯示框架，放在 Step4 按鈕之前
    else:
        step2_3_options_frame.pack_forget() # 隱藏框架

def log_message(message):
    """將訊息添加到日誌文字框中 (確保執行緒安全)，如果日誌視窗未打開則暫存訊息"""
    # 使用 app.after 將 GUI 更新操作安排在主執行緒中執行
    global log_messages_buffer # 需要訪問全局緩衝區
    # 無論日誌視窗是否打開，都先把訊息加到緩衝區
    log_messages_buffer.append(message)
    # 如果緩衝區太大，開始移除舊訊息以防止記憶體問題
    if len(log_messages_buffer) > 1000:  # 最多保留 1000 條訊息
        log_messages_buffer = log_messages_buffer[-1000:]
    # 嘗試更新日誌視窗 (如果存在)
    app.after(0, lambda: _update_log_textbox(message))

def _update_log_textbox(message):
    """實際更新 Textbox 的內部函數 (在主執行緒執行)"""
    global log_textbox # Need to access the global log_textbox
    try:
        # 檢查 log_textbox 是否還存在 (在獨立視窗中)
        if log_textbox is not None and log_textbox.winfo_exists():
            log_textbox.configure(state="normal") # 允許編輯
            log_textbox.insert(tk.END, message + "\n") # 插入訊息
            log_textbox.see(tk.END) # 自動滾動到底部
            log_textbox.configure(state="disabled") # 設回唯讀
            # 不再需要 else 分支，因為訊息已存入緩衝區
    except Exception as e:
        # 如果在更新日誌時出錯 (例如視窗已關閉)，在控制台打印
        print(f"Error updating log textbox: {e}")

# --- 新增：Prompt 相關函數 ---
def update_prompt_textbox(*args):
    """根據下拉選單選擇更新 Prompt 文字框內容和狀態"""
    selected_prompt_name = prompt_template_var.get()
    prompt_content = DEFAULT_PROMPTS.get(selected_prompt_name, "")

    prompt_textbox.configure(state="normal") # 允許編輯
    prompt_textbox.delete("1.0", tk.END) # 清空

    if selected_prompt_name == "自訂 Prompt":
        # 如果是自訂，允許編輯，並可選擇載入之前的內容
        loaded_content = "" # 可以考慮從 custom_prompt_path 載入？或維持空白
        prompt_textbox.insert("1.0", loaded_content if loaded_content else "點擊 '載入' 或直接在此編輯您的 Prompt。使用 {original_content} 作為原文的佔位符。")
        prompt_textbox.configure(state="normal", fg_color=None) # 恢復預設可編輯顏色
        load_prompt_button.configure(state="normal")
        save_prompt_button.configure(state="normal")
    else:
        # 如果是預設模板，顯示內容並設為唯讀
        prompt_textbox.insert("1.0", prompt_content)
        prompt_textbox.configure(state="disabled", fg_color="gray85") # 設為唯讀外觀
        load_prompt_button.configure(state="disabled")
        save_prompt_button.configure(state="disabled")

def load_custom_prompt():
    """載入自訂 Prompt 檔案"""
    file_path = filedialog.askopenfilename(
        title="載入自訂 Prompt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            prompt_textbox.configure(state="normal")
            prompt_textbox.delete("1.0", tk.END)
            prompt_textbox.insert("1.0", content)
            custom_prompt_path.set(file_path) # 記錄路徑 (雖然目前沒用到)
            log_message(f"【日誌】已從 {os.path.basename(file_path)} 載入自訂 Prompt。")
        except Exception as e:
            log_message(f"【錯誤】載入自訂 Prompt 失敗: {e}")

def save_custom_prompt():
    """儲存目前文字框中的 Prompt 為檔案"""
    if prompt_template_var.get() != "自訂 Prompt":
        log_message("【提示】只有在選擇 '自訂 Prompt' 時才能儲存。")
        return

    file_path = filedialog.asksaveasfilename(
        title="儲存自訂 Prompt",
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        initialdir=os.getcwd(), # 從當前工作目錄開始
        initialfile="my_custom_prompt.txt"
    )
    if file_path:
        try:
            content = prompt_textbox.get("1.0", tk.END).strip()
            if not content:
                 log_message("【警告】Prompt 內容為空，未儲存。")
                 return
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            custom_prompt_path.set(file_path)
            log_message(f"【日誌】已將自訂 Prompt 儲存至 {os.path.basename(file_path)}。")
        except Exception as e:
            log_message(f"【錯誤】儲存自訂 Prompt 失敗: {e}")

# --- 新增：設定視窗相關函數 ---
def open_settings_window():
    """開啟設定視窗"""
    global settings_window, settings_entries

    # 如果視窗已存在，將其帶到最前
    if settings_window is not None and settings_window.winfo_exists():
        settings_window.lift()
        return

    settings_window = Toplevel(app)
    settings_window.title("設定")
    settings_window.geometry("1000x900") # 大幅增加尺寸以適應高解析度螢幕
    settings_window.minsize(1000, 900)  # 設置更大的最小尺寸，確保內容在2K和FHD顯示器上都能完整顯示
    settings_window.transient(app) # 依附主視窗
    settings_window.grab_set() # 鎖定焦點

    settings_entries = {} # 重置 entry 字典

    # --- 設定內容框架 ---
    content_frame = ctk.CTkFrame(master=settings_window)
    content_frame.pack(pady=10, padx=10, fill="both", expand=True)
    
    # --- 建立分頁標籤框架 ---
    tabview = ctk.CTkTabview(master=content_frame)
    tabview.pack(fill="both", expand=True, padx=5, pady=5)
    
    # --- 建立基本設定和進階設定兩個分頁 ---
    tab_basic = tabview.add("基本設定")
    tab_advanced = tabview.add("進階設定")
    tabview.set("基本設定")  # 預設顯示基本設定頁面
    
    # --- 基本設定頁面的內容 ---
    basic_frame = ctk.CTkScrollableFrame(master=tab_basic, width=700, height=550)
    basic_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # --- API 金鑰設定 ---
    ctk.CTkLabel(master=basic_frame, text="API 設定", font=("Arial", 16, "bold")).pack(pady=(5, 10), anchor="w")

    # API 金鑰
    api_frame = ctk.CTkFrame(master=basic_frame, fg_color="transparent")
    api_frame.pack(fill="x", padx=5, pady=5)
    ctk.CTkLabel(master=api_frame, text="Gemini API 金鑰:", width=150, anchor="w").pack(side="left", padx=(0, 5))
    api_entry = ctk.CTkEntry(master=api_frame, placeholder_text="請輸入您的 API 金鑰", show="*", width=400)
    api_entry.insert(0, app_settings.get("api_key", ""))
    api_entry.pack(side="left", fill="x", expand=True)
    settings_entries["api_key"] = api_entry
    
    # API 模型
    model_frame = ctk.CTkFrame(master=basic_frame, fg_color="transparent")
    model_frame.pack(fill="x", padx=5, pady=5)
    ctk.CTkLabel(master=model_frame, text="Gemini API 模型:", width=150, anchor="w").pack(side="left", padx=(0, 5))
    model_entry = ctk.CTkEntry(master=model_frame, placeholder_text="例如：gemini-2.0-flash", width=400)
    model_entry.insert(0, app_settings.get("api_model", "gemini-2.0-flash"))
    model_entry.pack(side="left", fill="x", expand=True)
    settings_entries["api_model"] = model_entry
    
    # --- 常用路徑設定 ---
    ctk.CTkLabel(master=basic_frame, text="常用路徑設定", font=("Arial", 16, "bold")).pack(pady=(15, 10), anchor="w")
    
    basic_paths = {
        "video_input": "影片輸入資料夾:",
        "transcription_output": "轉錄輸出資料夾:",
        "final_output": "最終文案輸出資料夾:",
        "html_template": "HTML 模板:"
    }
    
    for key, label_text in basic_paths.items():
        frame = ctk.CTkFrame(master=basic_frame, fg_color="transparent")
        frame.pack(fill="x", padx=5, pady=3)

        ctk.CTkLabel(master=frame, text=label_text, width=150, anchor="w").pack(side="left", padx=(0, 5))
        
        entry = ctk.CTkEntry(master=frame)
        entry.insert(0, app_settings.get(key, ""))
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        settings_entries[key] = entry
        
        button_text = "選擇..."
        button_width = 80
        command = lambda e=entry: select_folder(e)

        if key == "html_template":
            command = lambda e=entry: select_template_file_settings(e)
            
        button = ctk.CTkButton(master=frame, text=button_text, width=button_width, command=command)
        button.pack(side="left")
    
    # --- Prompt 設定 ---
    ctk.CTkLabel(master=basic_frame, text="Prompt 設定", font=("Arial", 16, "bold")).pack(pady=(15, 10), anchor="w")
    
    # 添加是否包含影片連結的選項
    include_video_frame = ctk.CTkFrame(master=basic_frame, fg_color="transparent")
    include_video_frame.pack(fill="x", padx=5, pady=5)
    
    include_video_var = tk.BooleanVar(value=app_settings.get("include_video", True))
    include_video_checkbox = ctk.CTkCheckBox(
        master=include_video_frame, 
        text="包含影片連結區域 (若未啟用，將不會在電子報中顯示影片區塊)",
        variable=include_video_var, 
        onvalue=True, 
        offvalue=False
    )
    include_video_checkbox.pack(anchor="w", padx=5)
    settings_entries["include_video"] = include_video_var
    
    # 影片連結設定提示
    video_link_info = ctk.CTkLabel(
        master=include_video_frame,
        text="※ 提示：要使用影片連結功能，請在進階設定中指定正確的URL設定檔路徑",
        font=("Arial", 11),
        text_color="#888888"
    )
    video_link_info.pack(anchor="w", padx=25, pady=(0, 5))
    
    # Prompt 選擇下拉選單
    prompt_menu_frame = ctk.CTkFrame(master=basic_frame, fg_color="transparent")
    prompt_menu_frame.pack(fill="x", padx=5, pady=5)
    ctk.CTkLabel(master=prompt_menu_frame, text="選擇模板:", width=150, anchor="w").pack(side="left", padx=(0, 5))
    
    # 在設定視窗中建立新的下拉選單
    settings_prompt_var = tk.StringVar(value=prompt_template_var.get())
    prompt_template_optionmenu_settings = ctk.CTkOptionMenu(
        master=prompt_menu_frame, 
        values=prompt_options,
        variable=settings_prompt_var,
        command=lambda x: update_prompt_textbox_settings(x)
    )
    prompt_template_optionmenu_settings.pack(side="left", fill="x", expand=True)
    
    # Prompt 顯示/編輯文字框
    settings_prompt_textbox = ctk.CTkTextbox(
        master=basic_frame, 
        height=150, 
        wrap="word",
        text_color="black",
        fg_color="white"
    )
    settings_prompt_textbox.pack(fill="x", expand=False, padx=5, pady=5)
    
    # 載入當前選定的 prompt 內容到新的文字框
    selected_prompt_name = settings_prompt_var.get()
    prompt_content = DEFAULT_PROMPTS.get(selected_prompt_name, "")
    settings_prompt_textbox.insert("1.0", prompt_content)
    
    # 根據選擇的模板類型設定文字框狀態
    if selected_prompt_name == "自訂 Prompt":
        settings_prompt_textbox.configure(state="normal")
    else:
        settings_prompt_textbox.configure(state="disabled")
    
    # 儲存這個文字框的引用到設定字典中
    settings_entries["prompt_textbox"] = settings_prompt_textbox
    settings_entries["prompt_template"] = settings_prompt_var
    
    # 載入/儲存按鈕框架
    prompt_buttons_frame = ctk.CTkFrame(master=basic_frame, fg_color="transparent")
    prompt_buttons_frame.pack(fill="x", padx=5, pady=(0, 5))
    
    load_prompt_button_settings = ctk.CTkButton(
        master=prompt_buttons_frame, 
        text="載入自訂 Prompt", 
        command=lambda: load_custom_prompt_settings(settings_prompt_textbox),
        state="disabled" if selected_prompt_name != "自訂 Prompt" else "normal"
    )
    load_prompt_button_settings.pack(side="left", padx=5)
    
    save_prompt_button_settings = ctk.CTkButton(
        master=prompt_buttons_frame, 
        text="儲存自訂 Prompt", 
        command=lambda: save_custom_prompt_settings(settings_prompt_textbox, settings_prompt_var),
        state="disabled" if selected_prompt_name != "自訂 Prompt" else "normal"
    )
    save_prompt_button_settings.pack(side="left", padx=5)
    
    # --- 進階設定頁面的內容 ---
    advanced_frame = ctk.CTkScrollableFrame(master=tab_advanced, width=700, height=550)
    advanced_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    ctk.CTkLabel(master=advanced_frame, text="進階路徑設定", font=("Arial", 16, "bold")).pack(pady=(5, 10), anchor="w")
    
    # 進階路徑設定
    advanced_paths = {
        "label_output": "標籤檔儲存資料夾:",
        "queue_output": "待轉文案資料夾:",
        "url_config": "URL 設定檔:",
        "unpaired_output": "漏單資料夾:"
    }
    
    for key, label_text in advanced_paths.items():
        frame = ctk.CTkFrame(master=advanced_frame, fg_color="transparent")
        frame.pack(fill="x", padx=5, pady=3)
        
        ctk.CTkLabel(master=frame, text=label_text, width=150, anchor="w").pack(side="left", padx=(0, 5))
        
        entry = ctk.CTkEntry(master=frame)
        entry.insert(0, app_settings.get(key, ""))
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        settings_entries[key] = entry
        
        button_text = "選擇..."
        button_width = 80
        command = lambda e=entry: select_folder(e)
        
        if key == "url_config":
            button_text = "選擇/儲存..."
            button_width = 100
            command = lambda e=entry: select_file(e)
            
        button = ctk.CTkButton(master=frame, text=button_text, width=button_width, command=command)
        button.pack(side="left")
    
    # 路徑設定說明
    explanation_frame = ctk.CTkFrame(master=advanced_frame)
    explanation_frame.pack(fill="x", padx=5, pady=10)
    
    explanation_text = """
    路徑說明：
    
    • 標籤檔儲存資料夾: 存放 Step 2 分類產生的標籤檔案
    • 待轉文案資料夾: Step 2/3 處理完後的中間檔案存放位置
    • URL 設定檔: 影片URL配置檔案，用於嵌入影片連結
    • 漏單資料夾: 未能配對的檔案臨時存放處
    """
    
    explanation_label = ctk.CTkLabel(
        master=explanation_frame, 
        text=explanation_text, 
        justify="left",
        wraplength=650,
        font=("Arial", 12)
    )
    explanation_label.pack(padx=10, pady=10, fill="x")
    
    # 在基本設定頁面添加儲存按鈕
    save_button_frame_basic = ctk.CTkFrame(master=basic_frame, fg_color="transparent")
    save_button_frame_basic.pack(fill="x", pady=20)
    
    save_button_basic = ctk.CTkButton(
        master=save_button_frame_basic, 
        text="儲存並關閉", 
        command=save_and_close_settings,
        fg_color="#28a745",  # 使用綠色
        hover_color="#218838"  # 深綠色懸停效果
    )
    save_button_basic.pack(pady=10, padx=20, fill="x")
    
    # 在進階設定頁面添加儲存按鈕
    save_button_frame_advanced = ctk.CTkFrame(master=advanced_frame, fg_color="transparent")
    save_button_frame_advanced.pack(fill="x", pady=20)
    
    save_button_advanced = ctk.CTkButton(
        master=save_button_frame_advanced, 
        text="儲存並關閉", 
        command=save_and_close_settings,
        fg_color="#28a745",  # 使用綠色
        hover_color="#218838"  # 深綠色懸停效果
    )
    save_button_advanced.pack(pady=10, padx=20, fill="x")
    
    # --- 關閉視窗處理 ---
    settings_window.protocol("WM_DELETE_WINDOW", close_settings_window)

def update_prompt_textbox_settings(selected_prompt_name):
    """根據下拉選單選擇更新設定頁面中的 Prompt 文字框內容和狀態"""
    global settings_entries
    
    if not settings_entries or "prompt_textbox" not in settings_entries:
        return
        
    prompt_textbox = settings_entries["prompt_textbox"]
    prompt_content = DEFAULT_PROMPTS.get(selected_prompt_name, "")

    prompt_textbox.configure(state="normal") # 允許編輯
    prompt_textbox.delete("1.0", tk.END) # 清空

    if selected_prompt_name == "自訂 Prompt":
        # 如果是自訂，允許編輯
        prompt_textbox.insert("1.0", "點擊 '載入' 或直接在此編輯您的 Prompt。使用 {original_content} 作為原文的佔位符。")
        prompt_textbox.configure(state="normal")
        # 啟用按鈕
        for widget in prompt_textbox.master.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for button in widget.winfo_children():
                    if isinstance(button, ctk.CTkButton) and ("載入" in button._text or "儲存" in button._text):
                        button.configure(state="normal")
    else:
        # 如果是預設模板，顯示內容並設為唯讀
        prompt_textbox.insert("1.0", prompt_content)
        prompt_textbox.configure(state="disabled")
        # 禁用按鈕
        for widget in prompt_textbox.master.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for button in widget.winfo_children():
                    if isinstance(button, ctk.CTkButton) and ("載入" in button._text or "儲存" in button._text):
                        button.configure(state="disabled")

def load_custom_prompt_settings(textbox):
    """載入自訂 Prompt 檔案到設定頁面的文字框"""
    file_path = filedialog.askopenfilename(
        title="載入自訂 Prompt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            textbox.configure(state="normal")
            textbox.delete("1.0", tk.END)
            textbox.insert("1.0", content)
            custom_prompt_path.set(file_path) # 記錄路徑
            log_message(f"【日誌】已從 {os.path.basename(file_path)} 載入自訂 Prompt。")
        except Exception as e:
            log_message(f"【錯誤】載入自訂 Prompt 失敗: {e}")

def save_custom_prompt_settings(textbox, prompt_var):
    """儲存設定頁面文字框中的 Prompt 為檔案"""
    if prompt_var.get() != "自訂 Prompt":
        log_message("【提示】只有在選擇 '自訂 Prompt' 時才能儲存。")
        return

    file_path = filedialog.asksaveasfilename(
        title="儲存自訂 Prompt",
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        initialdir=os.getcwd(), # 從當前工作目錄開始
        initialfile="my_custom_prompt.txt"
    )
    if file_path:
        try:
            content = textbox.get("1.0", tk.END).strip()
            if not content:
                 log_message("【警告】Prompt 內容為空，未儲存。")
                 return
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            custom_prompt_path.set(file_path)
            log_message(f"【日誌】已將自訂 Prompt 儲存至 {os.path.basename(file_path)}。")
        except Exception as e:
            log_message(f"【錯誤】儲存自訂 Prompt 失敗: {e}")

def save_and_close_settings():
    """儲存設定視窗中的值並關閉視窗"""
    global app_settings, settings_window

    for key, entry_widget in settings_entries.items():
        if key == "prompt_textbox":
            # 儲存 Prompt 文字內容
            app_settings["prompt_content"] = entry_widget.get("1.0", tk.END).strip()
        elif key == "prompt_template":
            # 儲存選擇的 Prompt 模板
            selected_template = entry_widget.get()
            app_settings["prompt_template"] = selected_template
            # 同步更新主視窗的 prompt_template_var
            prompt_template_var.set(selected_template)
            # 如果主視窗的 prompt_textbox 仍然存在，更新其內容
            if "prompt_textbox" in globals() and prompt_textbox.winfo_exists():
                update_prompt_textbox()
        elif key == "include_video":
            # 處理複選框變數
            app_settings["include_video"] = entry_widget.get()
        else:
            # 處理一般的 Entry 元件
            app_settings[key] = entry_widget.get()

    # 保存設定到檔案
    if save_settings(app_settings):
        log_message("【日誌】設定已儲存至配置檔案。")
    else:
        log_message("【警告】無法將設定保存至檔案，僅保存至記憶體中。")
    
    close_settings_window()

def close_settings_window(): # Closes the *general* settings window
    global settings_window
    if settings_window:
        settings_window.destroy()
        settings_window = None

# --- Functions for Template Settings Window ---

def open_template_settings_window():
    """Opens the template customization settings window."""
    global template_settings_window, template_settings_entries, app_settings

    if template_settings_window is not None and template_settings_window.winfo_exists():
        template_settings_window.focus()
        return

    template_settings_window = Toplevel(app)
    template_settings_window.title("編輯模板設定")
    template_settings_window.geometry("600x550") # Adjust size as needed
    template_settings_window.transient(app) # Keep it on top of the main app
    template_settings_window.protocol("WM_DELETE_WINDOW", close_template_settings_window) # Handle window close button

    # --- Get current customizations or defaults ---
    customizations = app_settings.get("template_customizations", {})
    # Ensure all keys exist using the defaults from load_settings
    default_customizations = load_settings().get("template_customizations", {})
    customizations = {**default_customizations, **customizations}


    # --- Create Frames for Organization ---
    main_frame = ctk.CTkFrame(template_settings_window)
    main_frame.pack(padx=20, pady=20, fill="both", expand=True)

    # Use a scrollable frame if content might exceed window height
    scrollable_frame = ctk.CTkScrollableFrame(main_frame)
    scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)


    # --- Input Fields ---
    row_index = 0
    template_settings_entries = {} # Reset entries dict

    # Helper function to create label and entry pairs
    def create_entry(parent, label_text, setting_key, default_value, row):
        label = ctk.CTkLabel(parent, text=label_text, anchor="w")
        label.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        entry = ctk.CTkEntry(parent, width=350)
        entry.grid(row=row + 1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        entry.insert(0, customizations.get(setting_key, default_value))
        template_settings_entries[setting_key] = entry
        return row + 2 # Return next available row index

    # Top Logo
    row_index = create_entry(scrollable_frame, "頂部 Logo URL:", "logo_url", "", row_index)

    # --- Online Seminar Section ---
    seminar_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    seminar_frame.grid(row=row_index, column=0, columnspan=2, pady=(10, 5), sticky="ew")
    seminar_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(seminar_frame, text="--- 線上說明會區塊 ---", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5)
    row_index += 1

    seminar_row = 1 # Start rows within the seminar frame
    seminar_row = create_entry(seminar_frame, "標題文字:", "seminar_title", "", seminar_row)
    seminar_row = create_entry(seminar_frame, "說明文字:", "seminar_description", "", seminar_row)
    seminar_row = create_entry(seminar_frame, "按鈕文字:", "seminar_button_text", "", seminar_row)
    seminar_row = create_entry(seminar_frame, "連結 URL:", "seminar_url", "", seminar_row)
    # --- Latest Courses Section ---
    courses_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
    courses_frame.grid(row=row_index, column=0, columnspan=2, pady=(10, 5), sticky="ew")
    courses_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(courses_frame, text="--- 關注最新課程資訊區塊 ---", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5)
    row_index += 1

    courses_row = 1 # Start rows within the courses frame
    courses_row = create_entry(courses_frame, "關注最新課程資訊區塊標題:", "course_section_title", "", courses_row)
    courses_row = create_entry(courses_frame, "課程圖片 URL:", "course_image_url", default_customizations.get("course_image_url", ""), courses_row)
    courses_row = create_entry(courses_frame, "圖片替代文字(seo用):", "course_image_alt", default_customizations.get("course_image_alt", ""), courses_row)
    courses_row = create_entry(courses_frame, "課程標題文字:", "course_title", default_customizations.get("course_title", ""), courses_row)
    courses_row = create_entry(courses_frame, "說明文字:", "courses_description", "", courses_row)
    courses_row = create_entry(courses_frame, "行動呼籲按鈕:", "courses_button_text", "", courses_row)
    courses_row = create_entry(courses_frame, "行動呼籲按鈕連結:", "courses_button_url", "", courses_row)

    # --- Footer Section ---
    footer_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")  
    footer_frame.grid(row=row_index, column=0, columnspan=2, pady=(10, 5), sticky="ew")
    footer_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(footer_frame, text="--- 頁尾資訊 ---", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5)
    row_index += 1

    footer_row = 1
    footer_row = create_entry(footer_frame, "公司地址:", "footer_address", default_customizations.get("footer_address", ""), footer_row)


    # --- Buttons Frame ---
    button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    button_frame.pack(pady=(10, 0), fill="x")

    save_button = ctk.CTkButton(button_frame, text="儲存並關閉", command=save_and_close_template_settings)
    save_button.pack(side="right", padx=10)

    cancel_button = ctk.CTkButton(button_frame, text="取消", command=close_template_settings_window, fg_color="gray")
    cancel_button.pack(side="right", padx=10)


def save_and_close_template_settings():
    """Saves the template customizations and closes the window."""
    global app_settings, template_settings_entries, template_settings_window
    
    updated_customizations = {}
    for key, entry_widget in template_settings_entries.items():
        updated_customizations[key] = entry_widget.get()

    # Update the main app_settings dictionary
    app_settings["template_customizations"] = updated_customizations

    # Save all settings (including these customizations) to the file
    if save_settings(app_settings):
        log_message("【系統】模板自訂設定已儲存。")
        close_template_settings_window() # Close window only if save was successful
    else:
        log_message("【錯誤】儲存模板自訂設定失敗，請檢查終端輸出。")
        # Optionally show an error message box here

def close_template_settings_window():
    """Closes the template settings window."""
    global template_settings_window
    if template_settings_window:
        template_settings_window.destroy()
        template_settings_window = None

# --- Original close_settings_window (for general settings) ---
def close_settings_window(): # Renamed slightly for clarity if needed, but keeping original name is fine too
    """關閉設定視窗"""
    global settings_window
    if settings_window is not None and settings_window.winfo_exists():
        settings_window.destroy()
        settings_window = None

# --- 日誌視窗相關函數 ---
def toggle_log_window():
    """切換日誌視窗的顯示狀態"""
    global log_window, log_textbox, log_messages_buffer

    if log_window is not None and log_window.winfo_exists():
        # 如果視窗存在，則銷毀它
        close_log_window()
    else:
        # 如果視窗不存在，則創建它
        log_window = Toplevel(app)
        log_window.title("執行日誌")
        log_window.geometry("700x500") # 設定日誌視窗大小
        log_window.transient(app) # 依附主視窗
        # log_window.grab_set() # 不要鎖定焦點，允許操作主視窗

        # --- 日誌內容框架 ---
        log_content_frame = ctk.CTkFrame(master=log_window)
        log_content_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # log_textbox 需要在創建視窗時賦值給全局變數
        log_textbox = ctk.CTkTextbox(master=log_content_frame, state="normal", wrap="word")
        log_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # --- 顯示之前暫存的所有訊息 ---
        if log_messages_buffer:
            # 先顯示一個提示，區分之前的訊息
            if len(log_messages_buffer) > 0:
                log_textbox.insert(tk.END, f"--- 顯示 {len(log_messages_buffer)} 條之前的日誌訊息 ---\n\n")
            # 顯示所有暫存的訊息
            for stored_msg in log_messages_buffer:
                log_textbox.insert(tk.END, stored_msg + "\n")
            # 滾動到底部
            log_textbox.see(tk.END)
        
        # 將狀態設回唯讀
        log_textbox.configure(state="disabled")

        # --- 日誌控制按鈕 (新增) ---
        log_buttons_frame = ctk.CTkFrame(master=log_window, fg_color="transparent")
        log_buttons_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # 清除按鈕
        clear_button = ctk.CTkButton(
            master=log_buttons_frame, 
            text="清除日誌", 
            command=clear_log, 
            width=100
        )
        clear_button.pack(side="left", padx=5)
        
        # --- 關閉視窗處理 ---
        log_window.protocol("WM_DELETE_WINDOW", close_log_window)

def clear_log():
    """清除日誌內容和緩衝區"""
    global log_textbox, log_messages_buffer
    if log_textbox is not None and log_textbox.winfo_exists():
        log_textbox.configure(state="normal")
        log_textbox.delete("1.0", tk.END)
        log_textbox.configure(state="disabled")
    
    # 清空緩衝區
    log_messages_buffer = []
    
    # 添加一條清除的訊息
    log_message("【日誌】日誌已清除。")

def close_log_window():
    """關閉日誌視窗並清理變數"""
    global log_window, log_textbox
    if log_window is not None and log_window.winfo_exists():
        log_window.destroy()
    log_window = None
    log_textbox = None # 清理全局變數但保留緩衝區

def open_output_folder():
    """打開最終輸出檔案資料夾"""
    output_folder = app_settings.get("final_output", "")
    if not output_folder or not os.path.exists(output_folder):
        log_message("【錯誤】最終文案輸出資料夾未設定或不存在")
        return
    
    # 依據不同作業系統開啟資料夾
    try:
        if os.name == 'nt':  # Windows
            os.startfile(output_folder)
        elif os.name == 'posix':  # macOS, Linux
            import subprocess
            # 嘗試使用合適的命令開啟資料夾
            try:
                subprocess.run(['open', output_folder])  # macOS
            except FileNotFoundError:
                try:
                    subprocess.run(['xdg-open', output_folder])  # Linux
                except FileNotFoundError:
                    log_message("【錯誤】無法自動開啟資料夾，請手動開啟")
        log_message(f"【日誌】已開啟最終輸出資料夾：{output_folder}")
    except Exception as e:
        log_message(f"【錯誤】開啟資料夾時發生錯誤：{e}")

# --- 主要介面佈局 ---

# --- 頂部框架 (放置設定和日誌按鈕) ---
top_frame = ctk.CTkFrame(master=app, fg_color="transparent")
top_frame.pack(pady=(10, 5), padx=20, fill="x", expand=False)

settings_button = ctk.CTkButton(master=top_frame, text="開啟設定 (API金鑰/路徑/Prompt)", command=open_settings_window)
settings_button.pack(side="left", padx=5)

# --- 新增：模板設定按鈕 ---
template_settings_button = ctk.CTkButton(master=top_frame, text="編輯模板設定", width=120, command=open_template_settings_window)
template_settings_button.pack(side="left", padx=5)

log_toggle_button = ctk.CTkButton(master=top_frame, text="顯示/隱藏日誌", command=toggle_log_window)
log_toggle_button.pack(side="left", padx=5)

# --- 主要操作區塊 ---
main_ops_frame = ctk.CTkFrame(master=app)
main_ops_frame.pack(pady=10, padx=20, fill="x", expand=False)

ctk.CTkLabel(master=main_ops_frame, text="執行步驟", font=("Arial", 16, "bold")).pack(pady=(5, 10))

# --- Step 1 按鈕 ---
step1_button_frame = ctk.CTkFrame(master=main_ops_frame, fg_color="transparent")
step1_button_frame.pack(fill="x", padx=10, pady=5)
step1_button = ctk.CTkButton(master=step1_button_frame, text="Step 1: 影音轉文字", command=run_step1)
step1_button.pack(fill="x", expand=True)

# --- 分類與合併選項 ---
enable_step2_3_var = tk.BooleanVar()
enable_step2_3_checkbox = ctk.CTkCheckBox(master=main_ops_frame, text="啟用分類與合併",
                                          variable=enable_step2_3_var, onvalue=True, offvalue=False,
                                          command=toggle_step2_3_options)
enable_step2_3_checkbox.pack(anchor="w", padx=10, pady=(10, 0))

# --- Step 4 按鈕 ---
step4_button_frame = ctk.CTkFrame(master=main_ops_frame, fg_color="transparent")
step4_button_frame.pack(fill="x", padx=10, pady=10)
step4_button = ctk.CTkButton(master=step4_button_frame, text="Step 4: 生成電子報", command=run_step4)
step4_button.pack(fill="x", expand=True)

# --- 開啟輸出資料夾按鈕 ---
open_folder_button_frame = ctk.CTkFrame(master=main_ops_frame, fg_color="transparent")
open_folder_button_frame.pack(fill="x", padx=10, pady=5)
open_folder_button = ctk.CTkButton(
    master=open_folder_button_frame, 
    text="開啟最終輸出資料夾", 
    command=open_output_folder,
    fg_color="#5a86e0",  # 使用藍紫色
    hover_color="#4a76d0"  # 深藍紫色懸停效果
)
open_folder_button.pack(fill="x", expand=True)

# --- Step 2/3 選項框架 (初始隱藏) ---
step2_3_options_frame = ctk.CTkFrame(master=main_ops_frame, fg_color="transparent")
# 預設不 pack

# 分類條件
clf_frame = ctk.CTkFrame(master=step2_3_options_frame, fg_color="transparent")
clf_frame.pack(fill="x", pady=2)
ctk.CTkLabel(master=clf_frame, text="分類條件:", width=80, anchor="w").pack(side="left", padx=(0, 5))
classification_optionmenu = ctk.CTkOptionMenu(master=clf_frame, values=classification_options, variable=classification_var)
classification_optionmenu.pack(side="left", fill="x", expand=True)

# 合併方案
mrg_frame = ctk.CTkFrame(master=step2_3_options_frame, fg_color="transparent")
mrg_frame.pack(fill="x", pady=2)
ctk.CTkLabel(master=mrg_frame, text="合併方案:", width=80, anchor="w").pack(side="left", padx=(0, 5))
merging_optionmenu = ctk.CTkOptionMenu(master=mrg_frame, values=merging_options, variable=merging_var)
merging_optionmenu.pack(side="left", fill="x", expand=True)

# Step 2/3 按鈕
step2_3_button = ctk.CTkButton(master=step2_3_options_frame, text="Step 2/3: 執行分類與合併", command=run_step2_3)
step2_3_button.pack(fill="x", pady=(5, 0))

# --- 初始檢查與狀態設定 ---
if not step1_available:
    log_message("【警告】Step1 處理模組 (Step1影音轉文字.py) 載入失敗，相關功能將無法使用。")
    step1_button.configure(state="disabled") # 初始禁用按鈕
if not step2_3_processor_available:
     log_message("【警告】Step2/3 處理模組載入失敗，分類與合併功能將無法使用。")
     enable_step2_3_checkbox.configure(state="disabled") # 禁用 Checkbox
     if enable_step2_3_var.get():
         enable_step2_3_checkbox.deselect()
         toggle_step2_3_options() # 更新 UI
     # 在這裡禁用 Step 2/3 按鈕（即使框架隱藏也要禁用）
     step2_3_button.configure(state="disabled")
if not step4_available:
     log_message("【警告】Step4 處理模組 (Step4生成電子報.py) 載入失敗，相關功能將無法使用。")
     step4_button.configure(state="disabled") # 禁用按鈕

# --- 最終設定 ---
app.after(100, lambda: None) # 移除 update_prompt_textbox 呼叫，因為相關元件已移至設定視窗
app.geometry("800x400") # <--- 調整主視窗高度，因為移除了 Prompt 設定區塊
app.mainloop() 