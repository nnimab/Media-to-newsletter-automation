import os
import json
import requests
import traceback # 用於打印詳細錯誤
import importlib.util # 用於檢查模組是否已安裝

# Gemini API Endpoint (可以與 Step2 分開設定不同模型)
GEMINI_API_ENDPOINT_STEP4 = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}" # 使用 gemini-pro
HEADERS = {"Content-Type": "application/json"}

# 嘗試導入 google.genai 庫，如果不存在則退回到傳統 API 調用
has_genai = importlib.util.find_spec("google.genai") is not None

# 設定輸入與輸出資料夾路徑 -- 移除硬編碼
# input_folder = 'G:\我的雲端硬碟\自動化生成文案\待轉文案'
# output_folder = 'G:\我的雲端硬碟\自動化生成文案\文案生成完成'
# os.makedirs(output_folder, exist_ok=True)

# 設定URL配置檔案路徑 -- 移除硬編碼
# url_config_path = os.path.join(os.path.dirname(input_folder), 'video_urls.json')

# Gemini API 設定 -- 移除硬編碼
# API_KEY = "AIzaSyA4J7PlNJurZqxf9T38YPKGUyj-eYomfUE"
# endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-pro-exp-02-05:generateContent?key={API_KEY}"
# headers = {"Content-Type": "application/json"}

# 讀取URL配置文件 -- 移除全域讀取
# video_urls = {}
# try:
#     with open(url_config_path, 'r', encoding='utf-8') as f:
#         video_urls = json.load(f)
#     print(f"【日誌】成功載入URL配置檔案，共 {len(video_urls)} 個影片配置")
# except Exception as e:
#     print(f"【警告】讀取URL配置檔案失敗: {e}，將不會插入影片嵌入代碼")

# --- Helper Functions ---

def read_file_content(filepath, log_callback):
    """通用檔案讀取函數 (Step 4 預期只處理 txt)"""
    try:
        if filepath.lower().endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            log_callback(f"【警告】Step 4: 輸入資料夾中發現非 .txt 檔案，將跳過: {os.path.basename(filepath)}")
            return None
    except Exception as e:
        log_callback(f"【錯誤】Step 4: 讀取檔案失敗 {os.path.basename(filepath)}: {e}")
        return None

