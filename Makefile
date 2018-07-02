all:
	gcc -fPIC -shared -o libsizes.so size.c

phony: all
