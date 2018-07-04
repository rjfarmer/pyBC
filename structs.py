import ctypes
import os
import collections
import re
import subprocess
import numpy as np

import utils

# binary c structures

allStructs={}
arraySize={}

def check_enabled():
	# Find which flags have been enabled:
	bin_c_dir = utils.get_bin_c_dir()
	LIB = utils.get_lib_loc()
	
	#All flags
	allFlags = subprocess.check_output("grep -rihI 'ifdef' "+bin_c_dir+"/src/*.{c,h} | sort | uniq",shell=True)
	allFlags = [str(x.decode()) for x in allFlags.split() if b'#' not in x]
	
	FNULL = open(os.devnull, 'w')
	enabledFlags=[]
	for i in allFlags:
		x = subprocess.run(["grep","-xF",str(i),LIB],stdout=FNULL, stderr=subprocess.STDOUT)
		if x.returncode == 0:
			enabledFlags.append(i)

	return enabledFlags

def get_structs():
	bin_c_dir = utils.get_bin_c_dir()
	LIB = utils.get_lib_loc()
	
	filename = bin_c_dir+"/src/binary_c_structures.h"
	
	with open(filename,'r') as f:
		lines =f.readlines()
		
	s = []
	add = False
	skip = False
	for i in lines:
		ii=i.strip()
		if (ii.startswith('/*') and '*/' in ii) or ii.startswith('//'):
			skip=False
			continue
		if ii.startswith('/*'):
			skip=True
		if ii.startswith('*/'):
			skip=False
			continue
		if skip or len(i.strip())==0:
			continue
		if i.startswith('struct'):
			add = True
			s.append([])
		if i.startswith('};') or i.endswith('};'):
			add = False
		if add:
			s[-1].append(i.strip())
	
	types = ['int','double','unsigned','signed','Boolean','long','const','char','Aligned','void']
	
	res = collections.OrderedDict()
	for idi,i in enumerate(s):
		name = i[0].split()[1]
		res[name] = collections.OrderedDict()
		ifdef = ''
		for j in i[1:]:
			j = j.strip()
			if j.startswith("/*") or len(j)==0 or j.startswith('*') or j.startswith('{'):
				continue
			if ';' in j:
				j=j[:j.index(';')]
			l=re.split(" |,",j)
			
			if '#if' in j:
				ifdef = j.split()[1]
				continue
			if '#endif' in j:
				ifdef = None
				continue
			
			ll=[]
			x=''
			for i in l:
				if set(i)<=set('*'):
					x=i
				else:
					ll.append(x+i)
					x=''
			l=ll
			
			typ=[]
			if l[0] == 'struct':
				for k in l[2:]:
					p = k.count('*') + l[1].count('*')
					res[name][k] = {'type':l[1],'struct':True,'spec':False,'ifdef':ifdef,'pointer':p}
			elif l[0] in types:
				for idk,k in enumerate(l):
					if k not in types:
						break
				t = " ".join(l[:idk])
				for kk in l[idk:]:
					p = kk.count('*') + t.count('*')
					res[name][kk] = {'type':t,'struct':False,'spec':False,'ifdef':ifdef,'pointer':p}
			else:
				for k in l[1:]:
					p = k.count('*') + l[0].count('*')
					res[name][k] = {'type':l[0],'struct':False,'spec':True,'ifdef':ifdef,'pointer':p}
	
	#resolve unknown types
	files = [bin_c_dir+"/src/binary_c_types.h",
			# bin_c_dir+"/src/supernovae/sn.h",
			# bin_c_dir+"/src/nucsyn/nucsyn_element_to_atomic_number.c",
			# bin_c_dir+"/src/setup/cmd_line_args.h"
			]
	
	lines=[]
	for i in files:
		with open(i,'r') as f:
			lines.extend(f.readlines())
		
	bctypes={}
	for i in lines:
		if '#define' in i:
			z=i.split()
			bctypes[z[1]]=' '.join(z[2:])
	
	skip = set(("FILE","size_t","jmp_buf"))
	
	for i in res:
		for j in res[i]:
			if res[i][j]['spec']:
				if res[i][j]['type'] in skip:
					res[i][j]['size'] = None
					continue
				try:
					t = bctypes[res[i][j]['type']]
				except KeyError:
					print("Can't match "+str(res[i][j]['type'])+" for "+str(i)+" "+str(j))
					continue
				res[i][j]['spec']=False
				if 'struct' in t:
					res[i][j]['struct']=True
					res[i][j]['type'] = t.split()[1]
				else:
					res[i][j]['type'] = t
					
	#Remove unneeded elements
	flagsOn = check_enabled()
	for i in list(res.keys()):
		for j in list(res[i].keys()):
			if res[i][j]['ifdef']:
				ii = res[i][j]['ifdef']
				if not ii in flagsOn:
					del res[i][j]
				elif 'defined' in ii:
					if '||' in ii:
						ii = ii.replace('||','')
						ii = ii.replace('defined(','')
						a, b = re.split("\(*\)",ii[1:-1])[0:2]
						if not (a in flagsOn or b in flagsOn):
							del res[i][j]
					else:
						#&&
						ii = ii.replace('&&','')
						ii = ii.replace('defined(','')
						a, b = re.split("\(*\)",ii[1:-1])[0:2]
						if not (a in flagsOn and b in flagsOn):
							del res[i][j]

					
	return res
		

