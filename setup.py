from setuptools import setup, find_packages

setup(
    name="invoices_project",
    version="1.0.0",
    description="Extraction et reporting des factures depuis Gmail",
    author="TonNom",
    packages=find_packages(),
    install_requires=[
        "pdfplumber",
        "openpyxl"
    ],
    entry_points={
        "console_scripts": [
            "run-invoices=invoices.main:main"
        ]
    }
)
