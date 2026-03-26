# 车辆违法行为举报工具 - 技术方案

## 一、Context / 背景

用户需要创建一个工具，能够：
1. 上传交通违法视频
2. 自动识别视频中的违法车辆
3. 记录车牌号、违法时间、违法地点
4. 提取违法视频片段作为证据
5. 生成可用的举报材料

这是一个从零开始的全栈项目，涉及视频处理、AI模型集成、数据库设计。

---

## 二、整体架构

```
┌─────────────────────────────────────────┐
│              前端 (Vue3/React)           │
│  - 视频上传组件 (分片上传+断点续传)        │
│  - 地图组件 (高德/腾讯地图)               │
│  - 举报表单与结果展示                     │
└────────────────┬────────────────────────┘
                 │ HTTPS/REST
┌────────────────▼────────────────────────┐
│           后端 API (FastAPI)             │
│  - 用户认证/举报管理                     │
│  - 视频处理服务 (FFmpeg)                 │
│  - AI推理服务 (车辆检测+车牌识别)         │
│  - 违法检测模块                          │
│  - 报告生成服务 (PDF)                    │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│           AI/视频处理层                   │
│  - YOLOv8: 车辆检测                     │
│  - LPRNet/EasyOCR: 车牌识别             │
│  - FFmpeg: 视频转码/片段提取            │
│  - ByteTrack: 车辆跟踪                  │
└─────────────────────────────────────────┘
```

---

## 三、技术选型

### 前端
- **框架**: Vue3 + Vite + TypeScript
- **UI库**: Element Plus (PC) / uni-app (移动端可选)
- **视频播放**: video.js
- **地图**: 高德地图/腾讯地图 Web SDK
- **文件上传**: 分片上传组件

### 后端
- **框架**: FastAPI (Python 3.10+)
- **数据库**: PostgreSQL + Redis
- **对象存储**: MinIO (本地) / 阿里云OSS (可选)
- **消息队列**: RabbitMQ (异步任务)

### AI模型
| 功能 | 模型 | 说明 |
|------|------|------|
| 车辆检测 | YOLOv8 | 开源SOTA模型，支持多种车辆 |
| 车牌识别 | EasyOCR / LPRNet | 支持中文车牌 |
| 车辆跟踪 | ByteTrack | 多目标跟踪 |
| 违法检测 | 规则+时序分析 | 闯红灯、逆行、应急车道等 |

---

## 四、核心功能模块

### 4.1 视频上传模块
- 分片上传：5MB/片，支持断点续传
- 进度显示：实时上传进度
- 视频转码：统一转为H.264 MP4
- 抽帧生成缩略图

### 4.2 AI检测模块
```
视频帧 → 车辆检测(YOLOv8) → 车辆跟踪(ByteTrack)
                                      ↓
                              车牌识别(EasyOCR)
                                      ↓
                              违法检测(规则引擎)
```

### 4.3 违法检测类型
| 违法类型 | 检测方法 |
|---------|---------|
| 闯红灯 | 车辆跟踪 + 停止线区域检测 |
| 逆行 | 轨迹方向分析 |
| 占用应急车道 | 车道线检测 + 区域判断 |
| 违规变道 | 车道线检测 + 轨迹分析 |

### 4.4 举报报告生成
- PDF报告：包含时间、地点、车牌、违法类型、截图
- 视频片段：违法前后各3秒
- 关键帧截图：多角度证据

---

## 五、数据模型

