from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in zelin_ac/__init__.py
from zelin_ac import __version__ as version

setup(
	name="zelin_ac",
	version=version,
	description="Zelin Accounting",
	author="yuxinyong@163.com",
	author_email="yuxinyong@163.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
