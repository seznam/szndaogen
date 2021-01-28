#!/usr/bin/python3
from setuptools import find_packages, setup
from szndaogen.tools.setuptools import get_file_content, get_file_content_as_list

packages = find_packages()
print(f"Found packages: {packages}")
VERSION = get_file_content("szndaogen/VERSION")
INSTALL_REQUIRES = get_file_content_as_list("requirements.txt")
DOCUMENTATION_MD = get_file_content("README.md")

setup(
    name="szndaogen",
    version=VERSION,
    author="Ales Adamek, Filip Cima, Richard Paprok",
    author_email="hpo.sport@firma.seznam.cz",
    description="SZN Database Access Object Generator for MySQL. Generates Models and DataManagers from existing MySQL database structure.",
    long_description=DOCUMENTATION_MD,
    long_description_content_type="text/markdown",
    url="https://github.com/seznam/szndaogen",
    packages=packages,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=INSTALL_REQUIRES,
    include_package_data=True,  # MANIFEST.in
    zip_safe=False,  # aby se spravne vycitala statika pridana pomoci MANIFEST.in
    entry_points={"console_scripts": ["szndaogen=szndaogen.cli:main"]},
)
