"""Generate PDF report (ReportLab)."""
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.lib import colors


def generate_pdf(
    output_path: Path,
    project_name: str,
    image_path: Path | None,
    walls_count: int,
    aps: list[dict],
    coverage_pct: float,
    avg_rssi: float,
) -> Path:
    """Write a PDF report and return its path."""
    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    flow = []

    flow.append(Paragraph(f"<b>AI Wall Design Report</b>", styles["Title"]))
    flow.append(Paragraph(f"Project: <b>{project_name}</b>", styles["Heading2"]))
    flow.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["Normal"]))
    flow.append(Spacer(1, 0.5 * cm))

    # Floor plan thumbnail
    if image_path and image_path.exists():
        try:
            flow.append(Image(str(image_path), width=15 * cm, height=10 * cm,
                              kind='proportional'))
            flow.append(Spacer(1, 0.5 * cm))
        except Exception:
            pass

    # Summary table
    summary = [
        ["Metric", "Value"],
        ["Walls detected", str(walls_count)],
        ["Access Points (count)", str(len(aps))],
        ["Coverage (>= -65 dBm)", f"{coverage_pct:.1f}%"],
        ["Average RSSI", f"{avg_rssi:.1f} dBm"],
    ]
    t = Table(summary, colWidths=[8 * cm, 6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#F5F5F5"), colors.white]),
    ]))
    flow.append(t)
    flow.append(Spacer(1, 0.5 * cm))

    # AP positions table
    flow.append(Paragraph("<b>Access Point Positions</b>", styles["Heading3"]))
    ap_rows = [["Name", "X (m)", "Y (m)", "Z (m)"]]
    for ap in aps:
        ap_rows.append([
            ap["name"],
            f"{ap['x']:.2f}",
            f"{ap['y']:.2f}",
            f"{ap['z']:.2f}",
        ])
    t2 = Table(ap_rows, colWidths=[4 * cm, 3 * cm, 3 * cm, 3 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    flow.append(t2)

    doc.build(flow)
    return output_path
