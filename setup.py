from setuptools import find_packages, setup

setup(
    name="common_utils",       # Name of your package
    version="0.1.0",           # Version of your package
    description="A common utility library for Python",
    author="Prashant Yadav",
    author_email="prashant.yadav@terminus.com",
    packages=find_packages(),
    python_requires='>=3.8',
)
