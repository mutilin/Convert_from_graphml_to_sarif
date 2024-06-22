SPECIFICATION := 

all: runcode

runcode:
	python3 converter/src/main.py $(SPECIFICATION)