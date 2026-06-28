from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


def line_icon(name: str, color: str = "#334155", size: int = 20) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "folder":
        path = QPainterPath()
        path.moveTo(2.5, 6.5)
        path.lineTo(7.5, 6.5)
        path.lineTo(9.5, 8.5)
        path.lineTo(17.5, 8.5)
        path.lineTo(16.0, 15.5)
        path.lineTo(2.5, 15.5)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(2.5, 6.5), QPointF(2.5, 15.5))
    elif name == "grid":
        painter.drawRoundedRect(QRectF(3.0, 3.0, 14.0, 14.0), 1.5, 1.5)
        painter.drawLine(QPointF(8.0, 3.0), QPointF(8.0, 17.0))
        painter.drawLine(QPointF(12.5, 3.0), QPointF(12.5, 17.0))
        painter.drawLine(QPointF(3.0, 8.0), QPointF(17.0, 8.0))
        painter.drawLine(QPointF(3.0, 12.5), QPointF(17.0, 12.5))
    elif name == "users":
        painter.drawEllipse(QRectF(7.2, 3.0, 5.6, 5.6))
        painter.drawArc(QRectF(4.5, 9.0, 11.0, 8.0), 0, 180 * 16)
        painter.drawEllipse(QRectF(2.5, 5.0, 3.8, 3.8))
        painter.drawEllipse(QRectF(13.7, 5.0, 3.8, 3.8))
        painter.drawArc(QRectF(0.8, 9.5, 6.2, 5.5), 0, 150 * 16)
        painter.drawArc(QRectF(13.0, 9.5, 6.2, 5.5), 30 * 16, 150 * 16)
    elif name == "warning":
        path = QPainterPath()
        path.moveTo(10.0, 2.5)
        path.lineTo(18.0, 16.5)
        path.lineTo(2.0, 16.5)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(10.0, 7.0), QPointF(10.0, 11.5))
        painter.drawPoint(QPointF(10.0, 14.0))
    elif name == "play":
        path = QPainterPath()
        path.moveTo(6.0, 3.5)
        path.lineTo(16.0, 10.0)
        path.lineTo(6.0, 16.5)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "file":
        path = QPainterPath()
        path.moveTo(5.0, 2.5)
        path.lineTo(12.5, 2.5)
        path.lineTo(16.0, 6.0)
        path.lineTo(16.0, 17.0)
        path.lineTo(5.0, 17.0)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(12.5, 2.5), QPointF(12.5, 6.0))
        painter.drawLine(QPointF(12.5, 6.0), QPointF(16.0, 6.0))
        painter.drawLine(QPointF(7.5, 10.0), QPointF(13.5, 10.0))
        painter.drawLine(QPointF(7.5, 13.0), QPointF(13.5, 13.0))
    elif name == "cube":
        painter.drawPolygon(QPolygonF([QPointF(10.0, 2.5), QPointF(17.0, 6.5), QPointF(10.0, 10.5), QPointF(3.0, 6.5)]))
        painter.drawLine(QPointF(3.0, 6.5), QPointF(3.0, 14.0))
        painter.drawLine(QPointF(17.0, 6.5), QPointF(17.0, 14.0))
        painter.drawLine(QPointF(10.0, 10.5), QPointF(10.0, 18.0))
        painter.drawLine(QPointF(3.0, 14.0), QPointF(10.0, 18.0))
        painter.drawLine(QPointF(17.0, 14.0), QPointF(10.0, 18.0))
    elif name in {"left", "right", "up", "down"}:
        points = {
            "left": (QPointF(13.0, 4.0), QPointF(7.0, 10.0), QPointF(13.0, 16.0)),
            "right": (QPointF(7.0, 4.0), QPointF(13.0, 10.0), QPointF(7.0, 16.0)),
            "up": (QPointF(4.0, 13.0), QPointF(10.0, 7.0), QPointF(16.0, 13.0)),
            "down": (QPointF(4.0, 7.0), QPointF(10.0, 13.0), QPointF(16.0, 7.0)),
        }
        a, b, c = points[name]
        painter.drawPolyline(QPolygonF([a, b, c]))
    else:
        raise ValueError(f"Unknown icon: {name}")

    painter.end()
    return QIcon(pixmap)
