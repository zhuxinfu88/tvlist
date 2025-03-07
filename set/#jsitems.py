# 在文件开头添加正则表达式预编译
CTV_PATTERN = re.compile(r'(CCTV|央视)([1-9]|1[0-5])\b')
CUSTOM_CHANNEL = "苏州新闻综合,https://live-auth.51kandianshi.com/szgd/csztv1.m3u8"
CUSTOM_CHANNEL = "苏州社会经济,https://live-auth.51kandianshi.com/szgd/csztv2.m3u8"
CUSTOM_CHANNEL = "苏州文化生活,https://live-auth.51kandianshi.com/szgd/csztv3.m3u8"
CUSTOM_CHANNEL = "苏州生活资讯,https://live-auth.51kandianshi.com/szgd/csztv5.m3u8"
CUSTOM_CHANNEL = "苏州4K,https://live-auth.51kandianshi.com/szgd/csztv4k_hd.m3u8"
import os
import requests
import re
import base64
import cv2
import datetime
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse


files = os.listdir('udpjs')

files_name = []


for file in files:
    name, extension = os.path.splitext(file)
    files_name.append(name)


provinces_isps = [name for name in files_name if name.count('_') == 1]


print(f"本次查询：{provinces_isps}的组播节目") 

keywords = []

for province_isp in provinces_isps:

    try:
        with open(f'udpjs/{province_isp}.txt', 'r', encoding='utf-8') as file:
            lines = file.readlines()
            lines = [line.strip() for line in lines if line.strip()]

        if lines:
            first_line = lines[0]
            if "rtp://" in first_line:
                mcast = first_line.split("rtp://")[1].split(" ")[0]
                keywords.append(province_isp + "_" + mcast)
    except FileNotFoundError:

        print(f"文件 '{province_isp}.txt' 不存在. 跳过此文件.")

for keyword in keywords:
    province, isp, mcast = keyword.split("_")


    if province == "北京" and isp == "联通":
        isp_en = "cucc"
        org = "China Unicom Beijing Province Network"
    elif isp == "联通":
        isp_en = "cucc"
        org = "CHINA UNICOM China169 Backbone"
    elif isp == "电信":
        org = "Chinanet"
        isp_en = "ctcc"
    elif isp == "移动":
        org = "China Mobile communications corporation"
        isp_en = "cmcc"
        
#    else:
#        org = ""
    
    current_time = datetime.now()
    timeout_cnt = 0
    result_urls = set() 
    while len(result_urls) == 0 and timeout_cnt <= 5:
        try:
            search_url = 'https://fofa.info/result?qbase64='
            search_txt = f'\"udpxy\" && country=\"CN\" && region=\"{province}\" && org=\"{org}\"'
            bytes_string = search_txt.encode('utf-8')

            search_txt = base64.b64encode(bytes_string).decode('utf-8')
            search_url += search_txt
            print(f"{current_time} 查询运营商 : {province}{isp} ，查询网址 : {search_url}")

            headers = {"referer": "https://www.baidu.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
            "cookie": "_ga=GA1.1.706124435.1725120803; Hm_lvt_4275507ba9b9ea6b942c7a3f7c66da90=1730649235,1732191192; HMACCOUNT=F209405EC9F3D75F; __fcd=N7R0EGFFACH5QSHX05667FFA7BEF95DC; Hm_lpvt_4275507ba9b9ea6b942c7a3f7c66da90=1732450686; _ga_9GWBD260K9=GS1.1.1732450370.48.1.1732450686.0.0.0"
                      }

            response = requests.get(search_url, headers=headers, timeout=5)
 
            response.raise_for_status()

            html_content = response.text

            html_soup = BeautifulSoup(html_content, "html.parser")
           
            print(f"{current_time} html_content:{html_content}")

            pattern = r"http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+"
            urls_all = re.findall(pattern, html_content)

            result_urls = set(urls_all)
            print(f"{current_time} result_urls:{result_urls}")

            valid_ips = []


            for url in result_urls:
                video_url = url + "/rtp/" + mcast

                cap = cv2.VideoCapture(video_url)

                if not cap.isOpened():
                    print(f"{current_time} {video_url} 无效")
                else:

                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"{current_time} {video_url} 的分辨率为 {width}x{height}")

                    if width > 0 and height > 0:
                        valid_ips.append(url)

                    cap.release()

            # 修改文件生成部分（约第87行开始）
            if valid_ips:
                rtp_filename = f'udpjs/{province}_{isp}.txt'
                with open(rtp_filename, 'r', encoding='utf-8') as file:
                    data = file.read()
                txt_filename = f'txt_files/{province}{isp}.txt'

                # 创建频道容器
                channel_store = {}
    
                # 处理每个有效代理IP
                for url in valid_ips:
                    new_data = data.replace("rtp://", f"{url}/rtp/")
        
                    # 解析和过滤频道
                    for line in new_data.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
            
                        # 分割频道名称和URL
                        if ',' in line:
                            channel_name, channel_url = line.split(',', 1)
                        else:
                            continue
            
                        # 频道过滤逻辑
                        keep_channel = False
                        if CTV_PATTERN.search(channel_name):
                            keep_channel = True
                        elif '卫视' in channel_name:
                            keep_channel = True
            
                        # 有效频道存储（以频道名称为键去重）
                        if keep_channel:
                            channel_store[channel_name] = channel_url
    
            # 添加定制频道
            custom_name, custom_url = CUSTOM_CHANNEL.split(',', 1)
            channel_store[custom_name] = custom_url
    
            # 生成最终内容
            formatted_channels = []
            for name, url in channel_store.items():
                # 有效性验证（可选）
                cap = cv2.VideoCapture(url)
                if cap.isOpened():
                    cap.release()
                    formatted_channels.append(f"{name},{url}")
    
            # 写入文件
            with open(txt_filename, 'w', encoding='utf-8') as new_file:
                new_file.write('\n'.join(sorted(formatted_channels)))

            print(f'已生成播放列表，保存至 {txt_filename}')

    except (requests.Timeout, requests.RequestException) as e:
        timeout_cnt += 1
        print(f"{current_time} [{province}] 搜索请求发生超时，异常次数：{timeout_cnt}")
        if timeout_cnt <= 3:
            continue
        else:
            print(f"{current_time} 搜索IPTV频道源[{province}{isp}]，超时次数过多：{timeou
print('节目表制作完成！ 文件输出在 txt_files 目录下！')

