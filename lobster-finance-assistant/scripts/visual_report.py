# -*- coding: utf-8 -*-
"""
可视化报告生成模块

功能：
- HTML 报告生成
- PDF 导出
- 图表绘制
"""

import pandas as pd
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class VisualReportGenerator:
    """可视化报告生成器"""
    
    def __init__(self, output_dir: str = 'reports'):
        self.output_dir = output_dir
    
    def generate_html_report(self, stock_data: Dict[str, Any], output_file: str) -> str:
        """
        生成 HTML 报告
        
        Args:
            stock_data: 股票数据
            output_file: 输出文件名
            
        Returns:
            文件路径
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{stock_data.get('symbol', 'N/A')} - 投资分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #e3f2fd; border-radius: 8px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1976d2; }}
        .metric-label {{ font-size: 12px; color: #666; }}
        .recommendation {{ padding: 15px; background: #c8e6c9; border-radius: 8px; margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{stock_data.get('symbol', 'N/A')} - {stock_data.get('name', 'N/A')}</h1>
        <p>报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>核心指标</h2>
        <div class="metric">
            <div class="metric-value">¥{stock_data.get('price', 0):.2f}</div>
            <div class="metric-label">当前价格</div>
        </div>
        <div class="metric">
            <div class="metric-value">{stock_data.get('pe', 0):.2f}</div>
            <div class="metric-label">PE(TTM)</div>
        </div>
        <div class="metric">
            <div class="metric-value">{stock_data.get('pb', 0):.2f}</div>
            <div class="metric-label">PB</div>
        </div>
        <div class="metric">
            <div class="metric-value">{stock_data.get('roe', 0):.2f}%</div>
            <div class="metric-label">ROE</div>
        </div>
        <div class="metric">
            <div class="metric-value">{stock_data.get('score', 0):.1f}</div>
            <div class="metric-label">综合评分</div>
        </div>
    </div>
    
    <div class="recommendation">
        <h2>投资建议</h2>
        <p><strong>评级：</strong>{stock_data.get('recommendation', 'N/A')}</p>
        <p><strong>目标价：</strong>¥{stock_data.get('target_price', 0):.2f}</p>
        <p><strong>止损价：</strong>¥{stock_data.get('stop_loss', 0):.2f}</p>
        <p><strong>置信度：</strong>{stock_data.get('confidence', 0)}%</p>
    </div>
    
    <div class="section">
        <h2>估值分析</h2>
        <table>
            <tr><th>指标</th><th>当前值</th><th>行业中位</th><th>历史分位</th></tr>
            <tr><td>PE</td><td>{stock_data.get('pe', 0):.2f}</td><td>-</td><td>-</td></tr>
            <tr><td>PB</td><td>{stock_data.get('pb', 0):.2f}</td><td>-</td><td>-</td></tr>
            <tr><td>PS</td><td>{stock_data.get('ps', 0):.2f}</td><td>-</td><td>-</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>成长性分析</h2>
        <table>
            <tr><th>指标</th><th>值</th></tr>
            <tr><td>营收增长率</td><td>{stock_data.get('revenue_growth', 0):.2f}%</td></tr>
            <tr><td>净利润增长率</td><td>{stock_data.get('net_profit_growth', 0):.2f}%</td></tr>
            <tr><td>ROE</td><td>{stock_data.get('roe', 0):.2f}%</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>风险提示</h2>
        <ul>
            <li>市场风险：宏观经济波动</li>
            <li>行业风险：政策变化</li>
            <li>公司风险：经营不确定性</li>
        </ul>
    </div>
    
    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
        <p>免责声明：本报告仅供参考，不构成投资建议。市场有风险，投资需谨慎。</p>
    </div>
</body>
</html>
"""
        
        file_path = f"{self.output_dir}/{output_file}"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"HTML report generated: {file_path}")
        return file_path
    
    def generate_pdf_report(self, html_file: str, output_file: str) -> str:
        """
        生成 PDF 报告（需要 wkhtmltopdf）
        
        Args:
            html_file: HTML 文件路径
            output_file: 输出 PDF 文件名
            
        Returns:
            文件路径
        """
        try:
            import pdfkit
            pdfkit.from_file(html_file, f"{self.output_dir}/{output_file}")
            logger.info(f"PDF report generated: {output_file}")
            return f"{self.output_dir}/{output_file}"
        except ImportError:
            logger.error("pdfkit not installed. Run: pip install pdfkit")
            return ""


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    generator = VisualReportGenerator()
    
    test_data = {
        'symbol': '600519',
        'name': '贵州茅台',
        'price': 1800.00,
        'pe': 35.5,
        'pb': 12.3,
        'roe': 28.5,
        'score': 85,
        'recommendation': '买入',
        'target_price': 2000.00,
        'stop_loss': 1600.00,
        'confidence': 80,
    }
    
    html_file = generator.generate_html_report(test_data, '600519_report.html')
    print(f"Generated: {html_file}")
