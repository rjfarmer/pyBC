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




