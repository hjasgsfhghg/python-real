from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout, QMainWindow, QMessageBox, QWidget,
)

from view.widgets import CameraView, BoardView, CameraInfoPanel, GameInfoPanel

class MainWindow(QMainWindow):
    # View 门面：presenter 只和这个类打交道。

    mode_changed = Signal(int)
    record_toggled = Signal(bool)
    label_changed = Signal(int)
    train_requested = Signal()
    new_game_requested = Signal()
    column_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("四子棋 · 手势识别")
        self.resize(900, 600)

        self.camera_view = CameraView()
        self.board_view = BoardView()
        self.camera_info = CameraInfoPanel()
        self.game_info = GameInfoPanel()

        layout = QGridLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.camera_view, 1, 0)
        layout.addWidget(self.board_view, 0, 0)
        layout.addWidget(self.camera_info, 1, 1)
        layout.addWidget(self.game_info, 0, 1)
        layout.setColumnStretch(0, 3)
        layout.setColumnStretch(1, 2)
        layout.setRowStretch(0, 3)
        layout.setRowStretch(1, 2)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setStyleSheet(
            "QMainWindow, QWidget { background:#0d1117; color:#e6edf3; }"
            "QGroupBox { border:1px solid #30363d; border-radius:6px; margin-top:10px; }"
            "QGroupBox::title { subcontrol-origin: margin; left:10px; padding:0 4px; }"
            "QPushButton { padding:6px 10px; }"
        )

        # 子控件信号 → 窗口信号（冒泡，presenter 不需要认识子控件）
        self.camera_info.mode_changed.connect(self.mode_changed)
        self.camera_info.record_toggled.connect(self.record_toggled)
        self.camera_info.label_changed.connect(self.label_changed)
        self.game_info.train_requested.connect(self.train_requested)
        self.game_info.new_game_requested.connect(self.new_game_requested)
        self.board_view.column_clicked.connect(self.column_clicked)

    # ---------- presenter -> view ----------

    def show_frame(self, bgr) -> None:
        self.camera_view.set_frame(bgr)

    def show_board(self, snapshot: dict) -> None:
        self.board_view.set_state(snapshot)

    def show_camera_info(self, info: dict) -> None:
        self.camera_info.update_info(info)

    def show_game_info(self, info: dict) -> None:
        self.game_info.update_info(info)

    def set_mode(self, index: int) -> None:
        self.camera_info.set_mode(index)

    def set_recording(self, recording: bool) -> None:
        self.camera_info.set_recording(recording)

    def set_training(self, *args, **kwargs) -> None:
        self.game_info.set_training(*args, **kwargs)

    def train_config(self) -> dict:
        return self.game_info.train_config()

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, "错误", message)