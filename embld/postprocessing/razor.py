from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any


class RecordingRazor(metaclass=ABCMeta):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def __call__(
        self, file: Path, target_directory: Path, segment_timings: list[float]
    ) -> Any:
        pass

    @abstractmethod
    def handles_formats(self) -> list[str]:
        pass


class DispatchingRazor(RecordingRazor):
    def __init__(self) -> None:
        super().__init__()
        self.razors = []

    def __call__(
        self, file: Path, target_directory: Path, segment_timings: list[float]
    ) -> Any:
        for razor in self.razors:
            if file.suffix[1:] in razor.handles_formats():
                razor(file, target_directory, segment_timings)

    def handles_formats(self) -> list[str]:
        return [razor.handles_formats() for razor in self.razors]

    def add_razors(self, razors: list[RecordingRazor]) -> None:
        self.razors.extend(razors)


class MocapRecordingRazor(RecordingRazor):
    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self, file: Path, target_directory: Path, segment_timings: list[float]
    ) -> Any:
        import ezc3d

        c3d = ezc3d.c3d(file)
        sampling_rate = c3d["parameters"]["POINT"]["RATE"]["value"][0]
        c3d["data"]["points"] = c3d["data"]["points"][
            :, :, segment_timings[0] * sampling_rate :
        ]
        c3d.write(str(target_directory / file.name))

    def handles_formats(self) -> list[str]:
        return ["c3d"]


class FNIRSRecordingRazor(RecordingRazor):
    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self, file: Path, target_directory: Path, segment_timings: list[float]
    ) -> Any:
        import mne

        raw = mne.io.read_raw_fif(file, preload=True)
        raw.crop(tmin=segment_timings[0])
        raw.save(target_directory / file.name, overwrite=True)

    def handles_formats(self) -> list[str]:
        return ["fif"]


class SoundRecordingRazor(RecordingRazor):
    def __init__(self) -> None:
        super().__init__()

    def __call__(
        self, file: Path, target_directory: Path, segment_timings: list[float]
    ) -> Any:
        import pydub

        extension = file.suffix[1:]

        segment = pydub.AudioSegment.from_file(file, extension)
        segment = segment[
            segment_timings[0] * 1000 :
        ]  # segments are indexed in milliseconds
        if "mp3" in extension:
            info = pydub.utils.mediainfo(file)
            segment.export(
                target_directory / file.name, format="mp3", bitrate=info["bit_rate"]
            )
        else:
            segment.export(target_directory / file.name, format=extension)

    def handles_formats(self) -> list[str]:
        return ["wav", "mp3"]
