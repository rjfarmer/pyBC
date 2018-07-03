#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>

int get_jmp_buf(){
		return sizeof(jmp_buf);
}

FILE* get_file_ptr(const char * restrict filename){
	FILE *fp;
	fp = fopen(filename,"w");
	return fp;
}

void close_file_ptr(FILE *fp){
	fclose(fp);
}
