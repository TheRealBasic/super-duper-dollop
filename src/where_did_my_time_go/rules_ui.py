from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from where_did_my_time_go.rules import DEFAULT_CATEGORIES, AppContext, Rule, apply_rules
from where_did_my_time_go.storage import Database
from where_did_my_time_go.win_api import get_foreground_app


@dataclass
class RuleFormData:
    enabled: bool
    match_type: str
    process_pattern: str | None
    title_pattern: str | None
    category: str
    priority: int


class RuleDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, data: RuleFormData | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rule")
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        self.match_type = QComboBox()
        self.match_type.addItems(["substring", "regex"])
        self.process_pattern = QLineEdit()
        self.title_pattern = QLineEdit()
        self.category = QComboBox()
        self.category.addItems(DEFAULT_CATEGORIES)
        self.priority = QLineEdit("1")

        form = QFormLayout()
        form.addRow("Enabled", self.enabled_check)
        form.addRow("Match Type", self.match_type)
        form.addRow("Process Pattern", self.process_pattern)
        form.addRow("Title Pattern", self.title_pattern)
        form.addRow("Category", self.category)
        form.addRow("Priority", self.priority)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if data:
            self.enabled_check.setChecked(data.enabled)
            self.match_type.setCurrentText(data.match_type)
            self.process_pattern.setText(data.process_pattern or "")
            self.title_pattern.setText(data.title_pattern or "")
            self.category.setCurrentText(data.category)
            self.priority.setText(str(data.priority))

    def data(self) -> RuleFormData:
        return RuleFormData(
            enabled=self.enabled_check.isChecked(),
            match_type=self.match_type.currentText(),
            process_pattern=self.process_pattern.text().strip() or None,
            title_pattern=self.title_pattern.text().strip() or None,
            category=self.category.currentText(),
            priority=int(self.priority.text() or "1"),
        )


class RulesWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._db = Database()
        self._db.initialize()

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [
                "Enabled",
                "Match",
                "Process",
                "Title",
                "Category",
                "Priority",
                "Rule ID",
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)

        add_button = QPushButton("Add")
        edit_button = QPushButton("Edit")
        delete_button = QPushButton("Delete")
        test_button = QPushButton("Test on Current App")

        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        button_layout.addWidget(test_button)

        layout = QVBoxLayout(self)
        layout.addLayout(button_layout)
        layout.addWidget(self.table)

        add_button.clicked.connect(self.add_rule)
        edit_button.clicked.connect(self.edit_rule)
        delete_button.clicked.connect(self.delete_rule)
        test_button.clicked.connect(self.test_rule)

        self.refresh()

    def refresh(self) -> None:
        rows = self._db.list_rules()
        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            values = [
                "Yes" if row["enabled"] else "No",
                row["match_type"],
                row["process_pattern"] or "",
                row["title_pattern"] or "",
                row["category"],
                str(row["priority"]),
                str(row["rule_id"]),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row_idx, col, QTableWidgetItem(value))

    def _selected_rule_id(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        rule_id_item = selected[-1]
        return int(rule_id_item.text())

    def add_rule(self) -> None:
        dialog = RuleDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.data()
            self._db.add_rule(
                data.enabled,
                data.match_type,
                data.process_pattern,
                data.title_pattern,
                data.category,
                data.priority,
            )
            self.refresh()

    def edit_rule(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id is None:
            return
        rows = [row for row in self._db.list_rules() if row["rule_id"] == rule_id]
        if not rows:
            return
        row = rows[0]
        data = RuleFormData(
            enabled=bool(row["enabled"]),
            match_type=row["match_type"],
            process_pattern=row["process_pattern"],
            title_pattern=row["title_pattern"],
            category=row["category"],
            priority=row["priority"],
        )
        dialog = RuleDialog(self, data)
        if dialog.exec() == QDialog.Accepted:
            updated = dialog.data()
            self._db.update_rule(
                rule_id,
                updated.enabled,
                updated.match_type,
                updated.process_pattern,
                updated.title_pattern,
                updated.category,
                updated.priority,
            )
            self.refresh()

    def delete_rule(self) -> None:
        rule_id = self._selected_rule_id()
        if rule_id is None:
            return
        self._db.delete_rule(rule_id)
        self.refresh()

    def test_rule(self) -> None:
        app = get_foreground_app()
        rules = [Rule(**dict(row)) for row in self._db.list_rules()]
        category = apply_rules(rules, AppContext(app.process_name, app.window_title))
        QMessageBox.information(self, "Rule Test", f"Current app matches category: {category}")
