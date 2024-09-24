import threading
from queue import Queue
import time
import random
from bs4 import BeautifulSoup
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime
from github import Github
import os

# 随机获取User-Agent
def get_random_user_agent():
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    ]
    return random.choice(USER_AGENTS)

# 模拟请求
def make_request(region):
    url = "http://www.foodieguide.com/iptvsearch/hoteliptv.php"
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": url,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "saerch": region,
        "Submit": "+",
        "city": "",
        "address": ""
    }
    response = requests.post(url, headers=headers, data=data, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        ip_addresses = []
        results = soup.find_all('div', class_='result')
        for result in results:
            # Check if it is temporarily inactive
            status_div = result.find('div', style='color: crimson;')
            if status_div and '暂时失效' in status_div.text:
                continue  # Skip temporarily inactive entries
            
            # Extract IP address
            ip_link = result.find('a', href=re.compile(r'hotellist\.html\?s=([\d\.]+:\d+)'))
            if ip_link:
                ip_address = re.search(r'hotellist\.html\?s=([\d\.]+:\d+)', ip_link['href']).group(1)
                ip_addresses.append(ip_address)
        print(ip_addresses)
        return ip_addresses
    else:
        print(f"请求失败，状态码：{response.status_code}")

# 爬取iptv
def parse_channels_and_sources(ip, file):
    time.sleep(random.uniform(2, 5))
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": f"http://www.foodieguide.com/iptvsearch/hotellist.html?s={ip}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    url = f"http://www.foodieguide.com/iptvsearch/allllist.php?s={ip}&y=false"
    retries = 2  # 最大重试次数
    retry_delay = 10  # 重试延迟时间（秒）
    total_written = 0  # 记录写入的总条数
    for _ in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  

            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.select('.result')  

            for result in results:
                channel_name_elem = result.find(class_='channel')
                if channel_name_elem:
                    div_elem = channel_name_elem.find('div', style='float: left;')
                    if div_elem:
                        channel_name = div_elem.get_text(strip=True).replace(" ", "")
                    else:
                        continue  
                else:
                    continue 

                m3u8_elem = result.find(class_='m3u8')
                if m3u8_elem:
                    live_source_elem = m3u8_elem.select_one('td[style="padding-left: 6px;"]')
                    if live_source_elem:
                        live_source = live_source_elem.get_text(strip=True).replace(" ", "")
                    else:
                        continue  
                else:
                    continue  

                # 写入文件（例如CSV格式）
                file.write(f"{channel_name},{live_source},0\n")
                total_written += 1 
            print(f"处理IP地址: {ip}，共计{total_written}条直播源")
            return total_written 

        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 500:
                print(f"遇到500错误，将暂停 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print("发生其他请求异常，将重试...")

            time.sleep(random.uniform(1, 3))  # 加入随机延迟，防止频繁请求被封IP或拒绝访问
    print(f"无法从 {url} 获取数据，请稍后重试或检查网络连接。")

# 过滤iptv 
def filter_and_modify_sources(sources):  
    """  
    过滤和修改源，并返回符合关键字的频道信息。  

    :param sources: 一个列表，包含元组(name, url, speed)，分别代表频道名称、URL和速度  
    :return: 过滤并修改后的源列表  
    """  
      
    # 定义一个字典，用于替换频道名称中的特定字符串  
    name_dict = {  
        'HD': '', '-': '', 'IPTV': '', '[': '', ']': '', '超清': '', '高清': '', '标清': '',   
        '中文国际': '', 'BRTV': '北京', '北京北京': '北京', ' ': '', '北京淘': '', '⁺': "+"  
    }  
      
    # 定义一组关键字，用于筛选包含这些关键字的频道  
    keywords = [  
        "卫视", "CCTV", "凤凰",  "淘娱乐", "淘剧场", "淘电影", "剧场",   
        "影院", "电影", "CHC", "CBN", "爱"  
    ]  
      
    # 定义一组不需要的关键字，如果频道名称包含这些关键字，则会被排除  
    no_keywords = ["4k", "奥林匹克", "教育", "精彩"]  
    unique_urls = set()  
    filtered_sources = []  
      
    for name, url, speed in sources:  
        lower_name = name.lower()  
          
        # 如果频道名称不包含任何不需要的关键字  
        if not any(no_keyword in lower_name for no_keyword in no_keywords):  
            # 替换频道名称中的特定字符串  
            for key, value in name_dict.items():  
                name = name.replace(key, value)  
              
            # 如果频道名称中包含"CCTV"，则只保留字母和数字  
            if "CCTV" in name:  
                name = re.sub(r'[^\w]', '', name)  
              
            # 如果频道名称包含任何关键字，并且该URL尚未被添加到唯一URL集合中  
            if any(keyword in name for keyword in keywords) and url not in unique_urls:  
                # 将URL添加到唯一URL集合中  
                unique_urls.add(url)  
                # 将修改后的源添加到过滤后的源列表中  
                filtered_sources.append((name, url, speed))  
      
    # 返回过滤并修改后的源列表  
    return filtered_sources  

# 读取IPTV文件
def read_itv_file(file_path):
    """
    读取ITV文件并返回频道信息
    """
    channels = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():  # 忽略空行
                channel_info = line.strip().split(',')
                if len(channel_info) >= 2:
                    name, url = channel_info[0], channel_info[1]
                    speed = float(channel_info[2]) if len(channel_info) > 2 else 0  # 如果没有速度信息，则默认为0
                    channels.append((name, url, speed))
    return channels

# 测试下载速度
def test_download_speed(url, test_duration=8):
    """
    测试下载速度
    """
    try:
        start_time = time.time()
        response = requests.get(url, timeout=test_duration + 5, stream=True)
        response.raise_for_status()

        downloaded = 0
        for chunk in response.iter_content(chunk_size=4096):
            downloaded += len(chunk)
            elapsed_time = time.time() - start_time
            if elapsed_time > test_duration:
                break

        speed = downloaded / test_duration
        return speed / (1024 * 1024)  # 转换为 MB/s

    except requests.RequestException:
        return 0

# 并行测量下载速度
def measure_download_speed_parallel(channels, max_threads=10):
    """
    并行测量下载速度
    """
    results = []
    queue = Queue()
    processed_count = 0  # 记录处理的频道数

    for channel in channels:
        queue.put(channel)

    def worker():
        nonlocal processed_count  # 使用 nonlocal 声明变量
        while not queue.empty():
            channel = queue.get()
            name, url, _ = channel
            speed = test_download_speed(url)
            results.append((name, url, speed))
            processed_count += 1  # 增加已处理的频道数
            if processed_count % 100 == 0:  # 每处理 100 个频道打印一次进展
                print(f"已处理 {processed_count} 个频道")
            queue.task_done()

    threads = []
    for _ in range(max_threads):
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)

    queue.join()

    for thread in threads:
        thread.join()

    return results

# 根据分类和排序规则对源进行分类和排序，并写入文件
def classify_and_sort_sources(sources):  
    """  
    根据分类和排序规则对源进行分类和排序，并写入文件  
  
    :param sources: 一个列表，包含元组(name, url, speed)，分别代表频道名称、URL和速度  
    """  
    # 定义分类和排序所需的字典和列表  
    categories = {  
        "央视频道": ["CCTV"],  
        "卫视频道": ["卫视", "凤凰"],  
        "影视剧场": [  
            "解密", "星影", "光影", "爱", "淘娱乐", "淘剧场", "淘电影", "电影", "影院", "剧场", "娱乐"  
        ]  
    }  
      
    yingshijuchang_order = [  
        "解密", "星影", "光影", "爱", "淘娱乐", "淘剧场", "淘电影", "电影", "影院", "剧场", "娱乐"  
    ]  
  
    # 定义排序函数，用于央视频道和卫视频道的排序  
    def channel_key(source):  
        name, _, speed = source  
        if "CCTV" in name:  
            # 如果名称中包含CCTV，则根据数字进行排序，否则设为无穷大，确保排在最后  
            match = re.search(r'\d+', name)  
            if match:  
                return (int(match.group()), name, -speed)  
            else:  
                return (float('inf'), name, -speed)  
        else:  
            # 其他情况，直接按名称和速度的负值排序  
            return (name, -speed)  
      
    # 定义排序函数，专门用于影视剧场分类的排序  
    def yingshijuchang_key(source):  
        name, _, speed = source  
        for i, category in enumerate(yingshijuchang_order):  
            if category in name:  
                # 如果名称中包含影视剧场分类中的某个词，则按预设顺序排序  
                return (i, -speed)  
        # 如果不在分类中，则排在最后  
        return (len(yingshijuchang_order), -speed)  
  
    # 初始化分类后的源数据字典  
    classified_sources = {category: [] for category in categories}  
  
    # 对源数据进行分类  
    for name, url, speed in sources:  
        for category, channels in categories.items():  
            if any(channel in name for channel in channels):  
                classified_sources[category].append((name, url, speed))  
                break  
        # 如果不属于任何已定义分类，可以选择取消注释下面的代码行，将其归入"其他频道"  
        # else:  
        #     classified_sources["其他频道"].append((name, url, speed))  
  
    # 将分类并排序后的数据写入文件  
    with open("itvlist.txt", "w", encoding="utf-8") as f:  
        for category, channel_list in classified_sources.items():  
            if channel_list:  
                f.write(f"{category},#genre#\n")  # 写入分类名称和标记  
                if category == "影视剧场":  
                    channel_list.sort(key=yingshijuchang_key)  # 影视剧场按特定顺序排序  
                else:  
                    channel_list.sort(key=channel_key)  # 其他分类按默认规则排序  
                for name, url, speed in channel_list:  
                    f.write(f"{name},{url}\n")  # 写入频道名称和URL  
                f.write("\n")  # 每个分类后添加空行作为分隔  
  
# Git
def upload_file_to_github(token, repo_name, file_path, branch='main'):
    """
    将结果上传到 GitHub
    """
    g = Github(token)
    repo = g.get_user().get_repo(repo_name)
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    git_path = file_path.split('/')[-1]
    try:
        contents = repo.get_contents(git_path, ref=branch)
    except:
        contents = None
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if contents:
            repo.update_file(contents.path, current_time, content, contents.sha, branch=branch)
            print("文件已更新")
        else:
            repo.create_file(git_path, current_time, content, branch=branch)
            print("文件已创建")
    except Exception as e:
        print("文件上传失败:", e)

# 主函数
def main():
    token = os.getenv("GITHUB_TOKEN")
    sources = read_itv_file("./itvlist.txt")
    print(len(sources))
    if len(sources) < 500:
        ip_addresses_beijing = make_request("绍兴")
        ip_addresses_CHC = make_request("CMC")
        ip_addresses = ip_addresses_zhejiang + ip_addresses_CHC
        with open("./itv.txt", 'w', encoding='utf-8') as file:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(parse_channels_and_sources, ip, file) for ip in ip_addresses]
    channels = read_itv_file("./itv.txt")
    filtered_channels = filter_and_modify_sources(channels)
    channels_with_speed = measure_download_speed_parallel(filtered_channels, max_threads=10)
    sources = [(name, url, speed) for name, url, speed in channels_with_speed if speed > 0.4]
    classify_and_sort_sources(sources)
    print(f"完成了对 {len(filtered_channels)} 个频道的处理和速度测量。")
    if token :
        upload_file_to_github(token, "IPTV", "itvlist.txt")

if __name__ == "__main__":
    main()
