import sys

from embld.experiment.protocol import EMBLDAcquisitionDriver
from qtmrt import QTMException
from qtmrt.client import QTMRTClient
from util.logging import setup_logging
import logging

setup_logging(console_log_output="stdout", console_log_level="warn", console_log_color=True,
              logfile_file="experiment.log", logfile_log_level="debug", logfile_log_color=False,
              log_line_template="%(color_on)s[%(created)d] [%(threadName)s] [%(levelname)-8s] %(message)s%(color_off)s")

logger = logging.getLogger("Experiment Dashboard")

from embld import configuration
from PyQt5.QtWidgets import QApplication, QMainWindow

from main_window_ui import Ui_MainWindowUI


class Window(QMainWindow, Ui_MainWindowUI):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.qtm_client = None
        self.driver = None

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
                try:
                    logger.debug("Starting acquisition driver...")
                    self.driver = EMBLDAcquisitionDriver(self.qtm_client)
                    logger.debug("Connecting timer...")
                    self.driver.protocol_timer.connect(self.status_time_label.setText)
                    self.driver.protocol_event.connect(self.status_protocol.setText)
                    self.driver.protocol_event.connect(self.qtm_client.send_event)
                    self.driver.position_event.connect(self.position_label.setText)
                    self.driver.stop_experiment.connect(self.stop_button.setDown)
                    logger.debug("Starting driver simulation...")
                    self.driver.run_experiment()
                    logger.debug("Starting QTM capture..")
                    # self.qtm_client.new_measurement()
                    self.qtm_client.start_capture(True)
                except Exception as e:
                    self.statusbar.showMessage(str(e))

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
        del self.driver
        self.driver = None
        self.qtm_client.stop_capture()

    def pause_simulation(self):
        logger.info("Pausing simulation")
        self.status_state_label.setText("PAUSED")
        self.status_state_label.setStyleSheet("color:orange;")
        pass

    def connect_qtm(self, toggle_on: bool):
        if toggle_on:
            try:
                logger.info(f"Connecting to QTM @ RT://{self.qtm_hostname.text()}:{self.qtm_port.text()}")
                if self.qtm_use_authentication.isChecked():
                    self.qtm_client = QTMRTClient("127.0.0.1", 22222, self.qtm_password.text())
                else:
                    self.qtm_client = QTMRTClient("127.0.0.1", 22222)
                self.qtm_client.connect()
                self.qtm_connection_status.setText("Connected")
                self.qtm_connection_status.setStyleSheet("color:green; font-size:1em;")
                self.qtm_connect_btn.setStyleSheet("background-color:lightgreen;color:black;")
                self.qtm_hostname.setEnabled(False)
                self.qtm_port.setEnabled(False)
                self.qtm_use_authentication.setEnabled(False)
                self.auth_frame.setEnabled(False)
                calibration_status = self.qtm_client.get_calibration_status()

                if calibration_status['calibration']['calibrated'] == "true":
                    self.calibration_label.setStyleSheet("color: green;")
                    self.calibration_label.setText("Calibrated")
                else:
                    self.calibration_label.setStyleSheet("color: red; font-weight: bold; text-decoration: underline;")
                    self.calibration_label.setText("NOT CALIBRATED")

            except QTMException as e:
                logger.error("Aborting connection: " + str(e))
                self.qtm_connect_btn.setChecked(False)
                self.qtm_connect_btn.setStyleSheet("background-color:red;")
                self.qtm_connection_status.setStyleSheet("color: red; font-size:12px;")
                self.qtm_connection_status.setText(str(e))
                self.calibration_label.setStyleSheet("color: transparent;")
            # self.qtm_client.new_measurement()
        else:
            self.qtm_connection_status.setText("Disconnected")
            self.qtm_connection_status.setStyleSheet("color:transparent;")
            self.calibration_label.setStyleSheet("color: transparent;")
            self.qtm_connect_btn.setStyleSheet("color:black;background-color:none;")
            self.calibration_label.setStyleSheet("color: transparent;")
            self.qtm_hostname.setEnabled(True)
            self.qtm_port.setEnabled(True)
            self.qtm_use_authentication.setEnabled(True)
            if self.qtm_use_authentication.isChecked():
                self.auth_frame.setEnabled(True)
            # self.qtm_client.close_measurement()
            self.qtm_client.disconnect()
            del self.qtm_client
            self.qtm_client = None
            logger.info("Disconnecting from QTM")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
