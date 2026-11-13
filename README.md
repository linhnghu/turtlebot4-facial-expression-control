# TurtleBot 4 — Nhận diện biểu cảm khuôn mặt và điều khiển robot

Dùng **webcam thật**, **DeepFace + OpenCV** và **ROS 2 Humble** để điều khiển
TurtleBot theo sáu biểu cảm khuôn mặt. Một lệnh mở robot mô phỏng trong
Gazebo Fortress cùng cửa sổ nhận diện trực tiếp. Có thể chuyển sang robot
đã cung cấp `/cmd_vel` và `/odom`.

| Biểu cảm | Hành động | Mặc định |
|---|---|---|
| Happy — Vui vẻ | Đi cong sang trái | 0.10 m/s, +0.45 rad/s, 3 giây |
| Sad — Buồn | Đi cong sang phải | 0.10 m/s, −0.45 rad/s, 3 giây |
| Neutral — Bình thường | Dừng tại chỗ | Vận tốc bằng 0 |
| Angry — Tức giận | Lùi nhẹ | Khoảng 12 cm, 0.10 m/s |
| Surprise — Ngạc nhiên | Xoay một vòng tại chỗ | +0.45 rad/s, đo góc bằng odometry |
| Fear — Sợ hãi | Tiến nhẹ | Khoảng 20 cm, 0.10 m/s |

## Cài đặt và chạy nhanh

Môi trường đã kiểm chứng: **Ubuntu 22.04, ROS 2 Humble, Python 3.10,
Gazebo Fortress và TurtleBot 4 Lite**. Cần webcam USB hoặc webcam laptop,
màn hình desktop và Internet cho lần cài thư viện/trọng số đầu tiên.

Sau khi cài ROS 2 Humble và cấu hình kho APT của ROS:

```bash
sudo apt update
sudo apt install python3-venv python3-pip python3-pytest \
  python3-colcon-common-extensions ros-humble-turtlebot4-simulator \
  ros-humble-irobot-create-nodes ros-humble-ros-gz-bridge

git clone https://github.com/linhnghu/turtlebot4-facial-expression-control.git ~/turtlebot4_emotion_ws
cd ~/turtlebot4_emotion_ws
./setup_emotion.bash
./run_emotion_demo.bash
```

Nếu đang dùng workspace gốc trên máy đã cài sẵn, chỉ cần:

```bash
cd ~/ros2_ws
./run_emotion_demo.bash
```

Setup tạo `.venv-emotion` riêng, cài phiên bản thư viện tương thích với ROS,
tải mô hình Emotion vào `.models/emotion/.deepface/weights` và build package
`turtlebot4_emotion`. TensorFlow cần tải khoảng 475 MB; lần cài đầu có thể
mất vài phút. Sau setup, nhận diện chạy cục bộ, không gửi ảnh lên dịch vụ AI.

## Thao tác demo

1. Đợi TurtleBot xuất hiện trong Gazebo và cửa sổ webcam có kết quả nhận diện.
2. Để một khuôn mặt rõ, đủ sáng, gần chính diện trong khung hình.
3. Giữ biểu cảm tối thiểu **0.6 giây** và **3 kết quả nhận diện hợp lệ**.
   Ngưỡng điểm số mặc định là **0.65**.
4. Robot thực hiện chuyển động tương ứng rồi dừng. Giữ nguyên biểu cảm
   không làm robot lặp chuyển động liên tục.
5. Đưa về **Neutral** ổn định trước khi lặp cùng một biểu cảm.

Neutral dừng robot ngay khi có kết quả nhận diện, kể cả điểm số thấp.
Đổi biểu cảm giữa lúc chạy sẽ dừng hành động hiện tại; biểu cảm mới chỉ
kích hoạt sau khi đạt điều kiện ổn định. Nhấn **Q**, **Esc**, đóng cửa sổ
webcam hoặc **Ctrl+C** trong terminal để kết thúc.

Cửa sổ hiển thị ảnh webcam, khung khuôn mặt, biểu cảm, điểm số, số mặt,
tuổi ảnh và trạng thái điều khiển. Surprise dùng tổng góc quay từ `/odom`
để hoàn tất một vòng; Angry/Fear dùng quãng đường đo được. Quãng lùi 12 cm
được chọn để giữ cơ chế giới hạn backup của Create 3 trong mô phỏng.

## Chọn camera và chế độ chạy

```bash
# Camera khác
./run_emotion_demo.bash camera_index:=2

# Không mở giao diện Gazebo, vẫn hiển thị webcam
./run_emotion_demo.bash gazebo_gui:=false

# Không có desktop: không mở cửa sổ
./run_emotion_demo.bash gazebo_gui:=false show_window:=false

# Dùng robot hoặc simulator đã chạy sẵn
./run_emotion_demo.bash simulation:=false

# Robot có namespace
./run_emotion_demo.bash simulation:=false \
  cmd_vel_topic:=/robot/cmd_vel odom_topic:=/robot/odom
```

Mặc định demo dùng ROS domain **69**, localhost và Gazebo partition riêng.
Trong terminal phụ, chạy `source emotion_env.bash` từ thư mục repo.
Với robot thật qua LAN, đặt `EMOTION_DOMAIN_ID` trùng domain của robot
và `EMOTION_LOCALHOST_ONLY=0` trước khi chạy ở mọi terminal liên quan.
Robot phải nhận `geometry_msgs/msg/Twist`; kiểu TwistStamped cần bộ chuyển
đổi riêng. Chỉ để một nguồn điều khiển vận tốc hoạt động trong cùng domain.

