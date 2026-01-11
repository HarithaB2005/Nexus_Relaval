from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="nexus-releval",
    version="1.0.0",
    author="Nexus Releval Team",
    author_email="support@nexusreleval.com",
    description="Official Python SDK for Nexus Releval AI Auditor API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nexusreleval/python-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-cov>=4.0", "black>=23.0"],
    },
    keywords="ai audit safety medical financial nlp llm",
    project_urls={
        "Documentation": "https://docs.nexusreleval.com",
        "Source": "https://github.com/nexusreleval/python-sdk",
        "Bug Reports": "https://github.com/nexusreleval/python-sdk/issues",
    },
)
