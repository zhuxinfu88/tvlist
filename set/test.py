# 用OpenCV读取视频
cap = cv2.VideoCapture(video_url)

# 检查视频是否成功打开
if not cap.isOpened():
    print(f"{current_time} {video_url} 无效")
else:
    # 读取视频的宽度和高度
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"{current_time} {video_url} 的分辨率为 {width}x{height}")
    # 检查分辨率是否大于0
    if width > 0 and height > 0:
        valid_ips.append(ip_port)
    # 关闭视频流
    cap.release()
