from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pyzello",
    version="0.1.0",
    description="A Python SDK for the Zello Channel WebSocket API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Laird86/Pyzel",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Communications",
    ],
    python_requires=">=3.7",
    install_requires=[
        "websockets>=10.0",
        "PyJWT>=2.0.0",
        "pycryptodome>=3.15.0"
    ],
)
