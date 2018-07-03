import os,sys
import ctypes
import subprocess
import structs 

import utils


bc = ctypes.cdll.LoadLibrary(utils.get_lib_loc())

structs.build_structs()
