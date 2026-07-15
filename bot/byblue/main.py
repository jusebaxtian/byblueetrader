import logging
import sys

from PyQt6.QtWidgets import QApplication

from byblue.gui.main_window import MainWindow

logging.basicConfig(level=logging.INFO)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
