import sys

from qtmrt.client import QTMRTClient
from util.logging import setup_logging
import logging

setup_logging(console_log_output="stdout", console_log_level="debug", console_log_color=True,
              logfile_file="experiment.log", logfile_log_level="debug", logfile_log_color=False,
              log_line_template="%(color_on)s[%(created)d] [%(threadName)s] [%(levelname)-8s] %(message)s%(color_off)s")

logger = logging.getLogger("Experiment Dashboard")

from PyQt5.QtWidgets import QApplication, QMainWindow

from main_window_ui import Ui_MainWindowUI


class Window(QMainWindow, Ui_MainWindowUI):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.qtm_client = QTMRTClient("127.0.0.1", 22222)

    def start_simulation(self):
        if not self.stop_button.isEnabled():
            error = False
            if len(self.exp_subject_id.text()) == 0:
                error = True
                self.exp_subject_id_label.setStyleSheet("color:red;")
            else:
                self.exp_subject_id_label.setStyleSheet("color:black;")
            if self.exp_age.value() == -1:
                error = True
                self.exp_age_label.setStyleSheet("color:red;")
            else:
                self.exp_age_label.setStyleSheet("color:black;")
            checked_button = self.exp_gender_group.checkedButton()
            if checked_button is None:
                error = True
                self.exp_gender_label.setStyleSheet("color:red;")
            else:
                self.exp_gender_label.setStyleSheet("color:black;")
            if not self.qtm_connect_btn.isChecked():
                error = True
                self.qtm_connect_btn.setStyleSheet("background-color:red; color: red;")

            if error:
                self.statusbar.showMessage("Please fill in the fields in RED before staring the simulation...", 4000)
                logging.error("Cannot start simulation: all required fields not satisfied!")
            else:
                self.exp_subject_id_label.setStyleSheet("color:black;")
                self.exp_age_label.setStyleSheet("color:black;")
                self.exp_gender_label.setStyleSheet("color:black;")
                self.qtm_connect_btn.setStyleSheet("background-color:none;")
                logger.info("Starting simulation")
                self.status_state_label.setText("RUNNING")
                self.status_state_label.setStyleSheet("color:green;")

                self.pause_button.setEnabled(True)
                self.stop_button.setEnabled(True)
                self.qtm_group.setEnabled(False)
                self.experiment_group.setEnabled(False)
                self.play_button.setEnabled(False)

                self.qtm_client.start_capture(True)

        else:
            logger.info("Resuming simulation")
            self.status_state_label.setText("RUNNING")
            self.status_state_label.setStyleSheet("color:green;")
            self.pause_button.setEnabled(True)
            self.play_button.setEnabled(False)

    def stop_simulation(self):
        logger.info("Stopping simulation")
        self.status_state_label.setText("STOPPED")
        self.status_state_label.setStyleSheet("color:red;")
        self.qtm_client.stop_capture()

    def pause_simulation(self):
        logger.info("Pausing simulation")
        self.status_state_label.setText("PAUSED")
        self.status_state_label.setStyleSheet("color:orange;")
        pass

    def connect_qtm(self, toggle_on: bool):
        if toggle_on:
            logger.info(f"Connecting to QTM @ RT://{self.qtm_hostname.text()}:{self.qtm_port.text()}")
            self.qtm_connection_status.setText("Connected!")
            self.qtm_connection_status.setStyleSheet("color:green;")
            self.qtm_connect_btn.setStyleSheet("background-color:lightgreen;color:black;")
            self.qtm_hostname.setEnabled(False)
            self.qtm_port.setEnabled(False)
            self.qtm_use_authentication.setEnabled(False)
            self.auth_frame.setEnabled(False)
            self.qtm_client.connect()
            self.qtm_client.new_measurement()
        else:
            self.qtm_connection_status.setText("Disconnected")
            self.qtm_connection_status.setStyleSheet("color:black;background-color:none;")
            self.qtm_hostname.setEnabled(True)
            self.qtm_port.setEnabled(True)
            self.qtm_use_authentication.setEnabled(True)
            if self.qtm_use_authentication.isChecked():
                self.auth_frame.setEnabled(True)
            self.qtm_client.close_measurement()
            self.qtm_client.disconnect()
            logger.info("Disconnecting from QTM")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
