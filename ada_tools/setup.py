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
            f"load_images = {project_name}.get_images_maxar:main",
            f"filter_images = {project_name}.filter_images:main",
            f"filter_buildings = {project_name}.filter_buildings:main",
            f"final_layer = {project_name}.final_layer:main",
            f"get_osm = {project_name}.get_osm_data_in_bbox:main",
            f"prepare_data = {project_name}.prepare_data_for_caladrius:main",
        ]
    }
)
