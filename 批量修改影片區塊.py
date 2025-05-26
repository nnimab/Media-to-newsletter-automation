import os
import re
import shutil
from pathlib import Path

print("開始執行批量修改影片區塊腳本...")

# 使用相對路徑
current_dir = os.getcwd()
print(f"當前工作目錄: {current_dir}")

# 設定路徑
source_dir = Path(current_dir) / "done"
target_dir = Path(current_dir) / "done_fixed"

print(f"來源目錄: {source_dir}")
print(f"目標目錄: {target_dir}")

# 確保目標資料夾存在
try:
    target_dir.mkdir(exist_ok=True)
    print(f"目標目錄建立成功: {target_dir}")
except Exception as e:
    print(f"建立目標目錄時出錯: {e}")

# 檢查來源目錄是否存在
if not source_dir.exists():
    print(f"錯誤: 來源目錄不存在: {source_dir}")
    print(f"嘗試列出當前目錄的內容:")
    for item in Path(current_dir).iterdir():
        print(f"  - {item}")
    exit(1)
else:
    print(f"來源目錄存在，列出內部文件:")
    for item in source_dir.iterdir():
        print(f"  - {item}")

# 讀取文章影片縮圖url.txt獲取影片ID對應
video_urls = {}
url_file_path = source_dir / "文章影片縮圖url.txt"
print(f"嘗試讀取文件: {url_file_path}")

if url_file_path.exists():
    try:
        with open(url_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "=" in line and "youtube" in line:
                    parts = line.strip().split('=')
                    if len(parts) > 1:
                        video_id = parts[-1]
                        video_title = parts[0].split('.')[0] if '.' in parts[0] else parts[0]
                        video_urls[video_id] = video_title
        print(f"找到 {len(video_urls)} 個影片ID和標題對應")
    except Exception as e:
        print(f"讀取影片URL檔案時出錯: {e}")
else:
    print(f"警告: 影片URL檔案不存在: {url_file_path}")

# 新的影片區塊模板
def create_video_button_html(video_id, video_title=""):
    return f'''
<!-- 視頻縮略圖 -->
<table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:20px;">
  <tr>
    <td align="center">
      <a href="https://www.youtube.com/watch?v={video_id}" target="_blank" style="text-decoration:none; display:block;">
        <img src="https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" alt="{video_title}" width="100%" style="border:0; border-radius:12px; display:block;">
      </a>
    </td>
  </tr>
  <tr>
    <td align="center" style="padding:10px 0;">
      <a href="https://www.youtube.com/watch?v={video_id}" target="_blank" style="text-decoration:none;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border-collapse:separate; line-height:100%; max-width:250px;">
          <tr>
            <td align="center" bgcolor="#F53B7D" style="border:none; border-radius:0; padding:12px 15px; text-align:center;" valign="middle">
              <span style="font-family:Arial, sans-serif; font-size:15px; color:#FFFFFF; text-align:center; display:block;"><strong>點擊觀看完整教學</strong></span>
            </td>
          </tr>
        </table>
      </a>
    </td>
  </tr>
</table>
'''

# 處理每個HTML文件
try:
    html_files = [f for f in source_dir.glob("*.html") if f.is_file()]
    print(f"找到 {len(html_files)} 個HTML文件需要處理")
    
    if len(html_files) == 0:
        print(f"警告: 在 {source_dir} 中找不到HTML文件")
except Exception as e:
    print(f"搜尋HTML文件時出錯: {e}")
    html_files = []

process_count = 0
for html_file in html_files:
    print(f"處理文件: {html_file.name}")
    
    # 讀取HTML文件內容
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            print(f"  成功讀取文件，大小: {len(html_content)} 字節")
    except Exception as e:
        print(f"  讀取文件時出錯: {e}")
        continue
    
    # 尋找影片區塊
    video_section_pattern = r'<!-- 影片區 -->.*?<!-- 內容區 -->'
    video_section_match = re.search(video_section_pattern, html_content, re.DOTALL)
    
    if video_section_match:
        old_video_section = video_section_match.group(0)
        print(f"  找到影片區塊，大小: {len(old_video_section)} 字節")
        
        # 從舊的區塊中提取YouTube影片ID
        youtube_ids = re.findall(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', old_video_section)
        
        if youtube_ids:
            print(f"  找到 {len(youtube_ids)} 個YouTube影片ID: {', '.join(youtube_ids)}")
            
            # 生成新的影片區塊
            new_videos_html = ""
            for i, video_id in enumerate(youtube_ids):
                video_title = video_urls.get(video_id, f"影片{i+1}")
                new_videos_html += create_video_button_html(video_id, video_title)
            
            # 包裝新的影片區塊
            new_video_section = f'''<!-- 影片區 --> <div style="background:#FBE65D; margin:0px auto; max-width:600px;"> <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background:#FBE65D; width:100%;"> <tbody> <tr> <td style="direction:ltr; font-size:0px; padding:20px; text-align:center;"> <div style="font-size:0px; text-align:left; direction:ltr; display:inline-block; vertical-align:top; width:100%;"> <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%"> <tbody> <tr> <td style="vertical-align:top; padding:0;"> <table border="0" cellpadding="0" cellspacing="0" role="presentation" width="100%"> <tbody> <tr> <td align="center" style="font-size:0px; padding:0px; word-break:break-word;"> <div style="margin:0 auto; max-width:520px; width:100%;">{new_videos_html}</div> </td> </tr> </tbody> </table> </td> </tr> </tbody> </table> </div> </td> </tr> </tbody> </table> </div><!-- 內容區 -->'''
            print(f"  生成新的影片區塊，大小: {len(new_video_section)} 字節")
            
            # 替換舊的影片區塊
            new_html_content = html_content.replace(old_video_section, new_video_section)
            
            # 保存到新位置
            target_file = target_dir / html_file.name
            try:
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(new_html_content)
                process_count += 1
                print(f"  已保存修改後的文件: {target_file}")
            except Exception as e:
                print(f"  保存文件時出錯: {e}")
        else:
            print(f"  在影片區塊中未找到YouTube影片ID")
            # 仍然複製原始檔案到目標資料夾
            try:
                shutil.copy2(html_file, target_dir)
                process_count += 1
                print(f"  已複製原始文件: {target_dir / html_file.name}")
            except Exception as e:
                print(f"  複製文件時出錯: {e}")
    else:
        print(f"  未找到影片區塊")
        # 仍然複製原始檔案到目標資料夾
        try:
            shutil.copy2(html_file, target_dir)
            process_count += 1
            print(f"  已複製原始文件: {target_dir / html_file.name}")
        except Exception as e:
            print(f"  複製文件時出錯: {e}")

# 複製文章影片縮圖url.txt到新資料夾
if url_file_path.exists():
    try:
        shutil.copy2(url_file_path, target_dir)
        print(f"已複製 文章影片縮圖url.txt 到目標資料夾")
    except Exception as e:
        print(f"複製影片URL檔案時出錯: {e}")

print(f"處理完成！共處理 {process_count} 個文件")
print(f"修改後的文件已保存到: {target_dir}")

# 列出目標資料夾中的文件
try:
    target_files = list(target_dir.glob("*"))
    print(f"目標資料夾中的文件數量: {len(target_files)}")
    for file in target_files[:5]:  # 只顯示前5個文件
        print(f"- {file.name}")
    if len(target_files) > 5:
        print(f"...以及其他 {len(target_files) - 5} 個文件")
except Exception as e:
    print(f"列出目標資料夾文件時出錯: {e}") 