format:
	isort mark/
	black mark/ 

lint:
	flake8 mark/

install:
	pip3 install -e .

dev:
	pip3 install -e .["dev"]
