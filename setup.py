from setuptools import setup, find_packages

setup(
	name="mn_payments",
	version="0.1.0",
	description="Mongolian payments and ebarimt integration",
	author="Custom",
	packages=find_packages(),
	include_package_data=True,
	install_requires=[
		"frappe>=15.0.0",
		"qpay-client",
		"qrcode",
	],
)
