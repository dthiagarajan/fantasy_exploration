from pathlib import Path
from typing import List

from setuptools import find_namespace_packages, setup


def read(filename: Path) -> str:
    contents: str = filename.open().read()
    return contents


def read_lines(filename: Path) -> List[str]:
    return filename.open().readlines()


def read_version(file_path: Path) -> str:
    version_module = {}
    with file_path.open() as f:
        exec(f.read(), version_module)
    return version_module['__version__']


setup(
    name='fantasy-analysis',
    version=read_version(Path("src/fantasy/version.py")),
    license='MIT',
    author='Dilip Thiagarajan',
    author_email='dthiagar@gmail.com',
    url='https://github.com/dthiagarajan/fantasy_exploration',
    python_requires='>=3.6',
    description='Library for doing analysis on a fantasy basketball league',
    long_description=read(Path('README.md')),
    packages=find_namespace_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=read_lines(Path("requirements.txt")),
    scripts=['scripts/write_all_statistics'],
    classifiers=[
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
    ],
)
