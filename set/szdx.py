import requests

on:
  schedule:
  - cron: '03 16,20,00,5,8,12 * * *' 
# 原始节目源地址
origin_url = "https://raw.githubusercontent.com/gzj7003/tvlist/main/txt_files/江苏电信.txt"

# 新增节目源列表
new_channels = [
    "苏州新闻综合,https://live-auth.51kandianshi.com/szgd/csztv1.m3u8",
    "苏州社会经济,https://live-auth.51kandianshi.com/szgd/csztv2.m3u8",
    "苏州文化生活,https://live-auth.51kandianshi.com/szgd/csztv3.m3u8",
    "苏州生活资讯,https://live-auth.51kandianshi.com/szgd/csztv5.m3u8",
    "苏州生活资讯,http://121.237.245.90:8000/rtp/239.49.8.116:8000",
    "苏州生活资讯,http://tylive.kan0512.com/norecord/norecord_csztv5/playlist.m3u8",
    "苏州生活资讯,http://liveshowbak2.kan0512.com/norecord/norecord_sbs5/playlist.m3u8",
    "苏州生活资讯,rtmp://csztv.2500sz.com/live/c05",
    "苏州4k,http://tylive.kan0512.com/norecord/csztv4k_fhd.m3u8"
]

try:
    # 获取原始节目源
    response = requests.get(origin_url)
    response.raise_for_status()
    
    # 合并内容
    original_content = response.text.strip()
    new_content = "\n".join(new_channels)
    merged_content = f"{original_content}\n{new_content}"

    # 保存结果到文件
    with open("szdx.txt", "w", encoding="utf-8") as f:
        f.write(merged_content)
        
    print("节目源合并成功！已保存到 szdx.txt")

except requests.exceptions.RequestException as e:
    print(f"请求失败: {e}")
except Exception as e:
    print(f"发生错误: {e}")
