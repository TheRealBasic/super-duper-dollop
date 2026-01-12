from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCharts import QChart, QChartView, QPieSeries
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QVBoxLayout,
    QWidget,
)

from where_did_my_time_go.storage import Database, date_range_for_day


def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


class DashboardWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._db = Database()
        self._db.initialize()

        self.total_active_label = QLabel("Active: 0h 0m")
        self.total_idle_label = QLabel("Idle: 0h 0m")
        self.top_apps_list = QListWidget()

        self.series = QPieSeries()
        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setTitle("Today's Category Breakdown")
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.total_active_label)
        stats_layout.addWidget(self.total_idle_label)
        stats_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(stats_layout)
        layout.addWidget(QLabel("Top 10 Apps"))
        layout.addWidget(self.top_apps_list)
        layout.addWidget(self.chart_view)

        self.refresh()

    def refresh(self) -> None:
        start, end = date_range_for_day(datetime.now(timezone.utc))
        active = self._db.total_active(start, end)
        idle = self._db.total_idle(start, end)
        self.total_active_label.setText(f"Active: {format_duration(active)}")
        self.total_idle_label.setText(f"Idle: {format_duration(idle)}")

        self.top_apps_list.clear()
        for row in self._db.top_apps(start, end, 10):
            self.top_apps_list.addItem(
                f"{row['process_name']} - {format_duration(int(row['total']))}"
            )

        self.series.clear()
        for row in self._db.summarize_today(start, end):
            self.series.append(row["category"], float(row["total"]))
