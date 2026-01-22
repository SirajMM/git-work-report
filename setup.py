from setuptools import setup

setup(
    name="git-work-report",
    version="1.0.0",
    py_modules=["cli"],
    install_requires=[
        "openpyxl",
        "google-generativeai",
        "openai",
    ],
    entry_points={
        "console_scripts": [
            "git-report=cli:main",
        ],
    },
)
