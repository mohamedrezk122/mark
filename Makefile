format:
	isort mark/
	black mark/ --preview --enable-unstable-feature string_processing --line-length=88

lint:
	flake8 mark/ --ignore=E501


install:
	pip3 install -e .

dev:
	pip3 install -e .["dev"]
