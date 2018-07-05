import collections
import utils

from elftools.elf.elffile import ELFFile
from elftools.dwarf.descriptions import describe_attr_value, set_global_machine_arch
from elftools.common.py3compat import itervalues


with open(utils.get_lib_loc(),'rb') as f:
	elffile = ELFFile(f)
	if elffile.has_dwarf_info():
		dwarfinfo = elffile.get_dwarf_info()
	else:
		dwarfinfo = None
	
	machine_arch = set_global_machine_arch(elffile.get_machine_arch())
	
	
	if not dwarfinfo.has_debug_info:
		raise ValueError("No debug ino")
	
	# Offset of the .debug_info section in the stream
	section_offset = dwarfinfo.debug_info_sec.global_offset
	
	data = []
	
	for cu in dwarfinfo.iter_CUs():
		pointer_size = cu['address_size']
	
		# The nesting depth of each DIE within the tree of DIEs must be
		# displayed. To implement this, a counter is incremented each time
		# the current DIE has children, and decremented when a null die is
		# encountered. Due to the way the DIE tree is serialized, this will
		# correctly reflect the nesting depth
		#
		die_depth = 0
		for die in cu.iter_DIEs():		
			rr = collections.OrderedDict()
			rr['die_depth'] = die_depth
			rr['offset'] = die.offset
			rr['abbrev_code'] =  die.abbrev_code
			rr['die_null'] = die.is_null()
			rr['section_offset'] = section_offset
		
			if die.is_null():
				die_depth -= 1
				continue
	
			for attr in itervalues(die.attributes):
				r = collections.OrderedDict()
				name = attr.name
				# Unknown attribute values are passed-through as integers
				if isinstance(name, int):
					raise ValueError("Unknown attribute")
	
				r['name'] = name
				r['attr_offset'] = attr.offset
				r['attr_value'] = describe_attr_value(attr, die, section_offset)
				r['has_child'] = die.has_children
				
				r.update(rr)
	
			if die.has_children:
				die_depth += 1
	
			data.append(r)
	