def call_gemini_api_step4(api_key, prompt_text, log_callback, model_name="gemini-2.0-flash"):
    """呼叫 Gemini API (用於 Step 4 生成內文) 並處理回應"""
    global has_genai  # 聲明使用全域變數
    
    if not api_key:
        log_callback("【錯誤】Step 4: 未提供 Gemini API 金鑰。")
        return None
    
    log_callback(f"【日誌】Step 4: 呼叫 Gemini API 生成電子報內文中 (使用模型: {model_name})...")
    
    # 使用 google.genai 庫 (新方法)
    if has_genai:
        try:
            from google import genai
            
            # 配置 API
            genai.configure(api_key=api_key)
            
            # 生成內容
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt_text)
            
            if hasattr(response, 'text'):
                generated_text = response.text.strip()
                log_callback("【日誌】Step 4: 已成功從 API 獲取生成內文。")
                
                # 將 Markdown 常見格式稍微轉成 HTML (基本轉換)
                generated_text = generated_text.replace('\n\n', '<br><br>')
                generated_text = generated_text.replace('\n', '<br>')     # 換行
                return generated_text
            else:
                log_callback(f"【錯誤】Step 4: API 響應缺少文本內容: {response}")
                return None
                
        except ImportError:
            log_callback("【警告】未安裝 google-generativeai 庫，將使用傳統 API 調用方式。")
            has_genai = False  # 更新狀態以避免再次嘗試
            # 繼續使用舊方法
        except Exception as e:
            log_callback(f"【錯誤】Step 4: 使用 genai 庫調用 API 時發生錯誤: {e}")
            log_callback(traceback.format_exc())
            return None

    # 傳統 API 調用方法 (舊方法)
    if not has_genai:
        try:
            # 更新 endpoint 以使用自訂模型
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            # 增加 safetySettings 範例 (可選，根據需要調整)
            payload = {
                "contents": [{"parts": [{"text": prompt_text}]}],
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                ],
                "generationConfig": { # 可選：調整生成參數
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    # "maxOutputTokens": 8192, # 根據模型限制和需求設定
                }
            }

            response = requests.post(endpoint, headers=HEADERS, data=json.dumps(payload), timeout=120) # 生成可能需要更長超時

            if response.status_code == 403:
                 log_callback("【錯誤】Step 4: Gemini API 金鑰無效或權限不足。")
                 return None
            elif response.status_code != 200:
                log_callback(f"【錯誤】Step 4: API 回傳狀態碼 {response.status_code}: {response.text}")
                return None

            response_json = response.json()
            candidates = response_json.get("candidates", [])

            if not candidates:
                finish_reason = response_json.get("promptFeedback", {}).get("blockReason")
                if finish_reason:
                     log_callback(f"【警告】Step 4: API 回應缺少內容，原因: {finish_reason}")
                else:
                    log_callback(f"【錯誤】Step 4: API 回傳結果中沒有候選資料：{response_json}")
                return None

            # 解析日誌資訊 (可選)
            usage = response_json.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", "N/A")
            candidate_tokens = usage.get("candidatesTokenCount", "N/A")
            log_callback(f"【日誌】Step 4: API 使用量 - 提示 tokens: {prompt_tokens}, 回應 tokens: {candidate_tokens}")

            candidate_content = candidates[0].get("content", {})
            parts = candidate_content.get("parts", [])
            if not parts or not parts[0].get("text", "").strip():
                finish_reason = candidates[0].get("finishReason", "N/A")
                log_callback(f"【錯誤】Step 4: API 回傳生成的內文為空。完成原因: {finish_reason}")
                return None

            generated_text = parts[0].get("text", "").strip()
            log_callback("【日誌】Step 4: 已成功從 API 獲取生成內文。")
            # 將 Markdown 常見格式稍微轉成 HTML (基本轉換)
            generated_text = generated_text.replace('\n\n', '<br><br>')
            generated_text = generated_text.replace('\n', '<br>')     # 換行
            # 可以加入更多 Markdown 轉換規則 (e.g., **, lists)
            return generated_text

        except requests.exceptions.RequestException as e:
            log_callback(f"【錯誤】Step 4: 呼叫 API 時網路連線錯誤：{e}")
            return None
        except Exception as e:
            log_callback(f"【錯誤】Step 4: 呼叫 API 或解析回應時發生未知錯誤：{e}")
            log_callback(traceback.format_exc()) # 打印詳細錯誤
            return None


def load_video_urls(url_config_path, log_callback):
    """載入 video_urls.json 檔案"""
    if not os.path.exists(url_config_path):
        log_callback(f"【警告】URL 設定檔不存在: {url_config_path}，將無法插入影片連結。")
        return {}
    try:
        with open(url_config_path, 'r', encoding='utf-8') as f:
            video_urls = json.load(f)
        log_callback(f"【日誌】已載入 URL 設定檔，共 {len(video_urls)} 個影片配置。")
        return video_urls
    except Exception as e:
        log_callback(f"【錯誤】讀取 URL 設定檔失敗: {e}")
        return {}

def save_video_urls(video_urls, url_config_path, log_callback):
     """儲存更新後的 video_urls.json 檔案 (標記 processed)"""
     try:
         with open(url_config_path, 'w', encoding='utf-8') as f:
             json.dump(video_urls, f, ensure_ascii=False, indent=2)
         log_callback(f"【日誌】已更新 URL 設定檔 (標記完成狀態)。")
     except Exception as e:
         log_callback(f"【錯誤】儲存更新後的 URL 設定檔失敗: {e}")


