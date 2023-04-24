from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QRadioButton,
    QButtonGroup,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
)

from gui.main_windows_rc import *

class DashboardView(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.status_protocol = None
        self.status_time_label = None
        self.status_state_label = None
        self.experiment_progress = None
        self.exp_gender_label = None
        self.subject_notes = None
        self.gender_radio_group = None
        self.exp_session_label = None
        self.exp_session = None
        self.exp_age_label = None
        self.exp_age = None
        self.exp_subject_id_label = None
        self.exp_subject_id = None
        self.START_WINDOW_WIDTH = 1024
        self.START_WINDOW_HEIGHT = 850

        self._status_bar = None
        self.play_button = None
        self.next_button = None
        self.event_button = None

        self.running_state = 0

        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("MainWindowUI")
        self.resize(self.START_WINDOW_WIDTH, self.START_WINDOW_HEIGHT)
        self.setMinimumSize(
            QtCore.QSize(self.START_WINDOW_WIDTH, self.START_WINDOW_HEIGHT)
        )
        self.setWindowTitle("EMBLD Acquisiton Dashboard")

        self._status_bar = self.statusBar()
        self._status_bar.setMinimumWidth(self.START_WINDOW_WIDTH)
        self._status_bar.showMessage("Ready")
        # self.status_bar.setContentsMargins(0, 50, 0, 0)

        root_widget = QWidget(self)
        root_widget.setMinimumSize(self.minimumSize())
        layout = QVBoxLayout(self)
        root_widget.setLayout(layout)

        top_panel = QWidget(root_widget)
        top_panel.setMinimumWidth(self.START_WINDOW_WIDTH)

        top_panel_layout = QHBoxLayout()
        top_panel.setLayout(top_panel_layout)

        top_label = QLabel("EMBLD Dashboard")
        top_label.setStyleSheet("font-family: Segoe UI Semilight; font-size:32pt;")
        top_label.setAlignment(Qt.AlignCenter)
        top_panel_layout.addWidget(top_label)

        button_container = QWidget()
        button_hbox = QHBoxLayout()
        button_container.setLayout(button_hbox)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/play.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.play_button = QPushButton(icon, "", top_panel)
        self.play_button.setIconSize(QtCore.QSize(64, 64))
        self.play_button.setMaximumWidth(64)
        self.play_button.setShortcut("Ctrl+S")
        button_hbox.addWidget(self.play_button)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/next.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.next_button = QPushButton(icon, "", top_panel)
        self.next_button.setIconSize(QtCore.QSize(64, 64))
        self.next_button.setMaximumWidth(64)
        self.next_button.setShortcut("Return")
        self.next_button.setEnabled(False)
        button_hbox.addWidget(self.next_button)

        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(":/transition.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off
        )
        self.event_button = QPushButton(icon, "", top_panel)
        self.event_button.setIconSize(QtCore.QSize(64, 64))
        self.event_button.setMaximumWidth(64)
        self.event_button.setShortcut("Space")
        self.event_button.setEnabled(False)
        button_hbox.addWidget(self.event_button)

        top_panel_layout.addWidget(button_container)
        top_panel.setMinimumHeight(top_panel_layout.sizeHint().height())
        layout.addWidget(top_panel, 0)

        self.subject_panel = QGroupBox("Experiment Setting")
        self.subject_panel.setMinimumWidth(self.START_WINDOW_WIDTH - 20)
        self.subject_panel.setStyleSheet(
            "font-family: Segoe UI Semilight; font-size:16pt;"
        )

        subject_panel_layout = QHBoxLayout(root_widget)
        self.subject_panel.setLayout(subject_panel_layout)

        left_subject_pane = QWidget(self.subject_panel)
        left_subject_pane_layout = QFormLayout(left_subject_pane)
        left_subject_pane.setLayout(left_subject_pane_layout)
        left_subject_pane_layout.setVerticalSpacing(50)
        subject_panel_layout.addWidget(left_subject_pane)

        self.exp_subject_id = QLineEdit()
        self.exp_subject_id.setStyleSheet(
            "font-family: Segoe UI Semilight; font-size:12pt;"
        )
        self.exp_subject_id_label = QLabel("Subject Identifier*")
        self.exp_subject_id_label.setStyleSheet("font-weight:bold;font-size:12pt;")
        left_subject_pane_layout.addRow(self.exp_subject_id_label, self.exp_subject_id)

        self.exp_age = QSpinBox()
        self.exp_age.setMinimum(-1)
        self.exp_age.setValue(-1)
        self.exp_age.setStyleSheet("font-family: Segoe UI Semilight; font-size:12pt;")
        self.exp_age_label = QLabel("Age*")
        self.exp_age_label.setStyleSheet("font-weight:bold;font-size:10pt;")
        left_subject_pane_layout.addRow(self.exp_age_label, self.exp_age)

        self.exp_session = QSpinBox()
        self.exp_session.setValue(1)
        self.exp_session.setStyleSheet(
            "font-family: Segoe UI Semilight; font-size:12pt;"
        )
        self.exp_session_label = QLabel("Session Number")
        self.exp_session_label.setStyleSheet("font-size:10pt;")
        left_subject_pane_layout.addRow(self.exp_session_label, self.exp_session)
        
        self.exp_session_resume = QSpinBox()
        self.exp_session_resume.setValue(-1)
        self.exp_session_resume.setStyleSheet(
            "font-family: Segoe UI Semilight; font-size:12pt;"
        )
        
        self.exp_session_resume_label = QLabel("Resume at:")
        self.exp_session_resume_label.setStyleSheet("font-size:10pt;")
        left_subject_pane_layout.addRow(self.exp_session_resume_label, self.exp_session_resume)

        right_subject_pane = QWidget(self.subject_panel)
        right_subject_pane_layout = QFormLayout(right_subject_pane)
        # right_subject_pane_layout.set
        right_subject_pane.setLayout(right_subject_pane_layout)
        right_subject_pane_layout.setVerticalSpacing(50)
        subject_panel_layout.addWidget(right_subject_pane)

        male_radio = QRadioButton("Male")
        male_radio.setStyleSheet("font-family: Segoe UI Semilight; font-size:12pt;")
        female_radio = QRadioButton("Female")
        female_radio.setStyleSheet("font-family: Segoe UI Semilight; font-size:12pt;")
        other_radio = QRadioButton("Other")
        other_radio.setStyleSheet("font-family: Segoe UI Semilight; font-size:12pt;")
        self.gender_radio_group = QButtonGroup()
        self.gender_radio_group.addButton(female_radio)
        self.gender_radio_group.addButton(other_radio)
        self.gender_radio_group.addButton(male_radio)
        radio_h = QWidget(right_subject_pane)
        radio_h_layout = QHBoxLayout()
        radio_h.setLayout(radio_h_layout)
        radio_h_layout.addWidget(female_radio)
        radio_h_layout.addWidget(other_radio)
        radio_h_layout.addWidget(male_radio)
        self.exp_gender_label = QLabel("Biological gender*")
        self.exp_gender_label.setAlignment(Qt.AlignCenter)
        self.exp_gender_label.setStyleSheet("font-weight:bold;font-size:12pt;")
        right_subject_pane_layout.addRow(self.exp_gender_label, radio_h)

        self.subject_notes = QPlainTextEdit(right_subject_pane)
        self.subject_notes.setStyleSheet("font-size:12pt;")
        self.subject_notes.setMaximumHeight(50)
        subject_notes_label = QLabel("Subject notes")
        subject_notes_label.setStyleSheet("font-size:12pt;")
        right_subject_pane_layout.addRow(subject_notes_label, self.subject_notes)
        layout.addWidget(self.subject_panel, 0)

        self.subject_panel.setMinimumHeight(subject_panel_layout.sizeHint().height())

        status_panel = QGroupBox("Experiment Status")
        status_panel.setMinimumWidth(self.START_WINDOW_WIDTH - 20)
        status_panel.setStyleSheet("font-family: Segoe UI Semilight; font-size:16pt;")

        status_panel_layout = QVBoxLayout()
        status_panel.setLayout(status_panel_layout)

        upper_status_pane = QWidget(status_panel)
        upper_status_pane_layout = QHBoxLayout()
        upper_status_pane.setLayout(upper_status_pane_layout)

        self.status_state_label = QLabel("STOPPED")
        self.status_state_label.setStyleSheet("color:red; font-size:32pt;")
        self.status_state_label.setAlignment(Qt.AlignCenter)
        upper_status_pane_layout.addWidget(self.status_state_label)

        self.status_time_label = QLabel("00'00''00")
        self.status_time_label.setAlignment(Qt.AlignCenter)
        self.status_time_label.setStyleSheet("font-size:40pt;")
        self.status_time_label.setVisible(False)
        upper_status_pane_layout.addWidget(self.status_time_label)
        status_panel_layout.addWidget(upper_status_pane)

        self.status_protocol = QLabel("")
        self.status_protocol.setMinimumHeight(300)
        self.status_protocol.setStyleSheet("font-size:20pt;boder: 1px solid black")
        self.status_protocol.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.status_protocol.setAlignment(Qt.AlignCenter)
        self.status_protocol.setWordWrap(True)

        status_panel_layout.addWidget(self.status_protocol)

        layout.addWidget(status_panel)

        layout.addStretch(1)
        self.experiment_progress = QProgressBar(root_widget)
        self.experiment_progress.setMinimum(1)
        self.experiment_progress.setMaximum(100)
        self.experiment_progress.setFormat("%v / %m (%p%)")
        layout.addWidget(self.experiment_progress)

        # layout.addSpacerItem(QtWidgets.QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # layout.addStretch(1)

    def check_subject_form_validity(self):
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
        checked_button = self.gender_radio_group.checkedButton()
        if checked_button is None:
            error = True
            self.exp_gender_label.setStyleSheet("color:red;")
        else:
            self.exp_gender_label.setStyleSheet("color:black;")

        if error:
            self._status_bar.showMessage(
                "Please fill in the fields in RED before staring the simulation...",
                4000,
            )

        return not error

    def set_start_experiment_ui_elements(self):
        self.exp_subject_id_label.setStyleSheet("color:black;")
        self.exp_age_label.setStyleSheet("color:black;")
        self.exp_gender_label.setStyleSheet("color:black;")
        self.running_state = 0
        self.status_state_label.setText("PRESS SPACE TO START")
        self.status_state_label.setStyleSheet("color:orange;")
        self.status_time_label.setVisible(False)
        self.next_button.setEnabled(False)
        self.event_button.setEnabled(True)
        self.subject_panel.setEnabled(False)
        self.play_button.setEnabled(False)

    def increment_running(self):
        self.status_state_label.setStyleSheet("color:green;")
        self.status_state_label.setText(f"RUNNING {self.running_state}")
        self.running_state += 1

    def set_progressbar_start_experiment(self, num_configurations):
        if self.exp_session_resume.value() != -1:
            self.experiment_progress.setValue(self.exp_session_resume.value())
        else:
            self.experiment_progress.setMinimum(0)
        self.experiment_progress.setMaximum(num_configurations)

    def set_ready_for_next(self):
        self.status_time_label.setVisible(False)
        self.status_protocol.setText("")
        self.running_state = 0
        self.status_state_label.setStyleSheet("color:orange;")
        self.status_state_label.setText("PRESS RETURN FOR NEXT")
        self.next_button.setEnabled(True)
        self.event_button.setEnabled(False)

    def set_next_step(self):
        self.status_state_label.setText("PRESS SPACE TO START")
        self.status_state_label.setStyleSheet("color:orange;")
        self.next_button.setEnabled(False)
        self.event_button.setEnabled(True)
        self.experiment_progress.setValue(self.experiment_progress.value() + 1)

    def get_status_slot(self):
        return self.status_protocol.setText

    def show_time(self):
        self.status_time_label.setVisible(True)

    def subject_metadata(self):
        metadata = {"id": self.exp_subject_id.text()}
        metadata["age"] = self.exp_age.text()
        metadata["sex"] = self.gender_radio_group.checkedButton().text()
        metadata["notes"] = self.subject_notes.toPlainText()
        metadata["session"] = self.exp_session.value()
        return metadata

    def connect_start_simulation(self, slot):
        self.play_button.clicked.connect(slot)

    def connect_next(self, slot):
        self.next_button.clicked.connect(slot)

    def connect_sync(self, slot):
        self.event_button.clicked.connect(slot)

    def update_time(self, text):
        self.status_time_label.setText(text)
