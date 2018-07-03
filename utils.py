import os 
import subprocess

def get_bin_c_dir():
	if 'BINARY_C_DIR' not in os.environ:
		BINARY_C_DIR  = os.path.expandvars('$HOME/src/binary_c')
	else:
		BINARY_C_DIR = os.environ.get('BINARY_C_DIR')
	return BINARY_C_DIR

def get_lib_loc():
	return os.path.join(get_bin_c_dir(),'src','libbinary_c.so')
	
def get_cutils_loc():
	dir_path = os.path.dirname(os.path.realpath(__file__))
	return os.path.join(dir_path,'libcutils.so')
	

def rebuild():
    cwd = os.getcwd()
    os.chdir(get_bin_c_dir())
    try:
        subprocess.call('./configure')
        subprocess.call('./make')
        subprocess.call('./make libbinary_c.so')
    except:
        print("FAILED rebuild")
    finally:
        os.chdir(cwd)