```sql
-- 举报记录表
CREATE TABLE violation_reports (
    id UUID PRIMARY KEY,
    user_id UUID,

    -- 视频信息
    video_url VARCHAR(500),
    video_duration DECIMAL(10,2),
    thumbnail_url VARCHAR(500),

    -- 违法信息
    violation_type VARCHAR(50),
    violation_time TIMESTAMP,
    violation_location GEOMETRY(Point, 4326),
    address_text VARCHAR(500),

    -- 车牌信息
    license_plate VARCHAR(20),
    plate_confidence DECIMAL(5,4),

    -- 证据片段
    clip_url VARCHAR(500),
    clip_start_time DECIMAL(10,2),
    clip_end_time DECIMAL(10,2),

    -- 状态
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 六、项目结构

```
/jtwfjb
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI入口
│   │   ├── api/                 # API路由
│   │   │   └── v1/
│   │   │       ├── reports.py   # 举报相关API
│   │   │       └── upload.py     # 上传API
│   │   ├── services/            # 业务服务
│   │   │   ├── video_processor.py
│   │   │   ├── ai_detector.py
│   │   │   ├── plate_recognizer.py
│   │   │   ├── violation_detector.py
│   │   │   └── report_generator.py
│   │   ├── models/              # 数据模型
│   │   │   └── report.py
│   │   └── core/                # 核心配置
│   │       ├── config.py
│   │       └── database.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Upload.vue       # 上传页面
│   │   │   ├── ReportList.vue   # 举报列表
│   │   │   └── ReportDetail.vue # 举报详情
│   │   ├── components/
│   │   │   ├── VideoUploader.vue
│   │   │   └── MapPicker.vue
│   │   └── api/
│   │       └── report.ts
│   ├── package.json
│   └── vite.config.ts
│
└── docker-compose.yml            # 本地开发环境
```

---

## 七、实施步骤

### 第一步：项目初始化 (Day 1-2)
- 创建 Git 仓库
- 搭建后端 FastAPI 项目结构
- 搭建前端 Vue3 项目
- 配置 Docker Compose 本地开发环境

### 第二步：视频上传功能 (Day 3-5)
- 实现分片上传API
- 前端上传组件
- FFmpeg 视频处理服务
- 视频转码与抽帧

### 第三步：AI模型集成 (Day 6-10)
- YOLOv8 车辆检测服务
- EasyOCR 车牌识别
- ByteTrack 车辆跟踪
- 违法检测规则引擎

### 第四步：举报流程完善 (Day 11-14)
- 举报表单与提交
- 地图位置选择
- 报告生成服务 (PDF)
- 结果展示与下载

### 第五步：测试与部署 (Day 15-20)
- 单元测试
- 功能测试
- 性能优化
- 部署上线

---

## 八、验证方式

1. **视频上传测试**: 上传一段包含车辆的测试视频，验证转码、抽帧功能
2. **AI检测测试**: 验证车辆检测、车牌识别的准确率
3. **违法检测测试**: 使用已知违法视频（闯红灯等）验证检测效果
4. **报告生成测试**: 验证PDF报告内容完整性
5. **端到端测试**: 完整流程：上传→检测→生成报告→下载

---

## 九、关键依赖

```txt
# backend/requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
redis==5.0.1
python-multipart==0.0.6
ffmpeg-python==0.2.0
ultralytics==8.0.200  # YOLOv8
easyocr==1.7.1
opencv-python==4.9.0.80
paddleocr==2.7.3
weasyprint==60.1
```

```json
// frontend/package.json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "element-plus": "^2.5.0",
    "axios": "^1.6.0",
    "video.js": "^8.6.0",
    "@amap/amap-jsapi-loader": "^1.0.0"
  }
}
```

---

## 十、已确认需求

| 问题 | 选择 | 说明 |
|------|------|------|
| 部署方式 | 本地运行 | 适合个人/小团队使用 |
| 视频来源 | 行车记录仪 | 横向拍摄，视角相对固定，利于检测 |
| 用户系统 | 匿名举报 | 无需登录，直接使用 |

### 简化后的架构

由于是本地运行 + 匿名举报：
- **数据库**: SQLite (轻量级) 或 PostgreSQL
- **文件存储**: 本地磁盘 + MinIO (可选)
- **用户管理**: 跳过，无需实现
- **部署**: Docker Compose 一键启动

### 行车记录仪视频特点及适配

行车记录仪视频特点：
- 分辨率通常为 1080P/2K/4K
- 横向视角，视角相对固定
- 有时会带有GPS信息和水印
- 可能有机动车、非机动车、行人混合

适配方案：
- 使用 YOLOv8 的车辆检测模型，针对性优化
- 利用视频的GPS信息获取违法地点（如有）
- 支持常见格式：MP4、MOV、AVI
