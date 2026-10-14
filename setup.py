from setuptools import setup, find_packages

setup(
    name="optipulse",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "optipulse": ["ui/*", "ui/assets/*"],
    },
    install_requires=[
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "optipulse=optipulse.server:main",
        ],
    },
)
