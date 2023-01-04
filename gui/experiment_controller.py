import logging

from embld.experiment.protocol import EMBLDAcquisitionDriver
from gui.dashboard_view import DashboardView
from util.logging import setup_logging
from util.timer import now_absolute

setup_logging(console_log_output="stdout", console_log_level="info", console_log_color=True,
              logfile_file="experiment.log", logfile_log_level="info", logfile_log_color=False,
              log_line_template="%(color_on)s[%(created)d] [%(threadName)s] [%(levelname)-8s] %(message)s%(color_off)s")

logger = logging.getLogger("Experiment Dashboard")


class ExperimentGUIController():

    def __init__(self, view: DashboardView):
        super().__init__()
        self.driver = None
        self.view = view
        self.view.connect_start_simulation(self.start_simulation)
        self.view.connect_next(self.next_step)
        self.view.connect_sync(self.send_sync_event)
        self.time = 0.0

    def start_simulation(self):
        error = not self.view.check_subject_form_validity()
        if error:
            logging.error("Cannot start simulation: all required fields not satisfied!")
        else:
            logger.info("Starting simulation")
            self.view.set_start_experiment_ui_elements()
            # try:
            logger.info("Starting acquisition driver...")
            self.driver = EMBLDAcquisitionDriver()

            logger.info("Generating configurations...")
            num_configurations = self.driver.generate_configurations()
            status_label_slot = self.view.get_status_slot()
            num_configurations = self.driver.run_experiment(timer_slot=self.set_timer,
                                                            status_label_slot=status_label_slot,
                                                            waiting_next_slot=self.waiting_for_next_step,
                                                            ready_for_next_slot=self.ui_ready_for_next,
                                                            increment_segment_slot=self.view.increment_running,
                                                            metadata=self.subject_metadata())
            self.view.set_progressbar_start_experiment(num_configurations)
            self.time = now_absolute()

            # except Exception as e:
            #     print(e)
            #     exit(-1)

    def set_timer(self, now):
        time = now_absolute() - self.time
        seconds, ms = divmod(time, 1000)
        minutes, seconds = divmod(seconds, 60)
        self.view.update_time(f"{minutes:02.0f}'{seconds:02.0f}''")

    def ui_ready_for_next(self):
        self.view.set_ready_for_next()
        self.time = now_absolute()

    def waiting_for_next_step(self):
        logger.info("Pausing until next step is triggered...")
        self.view.show_time()
        self.time = now_absolute()
        self.driver.pause_until_next_step()

    def next_step(self):
        logger.info("Moving onto next step")
        self.view.set_next_step()
        self.driver.next_step()

    def send_sync_event(self):
        self.driver.emit_sync()

    def subject_metadata(self):
        return self.view.subject_metadata()
