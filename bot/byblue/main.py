import logging
import sys

from PyQt6.QtWidgets import QApplication

from byblue.gui.login_window import LoginWindow
from byblue.gui.main_window import MainWindow
from byblue.gui.styles import STYLESHEET

logging.basicConfig(level=logging.INFO)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    main_window_holder: list[MainWindow] = []

    def on_login_succeeded(email: str, password: str) -> None:
        window = MainWindow(email=email, password=password)
        main_window_holder.append(window)
        window.show()

    login_window = LoginWindow()
    login_window.login_succeeded.connect(on_login_succeeded)
    login_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
