from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QPieSeries
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from where_did_my_time_go.storage import Database


class ReportsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._db = Database()
        self._db.initialize()

        self.range_combo = QComboBox()
        self.range_combo.addItems(["Today", "Yesterday", "Last 7 Days", "Custom"])
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)

        today = datetime.now().date()
        self.start_date.setDate(today)
        self.end_date.setDate(today)

        self.category_filter = QLineEdit()
        self.category_filter.setPlaceholderText("Filter by category")
        self.app_filter = QLineEdit()
        self.app_filter.setPlaceholderText("Filter by app/process")
        self.export_button = QPushButton("Export CSV")

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Start",
                "End",
                "Duration",
                "Process",
                "Exe Path",
                "Title",
                "Category",
                "Intent",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)

        self.category_series = QPieSeries()
        self.category_chart = QChart()
        self.category_chart.addSeries(self.category_series)
        self.category_chart.setTitle("Category Breakdown")
        self.category_view = QChartView(self.category_chart)

        self.app_chart = QChart()
        self.app_series = QBarSeries()
        self.app_chart.addSeries(self.app_series)
        self.app_chart.setTitle("Top Apps")
        self.app_view = QChartView(self.app_chart)

        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("Range"))
        range_layout.addWidget(self.range_combo)
        range_layout.addWidget(self.start_date)
        range_layout.addWidget(self.end_date)
        range_layout.addStretch()
        range_layout.addWidget(self.export_button)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.category_filter)
        filter_layout.addWidget(self.app_filter)

        layout = QVBoxLayout(self)
        layout.addLayout(range_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.category_view)
        layout.addWidget(self.app_view)
        layout.addWidget(self.table)

        self.range_combo.currentTextChanged.connect(self.refresh)
        self.start_date.dateChanged.connect(self.refresh)
        self.end_date.dateChanged.connect(self.refresh)
        self.category_filter.textChanged.connect(self.refresh)
        self.app_filter.textChanged.connect(self.refresh)
        self.export_button.clicked.connect(self.export_csv)

        self.refresh()

    def _get_range(self) -> tuple[str, str]:
        now = datetime.now(timezone.utc)
        selection = self.range_combo.currentText()
        if selection == "Today":
            start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            end = start + timedelta(days=1)
        elif selection == "Yesterday":
            end = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            start = end - timedelta(days=1)
        elif selection == "Last 7 Days":
            end = now
            start = end - timedelta(days=7)
        else:
            start = datetime.combine(self.start_date.date().toPython(), datetime.min.time())
            end = datetime.combine(self.end_date.date().toPython(), datetime.min.time()) + timedelta(days=1)
            start = start.replace(tzinfo=timezone.utc)
            end = end.replace(tzinfo=timezone.utc)
        return start.isoformat(), end.isoformat()

    def refresh(self) -> None:
        start, end = self._get_range()
        rows = self._db.fetch_sessions(start, end)

        category_filter = self.category_filter.text().lower().strip()
        app_filter = self.app_filter.text().lower().strip()

        filtered = []
        for row in rows:
            if category_filter and category_filter not in row["category"].lower():
                continue
            if app_filter and app_filter not in row["process_name"].lower():
                continue
            filtered.append(row)

        self.table.setRowCount(len(filtered))
        for row_idx, row in enumerate(filtered):
            values = [
                row["start_ts"],
                row["end_ts"],
                str(row["duration_sec"]),
                row["process_name"],
                row["exe_path"],
                row["window_title"],
                row["category"],
                row["intent_tag"] or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.table.setItem(row_idx, col, item)

        self.category_series.clear()
        totals = {}
        for row in filtered:
            totals[row["category"]] = totals.get(row["category"], 0) + row["duration_sec"]
        for category, total in totals.items():
            self.category_series.append(category, float(total))

        self.app_series.clear()
        app_totals = {}
        for row in filtered:
            app_totals[row["process_name"]] = app_totals.get(row["process_name"], 0) + row["duration_sec"]
        top_apps = sorted(app_totals.items(), key=lambda item: item[1], reverse=True)[:10]
        bar_set = QBarSet("Apps")
        labels = []
        for app, total in top_apps:
            bar_set.append(total)
            labels.append(app)
        self.app_series.append(bar_set)
        axis = QBarCategoryAxis()
        axis.append(labels)
        self.app_chart.removeAxis(self.app_chart.axisX()) if self.app_chart.axisX() else None
        self.app_chart.createDefaultAxes()
        self.app_chart.setAxisX(axis, self.app_series)

    def export_csv(self) -> None:
        start, end = self._get_range()
        rows = self._db.fetch_sessions(start, end)
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", str(Path.home() / "sessions.csv"), "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "start_ts",
                    "end_ts",
                    "duration_sec",
                    "process_name",
                    "exe_path",
                    "window_title",
                    "category",
                    "intent_tag",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row["start_ts"],
                        row["end_ts"],
                        row["duration_sec"],
                        row["process_name"],
                        row["exe_path"],
                        row["window_title"],
                        row["category"],
                        row["intent_tag"],
                    ]
                )
