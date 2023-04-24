import logging
from pathlib import Path

from embld.acquisition.metadata_recorder import MetadataRecorder
from embld.acquisition.qtm_recorder import QTMMocapRecorder
from embld.configuration import APP_PARAMETERS
from embld.experiment.experiment_driver import EMBLDAcquisitionDriver
from gui.dashboard_view import DashboardView
from util.logging import setup_logging
from util.timer import now_absolute

logger = logging.getLogger("Experiment Dashboard")

from PyQt5.QtWidgets import QApplication


class ExperimentGUIController:
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
            logger.debug("Starting simulation")
            self.view.set_start_experiment_ui_elements()
            # try:
            logger.debug("Starting acquisition driver...")
            self.driver = EMBLDAcquisitionDriver()

            metadata = self.subject_metadata()

            base_output_path = APP_PARAMETERS["base_output_path"]
            Path(base_output_path).mkdir(exist_ok=True)

            trial_segments = APP_PARAMETERS["trial_segments"]

            logger.info("Registering recorders...")
            recorders = {
                "metadata": MetadataRecorder(metadata, trial_segments=trial_segments, inst=1),
                #"metadata2": MetadataRecorder(metadata, trial_segments=trial_segments, inst=2),
                "mocap": QTMMocapRecorder(metadata, trial_segments=trial_segments, sampling_rate=APP_PARAMETERS["sampling_rate"]),
                # 'fnirs': ArtinisFNIRSRecorder(metadata, trial_segments=trial_segments)
            }

            logger.debug("Generating configurations...")
            self.driver.generate_configurations()
            
            resume = self.view.exp_session_resume.value()

            status_label_slot = self.view.get_status_slot()
            num_configurations = self.driver.run_experiment(
                timer_slot=self.set_timer,
                status_label_slot=status_label_slot,
                waiting_next_slot=self.waiting_for_next_step,
                ready_for_next_slot=self.ui_ready_for_next,
                increment_segment_slot=self.view.increment_running,
                metadata=metadata,
                recorders=recorders,
                resume=resume
            )
            self.view.set_progressbar_start_experiment(num_configurations)
            self.time = now_absolute()
            
            self.driver.connect_experiment_end(QApplication.quit)

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
        logger.debug("Pausing until next step is triggered...")
        self.view.show_time()
        self.time = now_absolute()
        self.driver.pause_until_next_step()

    def next_step(self):
        logger.debug("Moving onto next step")
        self.view.set_next_step()
        self.driver.next_step()

    def send_sync_event(self):
        self.driver.emit_sync()

    def subject_metadata(self):
        return self.view.subject_metadata()
