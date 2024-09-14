from setuptools import setup, find_packages

setup(
    name="fastblocks",
    version="0.1.3",
    author="Florian Fenzl",
    author_email="info@somebot.de",
    description="A FastAPI-compatible block manager for storing images in WebP format in bin",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/schlummer13/fastblocks",
    packages=find_packages(),
    install_requires=[
        "pillow",
        "cryptography",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
