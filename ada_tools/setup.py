"""
Setup.py file.
Install once-off with:  "pip install ."
For development:        "pip install -e .[dev]"
"""
import setuptools

with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

PROJECT_NAME = "ada_tools"

setuptools.setup(
    name=PROJECT_NAME,
    version="0.1",
    description="Satellite image preprocessing utilities",
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
            f"load-images = {PROJECT_NAME}.get_images_maxar:main",
            f"load-images-azure = {PROJECT_NAME}.get_images_maxar_azure:main",
            f"filter-images = {PROJECT_NAME}.filter_images:main",
            f"filter-buildings = {PROJECT_NAME}.filter_buildings:main",
            f"get-osm-buildings = {PROJECT_NAME}.get_osm_buildings_in_raster:main",
            f"final-layer = {PROJECT_NAME}.final_layer:main",
            f"prepare-data = {PROJECT_NAME}.prepare_data_for_caladrius:main",
            f"create-index = {PROJECT_NAME}.create_index:main",
            f"setup-wd = {PROJECT_NAME}.setup_wd:main",
            f"merge-output = {PROJECT_NAME}.merge_output:main",
            f"align-raster = {PROJECT_NAME}.align_raster:main",
            f"check-alternative-buildings = {PROJECT_NAME}.check_alternative_buildings:main"
        ]
    }
)