## Dừng và quan sát trạng thái

```bash
source emotion_env.bash
ros2 topic echo /emotion/status
ros2 service call /emotion/stop std_srvs/srv/Trigger '{}'
ros2 service call /emotion/reset std_srvs/srv/Trigger '{}'
```

`stop` giữ chốt dừng; sau `reset`, cần đưa mặt về Neutral ổn định để nhận
lệnh mới. Không có mặt, nhiều mặt, nhãn Disgust/unknown, điểm thấp hoặc kết
quả sai/quá hạn đều làm robot dừng. Mất kết quả nhận diện hơn 1.5 giây hoặc
odometry quá 0.6 giây cũng dừng. Mọi chuyển động bị giới hạn tối đa 30 giây.

Controller chạy riêng ở 20 Hz, nên suy luận chậm không chặn watchdog.
Webcam chỉ giữ frame mới nhất. Các node webcam/controller phải chạy cùng
máy vì timestamp nhận diện dùng đồng hồ monotonic. Độ trễ dừng khi suy luận
treo phụ thuộc timeout cộng một chu kỳ điều khiển khoảng 50 ms.

Chương trình chưa có tránh vật cản. Khi thử robot thật, dùng vùng trống và
nút dừng của base. Nếu controller bị SIGKILL hoặc máy mất nguồn, cần watchdog
nhận `/cmd_vel` của base robot.

## Cấu hình và mã nguồn

Thông số nằm trong
[`src/turtlebot4_emotion/config/emotion.yaml`](src/turtlebot4_emotion/config/emotion.yaml).
Có thể dùng file khác bằng `config:=/duong/dan/emotion.yaml`.

```text
Webcam → DeepFace/OpenCV → /emotion/detection
                                 ↓
                       emotion_controller ← /odom
                                 ↓
                              /cmd_vel
```

| Thành phần | Vị trí |
|---|---|
| Bộ lọc biểu cảm và chuyển động | [core.py](src/turtlebot4_emotion/turtlebot4_emotion/core.py) |
| Nhận ảnh, suy luận và giao diện | [camera.py](src/turtlebot4_emotion/turtlebot4_emotion/camera.py) |
| Node điều khiển ROS 2 | [controller.py](src/turtlebot4_emotion/turtlebot4_emotion/controller.py) |
| Launch, world và cấu hình | [turtlebot4_emotion](src/turtlebot4_emotion) |
| Tài liệu kỹ thuật và ROS interface | [README package](src/turtlebot4_emotion/README.md) |
| Kết quả và phạm vi kiểm chứng | [VALIDATION.md](src/turtlebot4_emotion/VALIDATION.md) |
| Bằng chứng kiểm tra | [artifacts/emotion](artifacts/emotion) |

Repo chứa đầy đủ source các package trong workspace, cùng maps, scripts,
tài liệu và báo cáo kiểm chứng. Build/install/log, môi trường Python, trọng
số tải về và video webcam thô không nằm trong repo. Các bài khác có hướng
dẫn riêng: [SLAM/Nav2](README_TURTLEBOT4.md),
[YOLO](README_VISION_NAV.md), [cử chỉ tay](README_GESTURE_CONTROL.md),
[giọng nói](README_VOICE_NAV.md), cùng các package HRI trong `src`.
Các lệnh setup ở trên chỉ build phần biểu cảm; các bài khác cần setup riêng.

## Kiểm thử và kết quả

```bash
source emotion_env.bash
PYTHONPATH=src/turtlebot4_emotion python3 -m pytest -q src/turtlebot4_emotion/test
```

Kiểm tra chuyển động trong Gazebo bằng biểu cảm JSON tổng hợp:

```bash
# Terminal 1
./run_emotion_demo.bash camera:=false gazebo_gui:=false
# Terminal 2
source emotion_env.bash
python3 src/turtlebot4_emotion/test/check_gazebo.py
```


## Xử lý lỗi thường gặp

- **Không mở được webcam:** đóng ứng dụng đang dùng camera, kiểm tra
  `ls /dev/video*` rồi đổi `camera_index`. Một số thiết bị chỉ chứa metadata.
- **Robot đứng yên:** xem `/emotion/status`; kiểm tra `/odom`, số khuôn mặt,
  điểm số và độ ổn định. Giữ Neutral để cho phép lặp cùng lệnh.
- **Không tìm thấy package:** chạy lại `./setup_emotion.bash`, rồi mở terminal
  mới hoặc `source emotion_env.bash`.
- **Lỗi tải thư viện/trọng số:** kiểm tra Internet và chạy lại setup.
- **Gazebo chậm:** dùng `gazebo_gui:=false`; quỹ đạo cong tính theo thời gian
  thực nên quãng đường mô phỏng phụ thuộc real-time factor.

## Giấy phép

Mã nguồn của dự án dùng [Apache-2.0](LICENSE). DeepFace, TensorFlow, OpenCV,
trọng số và tài nguyên mô phỏng giữ giấy phép của từng tác giả. World biểu
cảm dẫn xuất từ TurtleBot 4 simulator; ghi công nằm trong file SDF.
Tài nguyên người cho bài YOLO có [ghi công riêng](src/turtlebot4_vision_nav/models/ATTRIBUTION.md).
