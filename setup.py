from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# Get version from __version__ variable in mn_payments/__init__.py
from mn_payments import __version__ as version

setup(
    name="mn_payments",
    version=version,
    description="Mongolian Payment Gateway Integration",
    author="Digital Consulting Service LLC",
    author_email="support@yourcompany.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        # SDK-only dependencies (without Frappe)
        "sdk": [
            "requests>=2.31.0",
            "qrcode[pil]>=7.4.2",
            "python-barcode>=0.15.1",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
    ],
    keywords="mongolian payments qpay ebarimt tax receipt frappe",
    project_urls={
        "Documentation": "https://github.com/yourorg/mn_payments",
        "Source": "https://github.com/yourorg/mn_payments",
        "Tracker": "https://github.com/yourorg/mn_payments/issues",
    },
)