def make_struct(name,names,types):
	class cstruct(ctypes.Structure):
		__fields__ = [(i,j) for i,j in zip(names,types)]
	cstruct.__name__ = name
	return cstruct


def compute_dependencies(struct):
	dep = []
	for k,v in struct.items():
		if v['struct'] and v['pointer'] == 0: #Skip pointers we dont need their actual size (its c_void_p)
			dep.append(v['type'])
	return list(set(dep))
	
	
def order_struct_dependencies(struct_names):
	debug = False
	ordered_names = collections.OrderedDict()
	dep = {}
	for name,st in struct_names.items():
		dep[name] = compute_dependencies(st)
	
	if(debug): print(dep)
	
	all_deps = list(dep.keys())
	
	# These come from standard libs
	special_cases = ["hsearch_data"]
	
	lenOld = len(all_deps)
	max_loops = 100
	while True:
		if len(all_deps) == 0:
			break
		if max_loops == 0:
			break
		max_loops = max_loops -1
		if(debug): print("Loop ",len(all_deps))
		for key in all_deps:
			if not len(dep[key]):
				ordered_names[key]=''
				all_deps.remove(key)
				if(debug): print("Added",key)
			else:
				for i in dep[key]:
					if i in ordered_names or i in special_cases:
						dep[key].remove(i)
						if(debug): print("Removed",i,"from",key,"Remaining",dep[key])

		lenOld = len(all_deps)
	if max_loops == 0:
		print()
		print("Failed to find")
		fails = []
		for k, v in dep.items():
			fails.extend(v)
		
		for i in set(fails):
			print(i)
			
		print()
		print(dep)
		
	if debug: print(ordered_names)				
	return ordered_names
	
	
def get_array_size(value):
	#This may be [X] or [X][Y] or [Align(X)]
	value=value.replace("*",'').replace('Align(','').replace(')','')
	value = value.split('[')[1:]
	
	s=[]
	for i in value:
		add=0
		if '+' in i:
			z=i.split('+')
			add = int(z[1])
			i=z[0]
		if i.isdigit():
			s.append(int(i))
		elif i in arraySize:
			s.append(arraySize[i])
		else:	
			# Search code for define
			
			
		s[-1] = s[-1] + add
	
	return np.product(s)
	
		
def build_structs():
	bin_c_dir = utils.get_bin_c_dir()
	LIB = utils.get_lib_loc()
	
	struct_names = get_structs()
	sizes = ctypes.cdll.LoadLibrary(utils.get_cutils_loc())
	
	jmp_buf_size = sizes.get_jmp_buf()
	
	mapTypes={'int':ctypes.c_int,'double':ctypes.c_double,
			'Boolean':ctypes.c_bool,'char':ctypes.c_char,
			'FILE':ctypes.c_void_p,'size_t':ctypes.c_size_t,
			'jmp_buf':ctypes.c_char*jmp_buf_size,
			'unsigned long long int':ctypes.c_int64,
			'long int':ctypes.c_int32,
			'void':ctypes.c_void_p,
			'hsearch_data':ctypes.c_void_p,
			'unsigned int':ctypes.c_uint,
			'double Aligned':ctypes.c_double, # Aligned elements may need some work?
			'unsigned long long':ctypes.c_ulonglong,
			'const char':ctypes.c_char,
			'int Aligned':ctypes.c_int,
			'char Aligned':ctypes.c_char
			}
			
	st = order_struct_dependencies(struct_names)	
	print(st)
		
	for key in st:
		names = []
		types = []
		for k,s in struct_names[key].items():
			skip_p=False # Skip one round of pointers 
			names.append(k)
			
			if '[' in k:
				print(k)
				
			if s['struct'] and s['pointer']:
				# We make these c_void_p anyway so dont add extra wrappers
				s['pointer'] = s['pointer'] - 1
			
			if s['type'] in mapTypes:
				t = mapTypes[s['type']]
			elif s['type'] in allStructs:
				t = allStructs[s['type']]
			else:
				# If pointer to struct then we add c_void_p
				if s['pointer']:
					t = ctypes.c_void_p
				else:
					print("Cant find",s['type'],"for",key)
				
			for i in range(s['pointer']):
				t = ctypes.POINTER(t)
			types.append(t)
			allStructs[key] = make_struct(key,names,types)
			
			
	
	#hanlde arrays [], embedding structs


