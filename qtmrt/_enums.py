from enum import Enum


class QTMEvent(Enum):
    CONNECTED = 1,
    CONNECTION_CLOSED = 2,
    CAPTURE_STARTED = 3,
    CAPTURE_STOPPED = 4,
    NOT_USED = 5,
    CALIBRATION_STARTED = 6,
    CALIBRATION_STOPPED = 7,
    RT_FROM_FILE_STARTED = 8,
    RT_FROM_FILE_STOPPED = 9,
    WAITING_FOR_TRIGGER = 10,
    CAMERA_SETTINGS_CHANGED = 11,
    QTM_SHUTTING_DOWN = 12,
    CAPTURE_SAVED = 13,
    REPROCESSING_STARTED = 14,
    REPROCESSING_STOPPED = 15,
    TRIGGER = 16




