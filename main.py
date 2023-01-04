# This is a sample Python script.

# if __name__ == '__main__':
#     from mne_realtime import LSLClient
#
#     raw_list = []
#     with LSLClient(host="OxySoft", stream_type='NIRS') as lsl:
#         info = lsl.get_measurement_info()
#         print(info)
#         raw = lsl.get_data_as_raw(500)
#         print("Writing to file...")
#         raw.plot(n_channels=len(raw.ch_names), show_scrollbars=False)
#         raw .plot_psd(average=True)
#         # mne_nirs.io.snirf.write_raw_snirf(raw, "./test.sfnirs")
#         # print(raw.get_data().shape)
#
#     # streams = pylsl.resolve_streams(wait_time=min(0.1, 2))
#     # for stream_info in streams:
#     #     print(stream_info.as_xml())
import sys

from PyQt5.QtWidgets import QApplication

from gui.dashboard_view import DashboardView
from gui.experiment_controller import ExperimentGUIController

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DashboardView()
    controller = ExperimentGUIController(win)
    win.show()
    sys.exit(app.exec())