def generate_video_embed(video_name, video_urls_data, log_callback):
    """根據 video_urls.json 中的資訊生成影片嵌入代碼"""
    # video_name 是不含副檔名的基本名稱
    url_info = video_urls_data.get(video_name)

    if not url_info or not url_info.get("url"):
        log_callback(f"【警告】在 URL 設定檔中找不到影片 '{video_name}' 的有效 URL。")
        # 返回一個佔位符或提示
        return """
        <div style="border:1px dashed #ccc; padding:20px; text-align:center; color:#777;">
            <p>影片嵌入區域</p>
            <p>(未在 URL 設定檔中找到此影片的連結)</p>
        </div>
        """

    video_url = url_info["url"]

    # --- 沿用您原有的嵌入邏輯 --- (稍微美化 iframe)
    if "youtube.com" in video_url or "youtu.be" in video_url:
        if "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1].split("?")[0]
        elif "v=" in video_url:
             video_id = video_url.split("v=")[1].split("&")[0]
        else:
             video_id = None # 無法解析 ID

        if video_id:
            # 使用 padding-bottom trick 保持長寬比
            return f'''<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; background: #000;"> <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border:0;" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe> </div>'''
        else:
             log_callback(f"【警告】無法從 YouTube URL 解析影片 ID: {video_url}")

    elif "vimeo.com" in video_url:
        try:
            video_id = video_url.split("/")[-1].split("?")[0]
            return f'''<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; background: #000;"> <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border:0;" src="https://player.vimeo.com/video/{video_id}" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe> </div>'''
        except IndexError:
             log_callback(f"【警告】無法從 Vimeo URL 解析影片 ID: {video_url}")

    # 如果無法生成 iframe 或不是 YT/Vimeo，顯示按鈕
    return f"""
    <div style="text-align:center; padding:20px; border:1px solid #eee; border-radius: 5px; background:#f9f9f9;">
        <a href="{video_url}" target="_blank" style="display:inline-block; background:#F53B7D; color:#FFFFFF; font-family:Arial, sans-serif; font-size:16px; font-weight:bold; padding:15px 30px; text-decoration:none; border-radius:4px;">▶️ 觀看影片</a>
        <p style="margin-top:8px; font-size:12px; color:#666;">(點擊按鈕在新分頁觀看)</p>
    </div>
    """

