format:
	isort mark/
	black mark/ 

lint:
	flake8 mark/ --ignore=E501


install:
	pip3 install -e .

dev:
	pip3 install -e .["dev"]
