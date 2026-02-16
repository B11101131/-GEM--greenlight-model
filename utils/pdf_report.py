"""
PDF 報告產生器

從原始 greenlight_model.py 搬移並增強，支援更多報告區段。
"""
import io
from datetime import datetime
from typing import Optional, Tuple

import matplotlib.pyplot as plt


def generate_pdf_report(
    project_name: str,
    genre: str,
    budget: float,
    marketing_pa: float,
    expected_profit: float,
    expected_roi: float,
    prob_loss: float,
    p5: float,
    p95: float,
    status: str,
    recommendation: str,
    fig_profit: plt.Figure,
    fig_sensitivity: Optional[plt.Figure] = None,
    var_text: Optional[str] = None,
    breakeven_text: Optional[str] = None,
) -> Tuple[bytes, bool]:
    """
    產生 PDF 報告並回傳 (bytes, font_warning)。

    Args:
        project_name: 專案名稱
        genre: 類型
        budget: 製作預算
        marketing_pa: 行銷費用
        expected_profit: 預期淨利
        expected_roi: 預期 ROI
        prob_loss: 虧損機率
        p5, p95: 信賴區間
        status: 決策狀態
        recommendation: 建議文字
        fig_profit: 獲利分佈圖
        fig_sensitivity: 敏感度圖（可選）
        var_text: VaR 摘要文字（可選）
        breakeven_text: 損益兩平摘要文字（可選）

    Returns:
        (PDF bytes, 是否有字體警告)
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import inch

    # 嘗試註冊中文字體
    font_warning = False
    try:
        pdfmetrics.registerFont(TTFont('MingLiU', 'mingliu.ttc'))
        chinese_font = 'MingLiU'
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont('SimHei', 'simhei.ttf'))
            chinese_font = 'SimHei'
        except Exception:
            chinese_font = 'Helvetica'
            font_warning = True

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=50, bottomMargin=50)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ChineseTitle', fontName=chinese_font,
        fontSize=20, alignment=1, spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name='ChineseBody', fontName=chinese_font,
        fontSize=11, leading=16,
    ))
    styles.add(ParagraphStyle(
        name='ChineseHeading', fontName=chinese_font,
        fontSize=14, spaceAfter=10, spaceBefore=15,
    ))

    elements = []

    # 標題
    elements.append(Paragraph("影視專案投資評估報告", styles['ChineseTitle']))
    elements.append(Paragraph(f"專案名稱：{project_name}", styles['ChineseBody']))
    elements.append(Paragraph(
        f"報告日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['ChineseBody'],
    ))
    elements.append(Spacer(1, 20))

    # 一、專案摘要
    elements.append(Paragraph("一、專案摘要", styles['ChineseHeading']))
    summary_data = [
        ['項目', '數值'],
        ['專案類型', genre],
        ['製作預算', f'{budget:.1f} 百萬 TWD'],
        ['行銷宣發費', f'{marketing_pa:.1f} 百萬 TWD'],
        ['總成本', f'{budget + marketing_pa:.1f} 百萬 TWD'],
    ]
    elements.append(_make_table(summary_data, chinese_font))
    elements.append(Spacer(1, 20))

    # 二、風險評估結果
    elements.append(Paragraph("二、風險評估結果", styles['ChineseHeading']))
    risk_data = [
        ['指標', '數值'],
        ['預估平均淨利', f'{expected_profit:.1f} 百萬 TWD'],
        ['預估 ROI', f'{expected_roi:.1f}%'],
        ['虧損風險機率', f'{prob_loss:.1f}%'],
        ['95% 信心區間下限', f'{p5:.1f} 百萬 TWD'],
        ['95% 信心區間上限', f'{p95:.1f} 百萬 TWD'],
    ]
    elements.append(_make_table(risk_data, chinese_font))
    elements.append(Spacer(1, 20))

    # 三、投資決策建議
    elements.append(Paragraph("三、投資決策建議", styles['ChineseHeading']))
    clean_status = status.replace('🟢 ', '').replace('🟡 ', '').replace('🔴 ', '')
    elements.append(Paragraph(f"決策狀態：{clean_status}", styles['ChineseBody']))
    elements.append(Paragraph(f"建議說明：{recommendation}", styles['ChineseBody']))
    elements.append(Spacer(1, 20))

    # 四、模擬結果分佈圖
    elements.append(Paragraph("四、模擬結果分佈圖", styles['ChineseHeading']))
    img_buffer = io.BytesIO()
    fig_profit.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    elements.append(Image(img_buffer, width=6 * inch, height=3.5 * inch))

    # 五、敏感度分析（可選）
    if fig_sensitivity is not None:
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("五、敏感度分析", styles['ChineseHeading']))
        sens_buffer = io.BytesIO()
        fig_sensitivity.savefig(sens_buffer, format='png', dpi=150, bbox_inches='tight')
        sens_buffer.seek(0)
        elements.append(Image(sens_buffer, width=6 * inch, height=3.5 * inch))

    # 六、VaR 風險值（可選）
    section_num = 6
    if var_text:
        elements.append(Spacer(1, 15))
        elements.append(Paragraph(
            f"{'六' if section_num == 6 else '七'}、風險值報告 (VaR)", styles['ChineseHeading'],
        ))
        elements.append(Paragraph(var_text, styles['ChineseBody']))
        section_num += 1

    # 七、損益兩平分析（可選）
    if breakeven_text:
        elements.append(Spacer(1, 15))
        num_map = {6: '六', 7: '七', 8: '八'}
        elements.append(Paragraph(
            f"{num_map.get(section_num, str(section_num))}、損益兩平分析",
            styles['ChineseHeading'],
        ))
        elements.append(Paragraph(breakeven_text, styles['ChineseBody']))

    # 頁尾
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "本報告由 GEM (Greenlight Evaluation Model) 自動產生，僅供參考。",
        styles['ChineseBody'],
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue(), font_warning


def _make_table(data: list, font_name: str):
    """建立統一格式的 PDF 表格"""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(data, colWidths=[200, 200])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    return table
