#!/usr/bin/env python3
import sys

from PySide6.QtWidgets import QApplication

from view.window import MainWindow

def main() -> int:
    # 加载model
    # 加载presenter
    # presenter = AppPresenter(window, game, camera, ...)   # 下一轮接
    # presenter.start()

    # 加载view
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec(app.exec())  # type: ignore


if __name__ == "__main__":
    sys.exit(main())