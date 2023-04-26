import os
import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication

from gui.dashboard_view import DashboardView
from gui.experiment_controller import ExperimentGUIController
from util.logging import setup_logging

setup_logging(
    console_log_output="stdout",
    console_log_level="debug",
    console_log_color=True,
    logfile_file="experiment.log",
    logfile_log_level="info",
    logfile_log_color=False,
    log_line_template="%(color_on)s[%(created)d] [%(threadName)s] [%(levelname)-8s] %(message)s%(color_off)s",
)


if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    
    win = DashboardView()
    controller = ExperimentGUIController(win)
    win.show()
    sys.exit(app.exec())
