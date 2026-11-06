from __future__ import annotations

import math
import os
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.legends import Legend


NAVY = colors.HexColor("#17345C")
BLUE = colors.HexColor("#3478C8")
PALE_BLUE = colors.HexColor("#EFF6FF")
GREEN = colors.HexColor("#1E9A74")
RED = colors.HexColor("#D65A63")
INK = colors.HexColor("#26364A")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#DCE6F0")
_FONT_REGISTERED = False


def _register_fonts() -> tuple[str, str]:
    """Use an embedded Unicode font so the Indian rupee glyph renders in PDF."""
    global _FONT_REGISTERED
    regular_candidates = [
        os.getenv("REPORT_FONT_REGULAR"),
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    bold_candidates = [
        os.getenv("REPORT_FONT_BOLD"),
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ]
    regular_path = next((Path(path) for path in regular_candidates if path and Path(path).is_file()), None)
    bold_path = next((Path(path) for path in bold_candidates if path and Path(path).is_file()), None)
    if regular_path is None:
        raise RuntimeError("A Unicode font is required to render Indian Rupee amounts in the PDF.")
    if not _FONT_REGISTERED:
        pdfmetrics.registerFont(TTFont("FinPrepSans", str(regular_path)))
        pdfmetrics.registerFont(TTFont("FinPrepSans-Bold", str(bold_path or regular_path)))
        _FONT_REGISTERED = True
    return "FinPrepSans", "FinPrepSans-Bold"


def _finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def format_inr(value: Any) -> str:
    number = _finite_number(value)
    if number is None:
        return "Not available"
    sign = "-" if number < 0 else ""
    whole, fraction = f"{abs(number):.2f}".split(".")
    if len(whole) > 3:
        groups = [whole[-3:]]
        prefix = whole[:-3]
        while prefix:
            groups.insert(0, prefix[-2:])
            prefix = prefix[:-2]
        whole = ",".join(groups)
    return f"{sign}₹{whole}.{fraction}"


def _count(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return "Not available"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError, OverflowError):
        return "Not available"


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _heading(text: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    return [Spacer(1, 5 * mm), _paragraph(text, styles["section"]), HRFlowable(width="100%", thickness=0.8, color=LINE, spaceAfter=3 * mm)]


def _metric_cards(report: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    analysis = report.get("analysis") or {}
    income = _finite_number(analysis.get("total_income"))
    expenses = _finite_number(analysis.get("total_expenses"))
    net_flow = income - expenses if income is not None and expenses is not None else None
    metrics = [
        ("TOTAL INCOME", format_inr(income), GREEN),
        ("TOTAL EXPENSES", format_inr(expenses), RED),
        ("NET CASH FLOW", format_inr(net_flow), BLUE),
        ("AVERAGE TRANSACTION", format_inr(analysis.get("average_transaction")), NAVY),
    ]
    cards = []
    for label, value, color in metrics:
        card_width = (A4[0] - 36 * mm) / 4 - 16
        card = Table([
            [_paragraph(label, styles["metric_label"])],
            [_paragraph(value, ParagraphStyle("metric_value", parent=styles["metric_value"], textColor=color))],
        ], colWidths=[card_width])
        card.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        cards.append(card)
    table = Table([cards], colWidths=[(A4[0] - 36 * mm) / 4] * 4)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    return table


def _chart_styles(chart: Any, font_name: str) -> None:
    chart.valueAxis.labelTextFormat = format_inr
    chart.valueAxis.labels.fontName = font_name
    chart.valueAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fontName = font_name
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.strokeColor = LINE
    chart.valueAxis.strokeColor = LINE
    chart.valueAxis.gridStrokeColor = LINE
    chart.valueAxis.gridStrokeWidth = 0.5


def _income_expense_chart(report: dict[str, Any], font_name: str) -> Drawing | None:
    analysis = report.get("analysis") or {}
    income = _finite_number(analysis.get("total_income"))
    expenses = _finite_number(analysis.get("total_expenses"))
    if income is None or expenses is None:
        return None
    drawing = Drawing(470, 210)
    chart = VerticalBarChart()
    chart.x = 52
    chart.y = 30
    chart.width = 360
    chart.height = 140
    chart.data = [[income], [expenses]]
    chart.categoryAxis.categoryNames = ["Current dataset"]
    chart.barWidth = 42
    chart.groupSpacing = 24
    chart.bars[0].fillColor = GREEN
    chart.bars[1].fillColor = RED
    chart.valueAxis.valueMin = 0
    maximum = max(income, expenses)
    chart.valueAxis.valueMax = maximum * 1.15 if maximum > 0 else 1
    chart.valueAxis.valueStep = max(chart.valueAxis.valueMax / 5, 0.01)
    _chart_styles(chart, font_name)
    legend = Legend()
    legend.colorNamePairs = [(GREEN, "Income"), (RED, "Expenses")]
    legend.fontName = font_name
    legend.fontSize = 8
    legend.x = 155
    legend.y = 195
    drawing.add(chart)
    drawing.add(legend)
    return drawing


def _category_chart(report: dict[str, Any], font_name: str) -> tuple[Drawing | None, bool]:
    analysis = report.get("analysis") or {}
    categories = analysis.get("category_summary")
    if not isinstance(categories, list):
        return None, False
    complete = []
    omitted = False
    for item in categories:
        if not isinstance(item, dict):
            omitted = True
            continue
        income = _finite_number(item.get("income"))
        expenses = _finite_number(item.get("expenses"))
        if income is None or expenses is None:
            omitted = True
            continue
        complete.append((item, income, expenses))
    if not complete:
        return None, omitted
    top_categories = sorted(complete, key=lambda row: row[1] + row[2], reverse=True)[:10]
    top_categories.reverse()
    drawing = Drawing(470, max(150, 32 * len(top_categories) + 45))
    chart = HorizontalBarChart()
    chart.x = 118
    chart.y = 28
    chart.width = 300
    chart.height = max(100, 26 * len(top_categories))
    chart.data = [
        [row[1] for row in top_categories],
        [row[2] for row in top_categories],
    ]
    chart.categoryAxis.categoryNames = [str(row[0].get("category") or "Uncategorized")[:28] for row in top_categories]
    chart.barWidth = 8
    chart.groupSpacing = 8
    chart.bars[0].fillColor = GREEN
    chart.bars[1].fillColor = RED
    maximum = max([row[1] for row in top_categories] + [row[2] for row in top_categories])
    chart.valueAxis.valueMax = maximum * 1.15 if maximum > 0 else 1
    chart.valueAxis.valueStep = max(chart.valueAxis.valueMax / 4, 0.01)
    _chart_styles(chart, font_name)
    chart.categoryAxis.labels.boxAnchor = "e"
    chart.categoryAxis.labels.dx = -5
    legend = Legend()
    legend.colorNamePairs = [(GREEN, "Income"), (RED, "Expenses")]
    legend.fontName = font_name
    legend.fontSize = 8
    legend.x = 170
    legend.y = drawing.height - 8
    drawing.add(chart)
    drawing.add(legend)
    return drawing, omitted


def _recommendations(report: dict[str, Any]) -> list[str]:
    analysis = report.get("analysis") or {}
    validation = report.get("validation") or {}
    recommendations = []
    missing = _finite_number(report.get("missing_values"))
    unknown = _finite_number(analysis.get("unknown_amounts"))
    duplicates = _finite_number(report.get("duplicate_records"))
    validation_count = _finite_number(validation.get("count"))

    if (missing is not None and missing > 0) or (unknown is not None and unknown > 0):
        recommendations.append("Review missing or unknown values. Unknown amounts are excluded from financial totals and averages.")
    if duplicates is not None and duplicates > 0:
        recommendations.append("Review the detected duplicate records and remove confirmed duplicates before final reporting.")
    if validation_count is not None and validation_count > 0:
        recommendations.append("Review the validation findings and correct invalid dates or financial amounts at their source.")
    if report.get("cleaned") is False:
        recommendations.append("This dataset has not been cleaned yet. Choose appropriate cleaning options, then generate a fresh report.")
    if not recommendations:
        if missing is None or duplicates is None or validation_count is None:
            recommendations.append("Some quality metrics are unavailable. Review the source data and regenerate the report when the checks are available.")
        else:
            recommendations.append("No outstanding issues were reported by the available quality checks. Continue reviewing source records as part of your normal process.")
    return recommendations


def _styles(font_name: str, bold_font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName=bold_font_name, fontSize=21, leading=26, textColor=NAVY, alignment=TA_LEFT, spaceAfter=3 * mm),
        "subtitle": ParagraphStyle("ReportSubtitle", parent=base["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=MUTED),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontName=bold_font_name, fontSize=12, leading=16, textColor=NAVY, spaceAfter=2 * mm),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName=font_name, fontSize=8.5, leading=12, textColor=INK),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName=font_name, fontSize=7.5, leading=10, textColor=MUTED),
        "metric_label": ParagraphStyle("MetricLabel", parent=base["Normal"], fontName=bold_font_name, fontSize=6.5, leading=9, textColor=MUTED, alignment=TA_LEFT),
        "metric_value": ParagraphStyle("MetricValue", parent=base["Normal"], fontName=bold_font_name, fontSize=10, leading=14, textColor=NAVY, alignment=TA_LEFT, wordWrap="CJK"),
        "table_header": ParagraphStyle("TableHeader", parent=base["Normal"], fontName=bold_font_name, fontSize=7.5, leading=10, textColor=colors.white),
        "table_cell": ParagraphStyle("TableCell", parent=base["Normal"], fontName=font_name, fontSize=7.5, leading=10, textColor=INK),
        "table_money": ParagraphStyle("TableMoney", parent=base["Normal"], fontName=font_name, fontSize=7.5, leading=10, textColor=INK, alignment=TA_RIGHT),
    }


def _table_style(header: bool = True) -> TableStyle:
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY if header else PALE_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]))
    return TableStyle(commands)


def _page_decoration(canvas: Any, document: Any, font_name: str, bold_font_name: str) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 7 * mm, width, 7 * mm, fill=1, stroke=0)
    canvas.setFont(bold_font_name, 8)
    canvas.setFillColor(NAVY)
    canvas.drawString(document.leftMargin, height - 13 * mm, "FINPREP  /  FINANCIAL DATA QUALITY")
    canvas.setStrokeColor(LINE)
    canvas.line(document.leftMargin, 14 * mm, width - document.rightMargin, 14 * mm)
    canvas.setFont(font_name, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(document.leftMargin, 9 * mm, "Prepared from the current dataset quality report")
    canvas.drawRightString(width - document.rightMargin, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_quality_pdf(report: dict[str, Any]) -> bytes:
    regular_font, bold_font = _register_fonts()
    styles = _styles(regular_font, bold_font)
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=20 * mm,
        title="Visual Financial Quality Report",
        author="FinPrep",
    )
    analysis = report.get("analysis") if isinstance(report.get("analysis"), dict) else {}
    quality = report.get("validation") if isinstance(report.get("validation"), dict) else {}
    story: list[Any] = [
        Spacer(1, 3 * mm),
        _paragraph("Visual Financial Quality Report", styles["title"]),
        _paragraph(f"Dataset: {report.get('filename') or 'Not available'}", styles["subtitle"]),
        _paragraph(
            f"{_count(report.get('row_count'))} rows  |  {_count(report.get('column_count'))} columns  |  Generated {datetime.now().astimezone().strftime('%d %b %Y, %H:%M %Z')}",
            styles["subtitle"],
        ),
        Spacer(1, 5 * mm),
        _metric_cards(report, styles),
    ]

    story.extend(_heading("Financial overview", styles))
    story.append(_paragraph("Income and expense totals use the financial calculations already included in this quality report.", styles["small"]))
    overview_chart = _income_expense_chart(report, regular_font)
    story.append(overview_chart if overview_chart is not None else _paragraph("Income and expense chart unavailable because one or both totals are missing.", styles["body"]))

    story.append(PageBreak())
    category_section = _heading("Category-wise financial analysis", styles)
    category_chart, omitted_categories = _category_chart(report, regular_font)
    category_section.append(category_chart if category_chart is not None else _paragraph("Category chart unavailable because category summaries are missing or have no complete values.", styles["body"]))
    if category_chart is not None:
        category_section.append(_paragraph("Chart shows up to 10 categories with available income and expense values. Incomplete categories are omitted from the chart, not counted as zero.", styles["small"]))
    story.append(KeepTogether(category_section))
    category_rows = analysis.get("category_summary")
    if isinstance(category_rows, list) and category_rows:
        table_rows: list[list[Any]] = [[_paragraph("Category", styles["table_header"]), _paragraph("Income", styles["table_header"]), _paragraph("Expenses", styles["table_header"])] ]
        for item in category_rows:
            if isinstance(item, dict):
                table_rows.append([
                    _paragraph(item.get("category") or "Uncategorized", styles["table_cell"]),
                    _paragraph(format_inr(item.get("income")), styles["table_money"]),
                    _paragraph(format_inr(item.get("expenses")), styles["table_money"]),
                ])
        if len(table_rows) > 1:
            table = Table(table_rows, colWidths=[84 * mm, 45 * mm, 45 * mm], repeatRows=1, hAlign="LEFT")
            table.setStyle(_table_style())
            story.extend([Spacer(1, 2 * mm), table])

    story.extend(_heading("Data quality", styles))
    quality_metrics = [
        ["Missing values", _count(report.get("missing_values"))],
        ["Duplicate records", _count(report.get("duplicate_records"))],
        ["Unknown or invalid amounts", _count(analysis.get("unknown_amounts"))],
        ["Validation errors", _count(quality.get("count"))],
    ]
    quality_table = Table(
        [[_paragraph(label, styles["table_cell"]), _paragraph(value, styles["table_cell"])] for label, value in quality_metrics],
        colWidths=[87 * mm, 87 * mm],
        hAlign="LEFT",
    )
    quality_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(quality_table)
    issues = quality.get("issues") if isinstance(quality.get("issues"), list) else []
    if issues:
        story.extend([Spacer(1, 3 * mm), _paragraph("Validation findings (first 10)", styles["section"])])
        issue_rows: list[list[Any]] = [[_paragraph(text, styles["table_header"]) for text in ("Row", "Column", "Finding")]]
        for issue in issues[:10]:
            if isinstance(issue, dict):
                issue_rows.append([
                    _paragraph(issue.get("row") if issue.get("row") is not None else "Not available", styles["table_cell"]),
                    _paragraph(issue.get("column") or "Not available", styles["table_cell"]),
                    _paragraph(issue.get("message") or "No detail available", styles["table_cell"]),
                ])
        issue_table = Table(issue_rows, colWidths=[18 * mm, 38 * mm, 118 * mm], repeatRows=1, hAlign="LEFT")
        issue_table.setStyle(_table_style())
        story.append(issue_table)
        if quality.get("truncated"):
            story.append(_paragraph("The API found additional validation findings; the PDF lists the first 10.", styles["small"]))

    story.append(PageBreak())
    story.extend(_heading("Cleaning status", styles))
    if report.get("cleaned") is True:
        status_text = "Cleaned - the backend has applied the selected cleaning options."
    elif report.get("cleaned") is False:
        status_text = "Not cleaned - the current report reflects the uploaded dataset before cleaning."
    else:
        status_text = "Cleaning status unavailable."
    story.append(_paragraph(status_text, styles["body"]))
    cleaning_options = report.get("cleaning_options") if isinstance(report.get("cleaning_options"), dict) else None
    if cleaning_options is not None:
        strategy_labels = {
            "keep": "Leave missing values unchanged",
            "fill_zero": "Replace numeric missing values with zero",
            "fill_mean": "Replace numeric missing values with mean",
            "fill_median": "Replace numeric missing values with median",
            "fill_mode": "Replace missing values with column mode",
            "drop_rows": "Drop rows with missing values",
            "fill_custom": "Replace missing values with a custom value",
        }
        option_rows = [
            ("Missing value method", strategy_labels.get(cleaning_options.get("missing_strategy"), "Not available")),
            ("Duplicate removal", "Enabled" if cleaning_options.get("remove_duplicates") else "Disabled"),
            ("Date standardization", "Enabled" if cleaning_options.get("standardize_dates") else "Disabled"),
            ("Invalid amount coercion", "Enabled" if cleaning_options.get("coerce_invalid_numbers") else "Disabled"),
        ]
        if cleaning_options.get("missing_strategy") == "fill_custom":
            option_rows.append(("Custom value", str(cleaning_options.get("custom_value") or "Not available")))
        option_table = Table(
            [[_paragraph(label, styles["table_cell"]), _paragraph(value, styles["table_cell"])] for label, value in option_rows],
            colWidths=[87 * mm, 87 * mm],
            hAlign="LEFT",
        )
        option_table.setStyle(_table_style(header=False))
        story.extend([Spacer(1, 3 * mm), option_table])
    cleaning = report.get("cleaning_summary") if isinstance(report.get("cleaning_summary"), dict) else None
    if cleaning is not None:
        cleaning_items = [
            ("Duplicates removed", cleaning.get("duplicates_removed")),
            ("Rows removed", cleaning.get("rows_removed")),
            ("Missing values filled", cleaning.get("missing_values_filled")),
            ("Missing values remaining", cleaning.get("missing_values_remaining")),
            ("Dates standardized", cleaning.get("dates_standardized")),
            ("Invalid numbers coerced", cleaning.get("numbers_coerced")),
        ]
        cleaning_table = Table(
            [[_paragraph(label, styles["table_cell"]), _paragraph(_count(value), styles["table_cell"])] for label, value in cleaning_items],
            colWidths=[87 * mm, 87 * mm],
            hAlign="LEFT",
        )
        cleaning_table.setStyle(_table_style(header=False))
        story.extend([Spacer(1, 3 * mm), cleaning_table])

    story.extend(_heading("Recommended next steps", styles))
    for recommendation in _recommendations(report):
        story.append(_paragraph(f"- {recommendation}", styles["body"]))
        story.append(Spacer(1, 1.5 * mm))

    if omitted_categories:
        story.append(Spacer(1, 2 * mm))
        story.append(_paragraph("One or more categories with unavailable amounts are shown as Not available in the table and excluded from the chart.", styles["small"]))

    decorate = lambda canvas, doc: _page_decoration(canvas, doc, regular_font, bold_font)
    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return output.getvalue()
