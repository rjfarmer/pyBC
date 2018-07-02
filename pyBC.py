import os,sys
import ctypes
import subprocess


if 'BINARY_C_DIR' not in os.environ:
    BINARY_C_DIR  = os.path.expandvars('$HOME/src/binary_c')
else:
    BINARY_C_DIR = os.environ.get('BINARY_C_DIR')

def rebuild():
    cwd = os.getcwd()
    os.chdir(BINARY_C_DIR)
    try:
        subprocess.call('./configure')
        subprocess.call('./make')
        subprocess.call('./make libbinary_c.so')
    except:
        print("FAILED rebuild")
    finally:
        os.chdir(cwd)

LIB = os.path.join(BINARY_C_DIR,'src','libbinary_c.so')

bc = ctypes.cdll.LoadLibrary(LIB)

sizes = ctypes.cdll.LoadLibrary('./libsizes.so')

size_t = sizes.get_size_t()
jmp_buf_size = sizes.get_jmp_buf()


def check_enabled():
	# Find which flags have been enabled:
	
	#All flags
	allFlags = subprocess.check_output("grep -rihI 'ifdef' "+BINARY_C_DIR+"/src/*.{c,h} | sort | uniq",shell=True)
	allFlags = [str(x.decode()) for x in allFlags.split() if b'#' not in x]
	
	FNULL = open(os.devnull, 'w')
	enabledFlags=[]
	for i in allFlags:
		x = subprocess.run(["grep","-xF",str(i),LIB],stdout=FNULL, stderr=subprocess.STDOUT)
		if x.returncode == 0:
			enabledFlags.append(i)

	return enabled_flags
