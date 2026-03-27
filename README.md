# jtwfjb - 车辆违法行为举报工具

基于 AI 的交通违法视频举报工具，支持视频上传、车辆检测、车牌识别、违法检测和报告生成。

## 功能特性

- 📹 **视频上传** - 分片上传 + 断点续传，统一转码为 H.264 MP4
- 🚗 **车辆检测** - YOLOv8 实时检测视频中的车辆
- 🔤 **车牌识别** - EasyOCR 支持中文车牌识别
- 📍 **轨迹跟踪** - ByteTrack 多目标跟踪
- ⚠️ **违法检测** - 闯红灯、逆行、占用应急车道、违规变道
- 📄 **报告生成** - PDF 格式举报材料，包含关键帧截图和视频片段

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue3 + Vite + TypeScript + Element Plus |
| 后端 | FastAPI (Python 3.10+) |
| 数据库 | PostgreSQL + Redis |
| AI | YOLOv8 / EasyOCR / ByteTrack |
| 视频处理 | FFmpeg |
| 部署 | Docker Compose |

## 项目结构

```
jtwfjb/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/      # API 路由
│   │   ├── services/    # 业务服务 (视频处理/AI检测/报告生成)
│   │   ├── models/      # 数据模型
│   │   └── core/        # 核心配置
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/            # Vue3 前端
│   ├── src/
│   │   ├── views/       # 页面 (上传/列表/详情)
│   │   ├── components/  # 组件 (视频上传/地图选择)
│   │   └── api/         # API 调用
│   └── package.json
├── docker-compose.yml   # 一键启动本地开发环境
└── PLAN.md             # 完整技术方案
```

## 快速开始

### 环境要求

- Docker & Docker Compose
- Python 3.10+ (本地开发)
- Node.js 18+ (本地前端开发)

### 启动服务

```bash
# 克隆仓库后，一键启动全部服务
docker-compose up -d
```

前端：http://localhost:3000
后端 API：http://localhost:8000
API 文档：http://localhost:8000/docs

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## 违法检测类型

| 违法类型 | 检测方式 |
|---------|---------|
| 闯红灯 | 车辆跟踪 + 停止线区域检测 |
| 逆行 | 轨迹方向分析 |
| 占用应急车道 | 车道线检测 + 区域判断 |
| 违规变道 | 车道线检测 + 轨迹分析 |

## 使用流程

1. **上传视频** - 上传行车记录仪视频（支持 MP4/MOV/AVI）
2. **AI 检测** - 自动检测车辆、识别车牌、分析违法行
3. **生成报告** - 自动生成 PDF 举报材料，包含时间、地点、车牌、截图证据
4. **提交举报** - 下载报告后提交至交管部门

## License

MIT
