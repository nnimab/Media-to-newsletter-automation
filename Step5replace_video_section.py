import os
import re
import glob

# 定義影片區的開始和結束標記
VIDEO_SECTION_START = "<!-- 影片區 -->"
VIDEO_SECTION_END = "<!-- 內容區 -->"

# 新的影片區模板
NEW_VIDEO_SECTION_TEMPLATE = """<!-- 影片區 --> <div style="background:#FBE65D; margin:0px auto; max-width:600px;"> <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background:#FBE65D; width:100%;"> <tbody> <tr> <td style="direction:ltr; font-size:0px; padding:20px; text-align:center;"> <div style="font-size:0px; text-align:left; direction:ltr; display:inline-block; vertical-align:top; width:100%;"> <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%"> <tbody> <tr> <td style="vertical-align:top; padding:0;"> <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%"> <tbody> <tr> <td align="center" style="font-size:0px; padding:0px; word-break:break-word;"> <div style="margin:0 auto; max-width:520px; width:100%;"> <a href="https://www.youtube.com/watch?v={video_id1}" target="_blank" style="display:block; position:relative; margin-bottom:20px;"> <img src="https://img.youtube.com/vi/{video_id1}/maxresdefault.jpg" alt="{alt_text1}" style="width:100%; height:auto; border:0; border-radius:12px; display:block; object-fit:cover; aspect-ratio:16/9;"> <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%);"> <div style="width:0; height:0; border-style:solid; border-width:20px 0 20px 35px; border-color:transparent transparent transparent white; filter:drop-shadow(2px 2px 2px rgba(0,0,0,0.5));"></div> </div> </a> <a href="https://www.youtube.com/watch?v={video_id2}" target="_blank" style="display:block; position:relative;"> <img src="https://img.youtube.com/vi/{video_id2}/maxresdefault.jpg" alt="{alt_text2}" style="width:100%; height:auto; border:0; border-radius:12px; display:block; object-fit:cover; aspect-ratio:16/9;"> <div style="position:absolute; top:50%; left:50%; transform:translate(-50%, -50%);"> <div style="width:0; height:0; border-style:solid; border-width:20px 0 20px 35px; border-color:transparent transparent transparent white; filter:drop-shadow(2px 2px 2px rgba(0,0,0,0.5));"></div> </div> </a> </div> </td> </tr> </tbody> </table> </td> </tr> </tbody> </table> </div> </td> </tr> </tbody> </table> </div>"""

# 正則表達式模式，用於提取YouTube視頻ID和alt文本
VIDEO_URL_PATTERN = r'href="https://www.youtube.com/watch\?v=([^&"]+)'
ALT_TEXT_PATTERN = r'alt="([^"]+)"'

def extract_video_info(video_section):
    """從影片區部分提取YouTube視頻ID和alt文本"""
    video_ids = re.findall(VIDEO_URL_PATTERN, video_section)
    alt_texts = re.findall(ALT_TEXT_PATTERN, video_section)
    
    # 確保至少有兩個視頻ID和alt文本
    while len(video_ids) < 2:
        video_ids.append("")
    while len(alt_texts) < 2:
        alt_texts.append("")
        
    return {
        'video_id1': video_ids[0],
        'video_id2': video_ids[1] if len(video_ids) > 1 else "",
        'alt_text1': alt_texts[0],
        'alt_text2': alt_texts[1] if len(alt_texts) > 1 else ""
    }

def replace_video_section(html_content):
    """替換HTML內容中的影片區部分"""
    # 尋找影片區部分
    start_index = html_content.find(VIDEO_SECTION_START)
    end_index = html_content.find(VIDEO_SECTION_END)
    
    if start_index == -1 or end_index == -1:
        print("在HTML中找不到影片區部分")
        return html_content
    
    # 提取影片區部分
    video_section = html_content[start_index:end_index]
    
    # 從影片區提取視頻信息
    video_info = extract_video_info(video_section)
    
    # 使用提取的信息創建新的影片區
    new_video_section = NEW_VIDEO_SECTION_TEMPLATE.format(
        video_id1=video_info['video_id1'],
        video_id2=video_info['video_id2'],
        alt_text1=video_info['alt_text1'],
        alt_text2=video_info['alt_text2']
    )
    
    # 替換原始的影片區
    new_html_content = html_content[:start_index] + new_video_section + html_content[end_index:]
    
    return new_html_content

def process_html_files(directory):
    """處理指定目錄中的所有HTML文件"""
    html_files = glob.glob(os.path.join(directory, "*.html"))
    
    for html_file in html_files:
        print(f"處理文件: {os.path.basename(html_file)}")
        
        # 讀取HTML文件內容
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 替換影片區部分
        new_html_content = replace_video_section(html_content)
        
        # 將新的內容寫回文件
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(new_html_content)
        
        print(f"已完成處理: {os.path.basename(html_file)}")

if __name__ == "__main__":
    process_html_files("done")
    print("所有HTML文件處理完成") 