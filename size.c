#include <stdio.h>
#include <setjmp.h>


int get_size_t(){
		return sizeof(size_t);
}

int get_jmp_buf(){
		return sizeof(jmp_buf);
}

