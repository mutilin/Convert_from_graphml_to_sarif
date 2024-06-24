SPECIFICATION := CHECK( init(main()), LTL(G ! data-race) )

all: runcode

runcode:
	python3 converter/src/main.py "$(SPECIFICATION)"