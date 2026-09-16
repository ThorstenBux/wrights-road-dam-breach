# Wrights Road Storage Ponds – dam-breach flood model pipeline
# Usage:  make env && conda activate damflood && make all SCENARIO=east
SHELL := /bin/bash
PY ?= python
SCENARIO ?= east
MODE ?= shakedown        # shakedown | extended (full domain to Diversion Road, 20 m) | production

.PHONY: env test dem vectors breach run post all clean offline

env:
	conda env create -f environment.yml || conda env update -f environment.yml

test:
	$(PY) -m pytest -q tests

dem:
	$(PY) scripts/01_fetch_dem.py --mode $(MODE)

vectors:
	$(PY) scripts/02_fetch_vectors.py

breach:
	$(PY) scripts/03_breach_hydrograph.py --scenario $(SCENARIO)

run:
	$(PY) scripts/04_run_model.py --scenario $(SCENARIO) --mode $(MODE)

compare:
	$(PY) scripts/06_compare.py --scenario $(SCENARIO) --mode $(MODE)

post:
	$(PY) scripts/05_postprocess.py --scenario $(SCENARIO) --mode $(MODE)

all: dem vectors breach run post

# Self-contained copy of the site for venues without internet: unzip, open START-HERE.html.
offline:
	rm -f wrights-road-dam-breach-offline.zip
	cp docs/index.html docs/START-HERE.html
	zip -qr wrights-road-dam-breach-offline.zip docs -x 'docs/*.md' 'docs/.DS_Store' '*/.DS_Store'
	rm docs/START-HERE.html
	@ls -lh wrights-road-dam-breach-offline.zip

clean:
	rm -rf outputs/* data/derived/*
