import logging
import sys

from pylsl import StreamInfo, StreamOutlet

from embld.experiment.protocol import EMBLDAcquisitionDriver
from qtmrt import QTMException
from qtmrt.client import QTMRTClient
from util.logging import setup_logging

setup_logging(console_log_output="stdout", console_log_level="info", console_log_color=True,
              logfile_file="experiment.log", logfile_log_level="info", logfile_log_color=False,
              log_line_template="%(color_on)s[%(created)d] [%(threadName)s] [%(levelname)-8s] %(message)s%(color_off)s")

logger = logging.getLogger("Experiment Dashboard")

# sys._excepthook = sys.excepthook
#
#
# def exception_hook(exctype, value, traceback):
#     sys._excepthook(exctype, value, traceback)
#     sys.exit(1)
#
#
# sys.excepthook = exception_hook

from PyQt5.QtWidgets import QApplication, QMainWindow

from main_window_ui import Ui_MainWindowUI


class Window(QMainWindow, Ui_MainWindowUI):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.qtm_client = None
        self.driver = None
        lsl_event_channel_info = StreamInfo('EMBLDEvents', 'Markers', 1, 0, 'string', 'EMBLDEventStream')
        self.lsl_outlet = StreamOutlet(lsl_event_channel_info)

    def start_simulation(self):
        error = not self.__check_subject_form_validity()
        if error:
            self.statusbar.showMessage("Please fill in the fields in RED before staring the simulation...", 4000)
            logging.error("Cannot start simulation: all required fields not satisfied!")
        else:
            logger.info("Starting simulation")
            self.__set_start_experiment_ui_elements()
            try:
                logger.info("Starting acquisition driver...")
                self.driver = EMBLDAcquisitionDriver(self.lsl_outlet)

                logger.info("Starting driver simulation...")
                status_slot = None if not self.simulation_mode.isChecked() else self.qtm_client.send_event

                logger.info("Generating configurations...")
                num_configurations = self.driver.generate_configurations()
                self.experiment_progress.setMinimum(0)
                self.experiment_progress.setMaximum(num_configurations)

                self.driver.run_experiment(timer_slot=self.status_time_label.setText,
                                           qtm_status_slot=status_slot,
                                           lsl_status_slot=self.lsl_outlet,
                                           status_label_slot=self.status_protocol.setText,
                                           waiting_next_slot=self.waiting_for_next_step)

                logger.debug("Starting QTM capture..")
                if not self.simulation_mode.isChecked():
                    self.qtm_client.new_measurement()
                self.qtm_client.start_capture(True)
            except Exception as e:
                self.statusbar.showMessage(str(e))

    #
    # def stop_simulation(self):
    #     logger.info("Stopping simulation")
    #     self.status_state_label.setText("STOPPED")
    #     self.status_state_label.setStyleSheet("color:red;")
    #
    #     self.experiment_progress.setValue(0)
    #     self.status_time_label.setText("00'00''00")
    #
    #     self.driver.stop_threads()
    #     del self.driver
    #     self.driver = None
    #     self.qtm_client.stop_capture()

    def waiting_for_next_step(self):
        logger.info("Pausing until next step is triggered...")
        self.status_state_label.setStyleSheet("color:orange;")
        self.status_state_label.setText("READY")
        self.next_button.setEnabled(True)
        self.driver.pause_until_next_step()

    def next_step(self):
        logger.info("Moving onto next step")
        self.status_state_label.setText("RUNNING")
        self.status_state_label.setStyleSheet("color:green;")
        self.next_button.setEnabled(False)
        self.experiment_progress.setValue(self.experiment_progress.value() + 1)
        self.driver.next_step()

    def connect_qtm(self, toggle_on: bool):
        if toggle_on:
            try:
                logger.info(f"Connecting to QTM @ RT://{self.qtm_hostname.text()}:{self.qtm_port.text()}")
                if self.qtm_use_authentication.isChecked():
                    self.qtm_client = QTMRTClient("127.0.0.1", 22222, self.qtm_password.text())
                else:
                    self.qtm_client = QTMRTClient("127.0.0.1", 22222)
                self.qtm_client.connect()

                self.__update_ui_qtm_connection_successful()

                calibration_status = self.qtm_client.get_calibration_status()

                self.qtm_client.new_measurement()

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


        else:
            self.__update_ui_qtm_disconnection()
            # self.qtm_client.close_measurement()
            self.qtm_client.disconnect()
            del self.qtm_client
            self.qtm_client = None
            logger.info("Disconnecting from QTM")

    def __check_subject_form_validity(self):
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

        return not error

    def __set_start_experiment_ui_elements(self):
        self.exp_subject_id_label.setStyleSheet("color:black;")
        self.exp_age_label.setStyleSheet("color:black;")
        self.exp_gender_label.setStyleSheet("color:black;")
        self.qtm_connect_btn.setStyleSheet("background-color:none;")

        self.status_state_label.setText("RUNNING")
        self.status_state_label.setStyleSheet("color:green;")
        self.next_button.setEnabled(False)
        self.qtm_group.setEnabled(False)
        self.experiment_group.setEnabled(False)
        self.play_button.setEnabled(False)

    def __update_ui_qtm_connection_successful(self):
        self.qtm_connection_status.setText("Connected")
        self.qtm_connection_status.setStyleSheet("color:green; font-size:1em;")
        self.qtm_connect_btn.setStyleSheet("background-color:lightgreen;color:black;")
        self.qtm_hostname.setEnabled(False)
        self.qtm_port.setEnabled(False)
        self.qtm_use_authentication.setEnabled(False)
        self.auth_frame.setEnabled(False)

    def __update_ui_qtm_disconnection(self):
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

    def send_sync_event(self):
        self.qtm_client.send_event("sync")
        self.lsl_outlet.push_sample(['sync'])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
