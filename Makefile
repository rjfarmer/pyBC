all:
	gcc -fPIC -shared -o libcutils.so cutils.c

phony: all
