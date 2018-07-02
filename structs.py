import ctypes 
import re
import collections

# binary c structures

class derivative_t(ctypes.Structure)
    __fields__ = [("mass", ctypes.c_double)
				  ("eccentricity", ctypes.c_double)
				  ("specific_angular_momentum",  ctypes.c_double)
				  ("other", ctypes.c_double)]



filename = BINARY_C_DIR+"/src/binary_c_structures.h"

with open(filename,'r') as f:
	lines =f.readlines()
	
s = []
add = False
skip = False
for i in lines:
	ii=i.strip()
	if ii.startswith('/*') and '*/' in ii:
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

types = ['int','double','unsigned','signed','Boolean','long','const','char','Aligned']

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
			ifdef = ''
			continue
		
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
		print(res[name][k])
	print()

			
		
		
