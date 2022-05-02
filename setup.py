from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="typedi",
    version="0.6.0",
    description="Simple yet powerful typed dependency injection container",
    url="https://github.com/bshishov/typedi",
    author="Boris Shishov",
    author_email="borisshishov@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    py_modules=["typedi"],
    package_dir={"": "src"},
    package_data={"typedi": ["py.typed"]},  # Providing type annotations (PEP 561)
    packages=find_packages(where="src"),
    license="MIT",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
    ],
    python_requires=">=3.7",
    extras_require={"dev": ["pytest", "black", "mypy", "coverage", "pytest-cov"]},
)
