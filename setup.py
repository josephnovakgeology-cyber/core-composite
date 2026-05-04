# -*- coding: utf-8 -*-
"""
Created on Mon May  4 13:42:48 2026

@author: joseph novak

setup file for Core Composite
"""

from setuptools import setup, find_packages

setup(
    name="core_composite",
    version="1.0.0",
    description="Stratigraphic alignment and core photo colorimetry tool",
    author="Joseph Novak",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "matplotlib",
        "scipy",
        "scikit-image",
        "PyMuPDF"  # This is the 'fitz' library you use for PDFs
    ]
)