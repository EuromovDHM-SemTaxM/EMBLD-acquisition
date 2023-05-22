import argparse
import json
from pathlib import Path

import tqdm

from embld.postprocessing.io import recurse_downwards_input_hierarchy
from embld.postprocessing.razor import (
    DispatchingRazor,
    FNIRSRecordingRazor,
    MocapRecordingRazor,
    SoundRecordingRazor,
)

parser = argparse.ArgumentParser(
    description="Postprocessing: Cut excess from captured data to keep only the trial segments"
)
parser.add_argument(
    "--input",
    type=str,
    help="Path to the input directory. Should contain raw recordings (json, c3d, mp3, etc.) or subdirectory trees where the raw data files are the leaves. The same structure will be kept for the target directory.",
    required=True,
)

parser.add_argument(
    "--output",
    type=str,
    help="Path to the output directory. The same structure as the input will be kept for the output",
)


def create_razor():
    return razor


if __name__ == "__main__":
    args = parser.parse_args()

    input_path = Path(args.input[0])
    output_directory = Path(args.output[0])

    input_directories = recurse_downwards_input_hierarchy(input_path)

    razor = DispatchingRazor()
    razor.add_razors(
        [MocapRecordingRazor(), FNIRSRecordingRazor(), SoundRecordingRazor()]
    )

    for directory in tqdm(input_directories, desc="Razor-cutting input directories"):
        annotation_files = list(directory.glob("*.json"))
        for annotation_file in annotation_files:
            metadata = json.load(annotation_file.open())
            segment_timings = [segment["onset"] for segment in metadata["segments"]]
            file_basename = annotation_file.file.suffix[0]
            data_files = list(directory.glob(f"{file_basename}*"))
            razor(data_files, output_directory, segment_timings)

