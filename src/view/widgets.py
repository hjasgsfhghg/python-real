from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPointF, QRectF, QSignalBlocker
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QGroupBox,
    QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QSizePolicy, QSpinBox, QWidget,
)

ROWS, COLS = 6, 7
MODES = ("采集", "训练", "识别 / 游戏")
GESTURES = ("Fist", "Palm Up", "Palm Down")

class CameraView(QLabel):
    """只负责显示一帧 BGR，并在窗口缩放时重新等比缩放。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background:#202124; color:#aaaaaa; border-radius:8px;")
        self.setText("摄像头未打开")
        self._pixmap: QPixmap | None = None

    def set_frame(self, bgr) -> None:
        """bgr: HxWx3 的 numpy 数组（BGR）。view 不 import numpy，只用它的属性。"""
        if bgr is None:
            return
        height, width = bgr.shape[:2]
        image = QImage(bgr.data, width, height, bgr.strides[0],
                       QImage.Format.Format_BGR888)
        # copy() 保证 QPixmap 不依赖 numpy 缓冲的生命周期
        self._pixmap = QPixmap.fromImage(image.copy())
        self._rescale()

    def _rescale(self) -> None:
        if self._pixmap is None:
            return
        self.setPixmap(self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()


class BoardView(QWidget):
    """只负责画 6x7 棋盘；鼠标点击换算成列号发出去。"""

    column_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._snap: dict | None = None
        self._cell = 0.0
        self._left = 0.0
        self._top = 0.0

    def set_state(self, snapshot: dict) -> None:
        """snapshot 由 presenter 从 model 取出，包含 board/cursor/winner 等。"""
        self._snap = snapshot
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#161a1f"))

        area = self.rect().adjusted(12, 12, -12, -12)
        cell = min(area.width() / COLS, area.height() / ROWS)
        width, height = cell * COLS, cell * ROWS
        left = area.left() + (area.width() - width) / 2
        top = area.top() + (area.height() - height) / 2
        self._cell, self._left, self._top = cell, left, top

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2b6cb0"))
        painter.drawRoundedRect(
            QRectF(left - 8, top - 8, width + 16, height + 16), 10, 10)

        snap = self._snap or {}
        board = snap.get("board") or tuple([0] * COLS for _ in range(ROWS))
        cursor = snap.get("cursor", COLS // 2)
        winner = snap.get("winner") or 0

        # 候选列高亮
        if not winner:
            painter.setBrush(QColor(255, 255, 255, 45))
            painter.drawRoundedRect(
                QRectF(left + cursor * cell + 3, top + 3, cell - 6, height - 6), 6, 6)

        colors = {1: QColor("#e53e3e"), 2: QColor("#ecc94b")}
        for row in range(ROWS):
            for col in range(COLS):
                cx = left + col * cell + cell / 2
                cy = top + row * cell + cell / 2
                radius = cell * 0.38
                painter.setBrush(QColor("#0f2537"))
                painter.drawEllipse(QPointF(cx, cy), radius, radius)
                value = board[row][col]
                if value in colors:
                    painter.setBrush(colors[value])
                    painter.drawEllipse(QPointF(cx, cy), radius, radius)

        if winner:
            painter.setPen(QColor("white"))
            font = painter.font()
            font.setPointSize(max(14, int(cell * 0.45)))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             f"玩家 {winner} 获胜")

    def mousePressEvent(self, event):
        if self._cell <= 0:
            return
        col = int((event.position().x() - self._left) // self._cell)
        if 0 <= col < COLS:
            self.column_clicked.emit(col)


class CameraInfoPanel(QGroupBox):
    """左下：模式、采集控制、已存张数、实时手势。"""

    mode_changed = Signal(int)
    record_toggled = Signal(bool)
    label_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__("摄像头 / 采集", parent)

        self.mode_box = QComboBox()
        self.mode_box.addItems(MODES)
        self.label_box = QComboBox()
        self.label_box.addItems(GESTURES)
        self.record_button = QPushButton("开始采集")
        self.record_button.setCheckable(True)
        self.count_label = QLabel("已保存 0 张")
        self.gesture_label = QLabel("手势：—")
        self.camera_label = QLabel("画面：—")

        grid = QGridLayout()
        grid.addWidget(QLabel("模式"), 0, 0)
        grid.addWidget(self.mode_box, 0, 1)
        grid.addWidget(QLabel("标签"), 1, 0)
        grid.addWidget(self.label_box, 1, 1)
        grid.addWidget(self.record_button, 2, 0, 1, 2)
        grid.addWidget(self.count_label, 3, 0, 1, 2)
        grid.addWidget(self.gesture_label, 4, 0, 1, 2)
        grid.addWidget(self.camera_label, 5, 0, 1, 2)
        grid.setRowStretch(6, 1)
        self.setLayout(grid)

        self.mode_box.currentIndexChanged.connect(self.mode_changed)
        self.label_box.currentIndexChanged.connect(self.label_changed)
        self.record_button.toggled.connect(self._on_record_toggled)

    def _on_record_toggled(self, checked: bool) -> None:
        self.record_button.setText("停止采集" if checked else "开始采集")
        self.record_toggled.emit(checked)

    # 以下两个方法给 presenter 用，程序化修改控件时不回头触发信号
    def set_mode(self, index: int) -> None:
        blocker = QSignalBlocker(self.mode_box)
        self.mode_box.setCurrentIndex(index)
        del blocker

    def set_recording(self, recording: bool) -> None:
        blocker = QSignalBlocker(self.record_button)
        self.record_button.setChecked(recording)
        self.record_button.setText("停止采集" if recording else "开始采集")
        del blocker

    def update_info(self, info: dict) -> None:
        if "saved" in info:
            self.count_label.setText(f"已保存 {info['saved']} 张")
        if "gesture" in info:
            text = f"手势：{info['gesture']}"
            if info.get("conf") is not None:
                text += f"（{info['conf']:.2f}）"
            self.gesture_label.setText(text)
        if "size" in info:
            width, height = info["size"]
            self.camera_label.setText(f"画面：{width} × {height}")


class GameInfoPanel(QGroupBox):
    """右下：棋局状态、模型状态、训练参数与进度。"""

    new_game_requested = Signal()
    train_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("棋局 / 模型", parent)

        self.turn_label = QLabel("当前：—")
        self.cursor_label = QLabel("候选列：—")
        self.winner_label = QLabel("状态：进行中")
        self.model_label = QLabel("模型：未加载")
        self.new_game_button = QPushButton("新开一局")

        self.epoch_box = QSpinBox()
        self.epoch_box.setRange(1, 200)
        self.epoch_box.setValue(10)
        self.lr_box = QDoubleSpinBox()
        self.lr_box.setDecimals(4)
        self.lr_box.setRange(0.00001, 1.0)
        self.lr_box.setSingleStep(0.0001)
        self.lr_box.setValue(0.0001)
        self.bs_box = QSpinBox()
        self.bs_box.setRange(1, 128)
        self.bs_box.setValue(16)

        self.train_button = QPushButton("开始训练")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label = QLabel("未在训练")

        grid = QGridLayout()
        grid.addWidget(self.turn_label, 0, 0, 1, 2)
        grid.addWidget(self.cursor_label, 1, 0, 1, 2)
        grid.addWidget(self.winner_label, 2, 0, 1, 2)
        grid.addWidget(self.model_label, 3, 0, 1, 2)
        grid.addWidget(self.new_game_button, 4, 0, 1, 2)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        grid.addWidget(line, 5, 0, 1, 2)

        grid.addWidget(QLabel("epoch"), 6, 0)
        grid.addWidget(self.epoch_box, 6, 1)
        grid.addWidget(QLabel("学习率"), 7, 0)
        grid.addWidget(self.lr_box, 7, 1)
        grid.addWidget(QLabel("batch"), 8, 0)
        grid.addWidget(self.bs_box, 8, 1)
        grid.addWidget(self.train_button, 9, 0, 1, 2)
        grid.addWidget(self.progress, 10, 0, 1, 2)
        grid.addWidget(self.progress_label, 11, 0, 1, 2)
        grid.setRowStretch(12, 1)
        self.setLayout(grid)

        self.new_game_button.clicked.connect(self.new_game_requested)
        self.train_button.clicked.connect(self.train_requested)

    def train_config(self) -> dict:
        return {
            "epoch": self.epoch_box.value(),
            "lr": self.lr_box.value(),
            "bs": self.bs_box.value(),
        }

    def update_info(self, info: dict) -> None:
        if "current" in info:
            self.turn_label.setText(f"当前：玩家 {info['current']}")
        if "cursor" in info:
            self.cursor_label.setText(f"候选列：{info['cursor'] + 1} / {COLS}")
        if "winner" in info:
            winner = info["winner"]
            if winner == -1:
                self.winner_label.setText("状态：平局")
            elif winner:
                self.winner_label.setText(f"状态：玩家 {winner} 获胜")
            else:
                self.winner_label.setText("状态：进行中")
        if "model" in info:
            self.model_label.setText(f"模型：{info['model']}")

    def set_training(self, running: bool, epoch: int = 0, total: int = 0,
                     loss: float | None = None, acc: float | None = None) -> None:
        for widget in (self.train_button, self.epoch_box, self.lr_box, self.bs_box):
            widget.setEnabled(not running)
        if total:
            self.progress.setRange(0, total)
            self.progress.setValue(epoch)
        if running:
            text = f"训练中：{epoch}/{total} 轮"
            if loss is not None:
                text += f"，loss {loss:.4f}"
            if acc is not None:
                text += f"，acc {acc:.2%}"
            self.progress_label.setText(text)
        else:
            self.progress_label.setText("未在训练" if epoch == 0 else "训练结束")

