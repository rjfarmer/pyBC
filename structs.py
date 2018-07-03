import ctypes
import os
import collections
import re
import subprocess

import utils

# binary c structures

allStructs={}


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
	
	sizes = ctypes.cdll.LoadLibrary(utils.get_cutils_loc())
	jmp_buf_size = sizes.get_jmp_buf()
	
	skip = {"FILE":ctypes.sizeof(ctypes.c_void_p),"size_t":ctypes.c_size_t,"jmp_buf":jmp_buf_size}
	
	for i in res:
		for j in res[i]:
			if res[i][j]['spec']:
				if res[i][j]['type'] in skip.keys():
					res[i][j]['size'] = skip[res[i][j]['type']]
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
		if v['struct']:
			dep.append(v['type'])
	return list(set(dep))
	
	
def order_struct_dependencies(struct_names):
	debug = False
	ordered_names = collections.OrderedDict()
	dep = {}
	for name,st in struct_names.items():
		dep[name] = compute_dependencies(st)
	
	print(dep)
	
	all_deps = list(dep.keys())
	
	# These come from standard libs
	special_cases = ["hsearch_data"]
	
	lenOld = len(all_deps)
	while len(all_deps):
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
						if(debug): print("Removed",i,"from",key,"Remiaing",dep[key])

		if len(all_deps) == lenOld:
			print()
			print("Failed to find")
			fails = []
			for k, v in dep.items():
				fails.extend(v)
			
			for i in set(fails):
				print(i)
			break
			
		lenOld = len(all_deps)
				
	# print(ordered_names)				
	return ordered_names
	
	
		
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
			'void':ctypes.c_void_p
			}
		
	st = order_struct_dependencies(struct_names)	
		
		# names = []
		# types = []
		# for k,s in st.items():
			# names.append(k)
			# t = mapTypes[s['type']]
			# for i in range(s['pointer']):
				# t = ctypes.POINTER(t)
			# types.append(t)
		# make_struct(name,names,types)
			
			
	
	#hanlde arrays [], embedding structs