# --- 新增：與AI協作生成HTML的函數 ---
def generate_html_with_ai(api_key, original_content, video_embed_html, template_content, template_customizations, log_callback, model_name="gemini-2.0-flash", include_video=True): # <-- 新增 template_customizations
    """讓AI將內容整合到HTML模板中，並應用自訂設定"""
    global has_genai  # 聲明使用全域變數
    
    # 根據include_video選項調整prompt
    if include_video and video_embed_html:
        video_instruction = f"""
# 影片嵌入代碼 (請放在適當位置)：
{video_embed_html}
"""
    elif include_video and not video_embed_html:
        video_instruction = """
# 注意：
未找到對應的影片連結。請在模板中預留一個簡單的影片佔位區域，顯示「(未在URL設定檔中找到此影片的連結)」。
"""
    else:
        video_instruction = """
# 注意：
用戶已選擇不包含影片連結區域。請不要在文章中添加影片的區域，僅專注於文章內容的排版，務必除了影片以外都依據模板的樣式標題，內文等等。
"""
    
    # --- 新增：建立自訂內容的說明 ---
    customization_instructions = "# 模板自訂內容 (請將這些值替換掉模板中對應的預設內容)：\n"
    has_customizations = False
    for key, value in template_customizations.items():
        if value: # 只包含有值的設定
            customization_instructions += f"- {key}: {value}\n"
            has_customizations = True
    if not has_customizations:
        customization_instructions = "# 注意：沒有提供模板自訂內容，請使用模板中的預設值。\n"
    # ---------------------------------

    prompt = f"""
請將以下轉錄文字內容，整合進提供的 HTML 模板中的適當位置（通常是主要內容區域）。
同時，請根據提供的「模板自訂內容」指示，修改 HTML 模板中對應區塊的內容（例如 Logo URL、說明會資訊、課程資訊、頁尾地址等）。如果某個自訂內容未提供，則保留模板中的原始值。

特別注意：
1. 請務必根據文章生成電子報的主標題，通常位於內容頂部的標題區域。這是電子報的主要標題，請查找模板中的標題文字整替換。
2. 標題通常在 HTML 中呈現為 <div> 元素，包含較大字體尺寸和粗體效果，位於頂部標誌區域之後。
3. 即使原始內容中有自己的標題，也請保留模板的標題樣式和格式，僅替換文字內容。

# 轉錄的內容 (請整合到模板主要內容區)：
{original_content}

{video_instruction}

{customization_instructions}

# HTML模板 (請基於此模板進行修改)：
{template_content}

請仔細檢查模板結構，確保替換操作的準確性，尤其是大標題的正確替換。最終請提供完整的、經過內容整合與自訂修改後的 HTML 代碼。只需回傳 HTML 代碼，不需要解釋或包含 ```html 標記，但要注意一點，如果原文中有標題之類的務必符合模板中的標題樣式。
"""

    # 使用 google.genai 庫 (新方法)
    if has_genai:
        try:
            from google import genai
            
            # 配置 API
            genai.configure(api_key=api_key)
            
            log_callback(f"【日誌】Step 4: 使用 AI 整合內容到 HTML 模板中 (使用模型: {model_name})...")
            
            # 生成內容
            model = genai.GenerativeModel(model_name)
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 8192
            }
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if hasattr(response, 'text'):
                generated_html = response.text.strip()
                log_callback("【日誌】Step 4: 成功生成完整 HTML。")
                return generated_html
            else:
                log_callback(f"【錯誤】Step 4: API 響應缺少文本內容: {response}")
                return None
                
        except ImportError:
            log_callback("【警告】未安裝 google-generativeai 庫，將使用傳統 API 調用方式。")
            # 繼續使用舊方法
        except Exception as e:
            log_callback(f"【錯誤】Step 4: 使用 genai 庫調用 API 時發生錯誤: {e}")
            log_callback(traceback.format_exc())
            return None

    # 傳統 API 調用方法 (舊方法)
    try:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        log_callback(f"【日誌】Step 4: 使用 API 整合內容到 HTML 模板中 (使用模型: {model_name})...")
        
        request_data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 60192  # 增加輸出長度限制，以容納完整HTML
            }
        }
        
        response = requests.post(endpoint, headers=headers, json=request_data)
        response.raise_for_status()  # 如果HTTP響應狀態不在200-299之間，則拋出異常
        
        response_json = response.json()
        
        # 嘗試從響應中提取文本
        try:
            generated_html = response_json['candidates'][0]['content']['parts'][0]['text']
            return generated_html
        except (KeyError, IndexError) as e:
            log_callback(f"【錯誤】Step 4: 解析 API 回應時出錯：{e}，未找到生成的內容")
            log_callback(f"API 回應：{response_json}")
            return None
        
    except requests.exceptions.RequestException as e:
        log_callback(f"【錯誤】Step 4: 呼叫 API 時網路連線錯誤：{e}")
        return None
    except Exception as e:
        log_callback(f"【錯誤】Step 4: 呼叫 API 或解析回應時發生未知錯誤：{e}")
        log_callback(traceback.format_exc())
        return None

