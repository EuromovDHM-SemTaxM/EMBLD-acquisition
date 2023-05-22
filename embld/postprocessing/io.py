from pathlib import Path


def recurse_downwards_input_hierarchy(path: Path):
    leaf_directories = []
    if path.is_dir():
        children = list(path.iterdir())
        if children[0].is_dir():
            for child in children:
                leaf_directories.extend(recurse_downwards_input_hierarchy(child))
        else:
            leaf_directories.append(path)
    return leaf_directories