from setuptools import find_packages, setup

VERSION = "0.2.3"
with open("README.md", "r", encoding='utf-8') as r:
    long_desc = r.read()
setup(
    name="terminus_utils",       # Name of your package
    version=VERSION,           # Version of your package
    description="A common utility library for Python",
    author="Prashant Yadav",
    author_email="prashant.yadav@terminus.com",
    packages=find_packages(),
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/prashant-yadav-dev/terminus_utils",
    install_requires=[
        # List your package dependencies here
        'forex-python', 'CurrencyConverter'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",  # Python versions supported
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",  # License type
        "Operating System :: OS Independent",  # OS compatibility
    ],
    python_requires='>=3.8',  # Minimum Python version required
    keywords="utilities, python, common_utilities",

)