# --- 修改主要處理函數 ---
def generate_newsletter(
    input_folder,
    output_folder,
    url_config_path,
    html_template_path,
    api_key,
    prompt_template_name, # e.g., "改寫成文章"
    prompt_template_content, # The actual prompt string (might be custom)
    log_callback=print,
    api_model="gemini-2.0-flash", # 新增：自訂模型參數
    include_video=True, # 新增：是否包含影片連結區域
    template_customizations={} # <-- 新增：模板自訂設定字典
):
    """
    遍歷輸入資料夾的 txt 檔案，生成 HTML 電子報。
    
    Args:
        ... (其他參數)
        template_customizations (dict): 包含模板自訂內容的字典。
    """
    log_callback(f"--- 開始執行 Step 4：生成電子報 ---")
    log_callback(f"讀取處理後文字稿來源: {input_folder}")
    log_callback(f"HTML 輸出資料夾: {output_folder}")
    log_callback(f"使用的 HTML 模板: {html_template_path}")
    log_callback(f"使用的 Prompt 模板: {prompt_template_name}")
    log_callback(f"使用的 Gemini 模型: {api_model}")
    log_callback(f"是否包含影片連結區域: {'是' if include_video else '否'}")

    # --- 檢查輸入 --- (不變)
    if not os.path.isdir(input_folder):
        log_callback(f"【錯誤】Step 4: 輸入資料夾不存在: {input_folder}")
        return False
    os.makedirs(output_folder, exist_ok=True) # 確保輸出目錄存在
    if not html_template_path or not os.path.exists(html_template_path):
         log_callback(f"【錯誤】Step 4: HTML 模板檔案不存在或未指定: {html_template_path}")
         return False
    if prompt_template_name != "僅填入原文" and not api_key:
        log_callback("【錯誤】Step 4: 選擇的 Prompt 需要 API 金鑰，但未提供。")
        return False

    # --- 讀取HTML模板 ---
    try:
        with open(html_template_path, "r", encoding="utf-8") as f:
            html_template_content = f.read()
        log_callback(f"【日誌】成功讀取 HTML 模板，大小：{len(html_template_content)} 字元。")
    except Exception as e:
        log_callback(f"【錯誤】讀取 HTML 模板失敗: {e}")
        return False

    # --- 讀取URL配置 ---
    video_urls_data = load_video_urls(url_config_path, log_callback)
    
    # --- 處理每個輸入檔案 ---
    processed_count = 0
    error_count = 0
    input_files = []
    
    # 只處理 .txt 檔案
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.txt'):
            input_files.append(filename)
    
    if not input_files:
        log_callback(f"【警告】輸入資料夾 '{input_folder}' 中未找到任何 .txt 檔案。")
        return False
    
    total_files = len(input_files)
    log_callback(f"【日誌】總共找到 {total_files} 個 .txt 檔案等待處理。")
    
    overall_success = True # 用於追蹤全局處理狀態
    
    for index, filename in enumerate(input_files, 1):
        log_callback(f"\n--- 處理檔案 {index}/{total_files}: {filename} ---")
        file_path = os.path.join(input_folder, filename)
        
        # 讀取檔案內容
        original_content = read_file_content(file_path, log_callback)
        if original_content is None:
            log_callback(f"【跳過】讀取檔案失敗: {filename}")
            error_count += 1
            overall_success = False
            continue
        
        # 取得不含副檔名的檔名
        base_name = os.path.splitext(filename)[0]
        
        # --- Step 1: 使用選定的 Prompt 處理內容 ---
        if prompt_template_name == "僅填入原文":
            log_callback("【日誌】使用 '僅填入原文' 策略，直接使用檔案內容。")
            # 不經過API，直接使用原始內容
            processed_content = original_content
        else:
            # 需要呼叫 API 進行內容處理
            log_callback(f"【日誌】使用 '{prompt_template_name}' Prompt 處理內容...")
            final_prompt = prompt_template_content.format(original_content=original_content)
            api_result = call_gemini_api_step4(api_key, final_prompt, log_callback, api_model)
            if api_result is not None:
                processed_content = api_result
                log_callback("【日誌】內容處理成功。")
            else:
                log_callback("【錯誤】從 API 獲取生成內文失敗，將使用原始內容作為備用。")
                processed_content = original_content
                error_count += 1
                overall_success = False
        
        # --- Step 2: 提取影片嵌入代碼 ---
        # 嘗試從 base_name 推斷原始影片名稱 (如果包含 '+', 取第一部分)
        original_video_name_guess = base_name.split('+')[0]
        video_embed_html = generate_video_embed(original_video_name_guess, video_urls_data, log_callback)
        
        # --- Step 3: 使用AI將內容整合進HTML模板 ---
        log_callback("【日誌】使用AI將處理後的內容整合到HTML模板...")
        final_html = generate_html_with_ai(
            api_key=api_key,
            original_content=processed_content,  # 已處理過的內容
            video_embed_html=video_embed_html,   # 影片嵌入代碼
            template_content=html_template_content,  # 原始HTML模板
            template_customizations=template_customizations, # <-- 傳遞自訂設定
            log_callback=log_callback, # <-- 確保 log_callback 在正確位置
            model_name=api_model,
            include_video=include_video  # 傳遞是否包含影片區域的設定
        )
        
        if final_html is None:
            log_callback("【錯誤】無法生成最終HTML，跳過此檔案。")
            error_count += 1
            overall_success = False
            continue
        
        # --- 儲存最終HTML ---
        output_filename = f"{base_name}.html"
        output_path = os.path.join(output_folder, output_filename)
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_html)
            log_callback(f"【成功】已生成並儲存HTML電子報: {output_filename}")
            processed_count += 1
            
            # 更新影片URL設定檔中的處理狀態
            if original_video_name_guess in video_urls_data:
                video_urls_data[original_video_name_guess]["processed"] = True
        except Exception as e:
            log_callback(f"【錯誤】儲存HTML檔案失敗: {e}")
            error_count += 1
            overall_success = False
    
    # --- 儲存更新後的 URL 設定檔 ---
    save_video_urls(video_urls_data, url_config_path, log_callback)
    
    # --- 處理完成報告 ---
    log_callback(f"\n--- Step 4 處理完成 ---")
    log_callback(f"總共處理: {total_files} 個檔案")
    log_callback(f"成功生成: {processed_count} 個電子報")
    log_callback(f"處理失敗: {error_count} 個檔案")
    
    # 返回整體成功狀態
    return overall_success


