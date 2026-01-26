from setuptools import setup, find_packages

setup(
    name="oksentinel-sdk",
    version="0.1.0",
    description="OkSentinel SDK - Enterprise Secure Content Sharing system",
    author="OkSentinel",
    packages=find_packages(include=["oksentinel", "oksentinel.*"]),
    install_requires=[
        "cryptography>=41.0.0",
        "click>=8.1.0",
    ],
    entry_points={
        'console_scripts': [
            'oksentinel-cli=cli.main:cli',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

