"""
Setupskript.
von Niklas Elsbrock
"""

from setuptools import find_packages, setup

setup(
    name="NateMan",
    version="1.2.1",
    author="Niklas Elsbrock, Johannes Bingel",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    python_requires="~=3.6",
    install_requires=[
        "Flask",
        "Flask-SQLAlchemy>=2.0.0",
        "Click",
        "PyYAML",
        "bcrypt",
        "openpyxl"
    ],
    entry_points={"console_scripts": ["nateman = nateman.commands:cli"]}
)