# --- 可選：允許腳本獨立執行 (用於測試) ---
if __name__ == "__main__":
    print("** 正在執行 Step 4 生成電子報測試 **")

    # --- 測試設定 ---
    test_input_folder = r"G:\我的雲端硬碟\自動化生成文案\待轉文案_test" # Step 3 的輸出
    test_output_folder = r"G:\我的雲端硬碟\自動化生成文案\文案生成完成_test"
    test_url_config_path = r"G:\我的雲端硬碟\自動化生成文案\video_urls_test.json"
    test_html_template_path = r"templates\範例模板.html" # 確保此模板存在
    test_api_key = "YOUR_API_KEY" # <--- 填入您的 API 金鑰

    os.makedirs(test_output_folder, exist_ok=True)

    # --- 選擇測試 Prompt ---
    # prompt_name_to_test = "僅填入原文"
    prompt_name_to_test = "改寫成文章"
    # prompt_name_to_test = "摘要重點"
    # prompt_name_to_test = "自訂 Prompt" # 如果測試自訂，需要設定下面的 content
    prompt_content_to_test = ""
    if prompt_name_to_test == "自訂 Prompt":
         prompt_content_to_test = "請將以下內容總結成三句話：\n{original_content}" # 範例自訂 Prompt
    else:
         # 從 DEFAULT_PROMPTS 字典 (如果 Step 4 也定義了) 或直接複製貼上
         prompt_content_to_test = """請將以下影片轉錄內容（可能包含原始檔名、影片長度和轉錄文字）改寫成一篇流暢、易於閱讀的電子報文章段落。請保留核心資訊和教學內容（如果有），但用更自然的語氣書寫。
內容：
{original_content}

改寫後的文章段落：
"""

    print(f"測試輸入資料夾: {test_input_folder}")
    print(f"測試輸出資料夾: {test_output_folder}")
    print(f"測試 URL 設定檔: {test_url_config_path}")
    print(f"測試 HTML 模板: {test_html_template_path}")
    print(f"測試 Prompt 模板: {prompt_name_to_test}")

    if prompt_name_to_test != "僅填入原文" and test_api_key == "YOUR_API_KEY":
         print("\n!!警告!! 測試需要 API 金鑰，請在程式碼中設定 test_api_key")
    else:
        success = generate_newsletter(
            input_folder=test_input_folder,
            output_folder=test_output_folder,
            url_config_path=test_url_config_path,
            html_template_path=test_html_template_path,
            api_key=test_api_key,
            prompt_template_name=prompt_name_to_test,
            prompt_template_content=prompt_content_to_test,
            log_callback=print
        )

        if success:
            print("\n--- Step 4 測試執行完畢 (可能包含警告) ---")
        else:
            print("\n--- Step 4 測試執行過程中發生錯誤 ---")

        print(f"\n請檢查輸出資料夾：{test_output_folder}")
