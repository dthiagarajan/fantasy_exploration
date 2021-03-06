from pathlib import Path
from typing import Any, Union

from prefect.engine.results import LocalResult


def load_result(checkpoint_dir: Union[str, Path], date: str, name: str) -> Any:
    """Loads a Prefct checkpointed result from file for the given date.

    Args:
        date (str): date to load the checkpoint from
        name (str): name of the file (stem, e.g. 'p' if file name is 'p.prefect')

    Returns:
        Any
    """
    result_existence = LocalResult(dir=Path(checkpoint_dir).as_posix()).exists(
        location=Path(date, f'{name}.prefect').as_posix()
    )
    assert (
        result_existence
    ), f'Result must exist, checked {Path(checkpoint_dir, date).as_posix()} for {name}.prefect.'
    return (
        LocalResult(dir=Path(checkpoint_dir).as_posix())
        .read(location=Path(date, f'{name}.prefect').as_posix())
        .value
    )
