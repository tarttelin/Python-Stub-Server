.PHONY: all test clean docs

clean:
	rm -rf build/ dist/ .coverage stubserver.egg-info

test:
	python setup.py test

install:
	python setup.py install

build:
	python setup.py build
# 
# docs:
# 	cd docs && make html
