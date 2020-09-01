"""
Setup.py file.
Install once-off with:  "pip install ."
For development:        "pip install -e .[dev]"
"""

import setuptools

with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

project_name = "ada_tools"

setuptools.setup(
    name=project_name,
    version="0.1",
    description="Satelite image preprocessing utilities",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=install_requires,
    extras_require={
        "dev": [  # Place NON-production dependencies in this list - so for DEVELOPMENT ONLY!
            "black",
            "flake8"
        ],
    },
    entry_points={
        'console_scripts': [
            f"load_images = {project_name}.data_processing.get_images_Maxar:main",
            f"filter_images = {project_name}.data_processing.filter_images:main"
        ]
    }
)
