from setuptools import setup

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='typedi',
    version='0.5.0',
    description='Simple yet powerful typed dependency injection container',
    url='https://github.com/bshishov/typedi',
    author='Boris Shishov',
    author_email='borisshishov@gmail.com',
    long_description=long_description,
    long_description_content_type='text/markdown',
    py_modules=['typedi'],
    license="MIT",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries'
    ],
    python_requires='>=3.6',
    extras_require={
        'dev': [
            'pytest',
            'coverage',
            'pytest-cov'
        ]
    }
)
