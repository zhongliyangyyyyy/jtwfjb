from pathlib import Path
from typing import Dict
import datetime

from app.core.config import settings
from app.models.report import Report

# 违法类型映射
VIOLATION_TYPES = {
    "red_light": "违反道路交通信号灯通行",
    "wrong_way": "逆向行驶",
    "emergency_lane": "在应急车道行驶",
    "illegal_parking": "违规停放",
    "illegal_change": "违规变道",
    "overspeed": "超速行驶",
    "fatigue_driving": "疲劳驾驶",
}


class ReportGenerator:
    """报告生成服务 - 生成PDF举报材料"""

    def async_generate(self, report: Report) -> str:
        """同步生成PDF（内部使用）"""
        return self._generate_pdf_sync(report)

    async def generate(self, report: Report) -> str:
        """生成PDF举报报告"""
        return self._generate_pdf_sync(report)

    def _generate_pdf_sync(self, report: Report) -> str:
        """同步生成PDF"""
        from weasyprint import HTML, CSS

        output_path = settings.REPORTS_DIR / f"{report.id}.pdf"

        # 构建HTML内容
        html_content = self._build_html(report)

        # 生成PDF
        HTML(string=html_content).write_pdf(str(output_path))

        return str(output_path)

    def _build_html(self, report: Report) -> str:
        """构建HTML模板"""
        violation_desc = VIOLATION_TYPES.get(
            report.violation_type,
            report.violation_type or "未知违法行为"
        )

        violation_time_str = ""
        if report.violation_time:
            if isinstance(report.violation_time, str):
                violation_time_str = report.violation_time
            else:
                violation_time_str = report.violation_time.strftime("%Y年%m月%d日 %H:%M:%S")

        created_at_str = ""
        if report.created_at:
            if isinstance(report.created_at, str):
                created_at_str = report.created_at
            else:
                created_at_str = report.created_at.strftime("%Y年%m月%d日 %H:%M:%S")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>交通违法举报报告</title>
    <style>
        body {{
            font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #e74c3c;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #e74c3c;
            margin: 0;
            font-size: 28px;
        }}
        .header p {{
            color: #666;
            margin: 10px 0 0 0;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section-title {{
            background: #f8f9fa;
            padding: 10px 15px;
            border-left: 4px solid #e74c3c;
            font-weight: bold;
            margin-bottom: 15px;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .info-table td {{
            padding: 8px 12px;
            border: 1px solid #ddd;
        }}
        .info-table td:first-child {{
            background: #f8f9fa;
            font-weight: bold;
            width: 120px;
        }}
        .highlight {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .evidence {{
            margin-top: 15px;
        }}
        .evidence img {{
            max-width: 100%;
            border: 1px solid #ddd;
            margin: 5px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: right;
            color: #666;
            font-size: 14px;
        }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>交通违法举报报告</h1>
        <p>编号: {report.id}</p>
    </div>

    <div class="warning">
        <strong>郑重声明：</strong>本报告由系统自动生成，内容真实有效。举报人愿对举报内容的真实性负责。
    </div>

    <div class="section">
        <div class="section-title">一、违法车辆信息</div>
        <table class="info-table">
            <tr>
                <td>车牌号码</td>
                <td class="highlight">{report.license_plate or "未能识别"}</td>
            </tr>
            <tr>
                <td>车牌置信度</td>
                <td>{"{:.1%}".format(report.plate_confidence) if report.plate_confidence else "N/A"}</td>
            </tr>
            <tr>
                <td>车辆类型</td>
                <td>{report.vehicle_type or "未知"}</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">二、违法行为信息</div>
        <table class="info-table">
            <tr>
                <td>违法类型</td>
                <td class="highlight">{violation_desc}</td>
            </tr>
            <tr>
                <td>违法时间</td>
                <td>{violation_time_str or "未知"}</td>
            </tr>
            <tr>
                <td>违法地点</td>
                <td>{report.violation_location or "未知"}</td>
            </tr>
            <tr>
                <td>GPS坐标</td>
                <td>{"{:.6f}, {:.6f}".format(report.gps_latitude, report.gps_longitude) if report.gps_latitude and report.gps_longitude else "无"}</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">三、视频证据信息</div>
        <table class="info-table">
            <tr>
                <td>原始视频</td>
                <td>{report.video_filename}</td>
            </tr>
            <tr>
                <td>视频时长</td>
                <td>{"{:.1f} 秒".format(report.video_duration) if report.video_duration else "未知"}</td>
            </tr>
            <tr>
                <td>违法片段</td>
                <td>{"{:.1f}s - {:.1f}s".format(report.clip_start_time, report.clip_end_time) if report.clip_start_time and report.clip_end_time else "无"}</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">四、证据材料</div>
        <p>本举报包含以下证据材料：</p>
        <ul>
            <li>原始执法视频文件</li>
            <li>违法片段视频（标注时间段）</li>
            <li>视频关键帧截图</li>
        </ul>
        <p style="color: #666; font-size: 14px;">
            注：证据材料请查看附件或联系系统管理员获取。
        </p>
    </div>

    <div class="section">
        <div class="section-title">五、举报信息</div>
        <table class="info-table">
            <tr>
                <td>举报时间</td>
                <td>{created_at_str}</td>
            </tr>
            <tr>
                <td>举报编号</td>
                <td>{report.id}</td>
            </tr>
            <tr>
                <td>处理状态</td>
                <td>待审核</td>
            </tr>
        </table>
    </div>

    <div class="footer">
        <p>举报系统生成时间：{datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}</p>
        <p>交通违法举报平台</p>
    </div>
</body>
</html>
"""
        return html
