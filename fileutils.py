import os.path
import re
import string
from pylab import transpose, array#, float

#from wave import Wave, Spectrum

#This is a regexp that must recognize a line of data for it to be loaded!
datare=re.compile('\s*(-?\d+(\.\d*)?([Ee][+-]?\d+)?(,\s*|\s+|$)){2,}')

def load(fname=None,datastr=None,comments='#',delimiter=None, converters=None,skiprows=0,
		 usecols=None, userows=-1, unpack=False):
	"""
	Norped from matplotlib/mlab.py and modified...
	"""

	if converters is None: converters = {}

	if type(fname)==str:
		if fname.endswith('.gz'):
			import gzip
			fh = gzip.open(fname)
		else:
			fh = file(fname)
	elif hasattr(fname, 'seek'):
		fh = fname
	else:
		#raise ValueError('fname must be a string or file handle')
		fh=datastr.split("\n")
	X = []

	converterseq = None
	for i,ln in enumerate(fh):
		if i<skiprows: continue
		#print ln
		line = ln
		#[:ln.find(comments)].strip()
		#print line
		if (not len(line)) or (datare.match(line) is None):
#			print "nix"
			continue
		if converterseq is None:
#			print "making converterseq..."
			converterseq = [converters.get(j,float) for j,val in
							enumerate(map(lambda s: s.strip(", \t"), line.split(delimiter)))]
		if usecols is not None:
			vals = line.split(delimiter)
			row = [converterseq[j](vals[j]) for j in usecols]
		else:
			row = [converterseq[j](val) for j,val in enumerate(map(lambda s: s.strip(", \t"), line.split(delimiter)))]
		thisLen = len(row)
		#print row
		X.append(row)

	X = array(X, float)
	r,c = X.shape
	if r==1 or c==1:
		X.shape = max([r,c]),
	if unpack: return transpose(X)
	else:  return X



def load_data(filename=None, datastr=None, skip_rows=False,use_cols=False):
	"""Load a file with numeric column data into a numpy array.
	Automatically skips header unless "skip_rows" is specified.
	Loads all columns unless "use_cols" is specified."""

	if filename is not None:
		textiter = open(filename, 'r')
	else:
		textiter = iter(datastr.split("\n"))
	#datare=re.compile('\s*(-?\d+(\.\d+)?([Ee][+-]?\d+)?(\s+|$)){2,}')

	if skip_rows == False:
		skip_rows=0
		nx=textiter.next()
		while datare.match(nx)==None:
#			print "skipping row ", skip_rows
			skip_rows+=1
			print nx
			nx=textiter.next()

		if filename is not None:
			textiter.close()
			textiter = open(filename, 'r')
#		else:
#			textiter=iter(datastr.split("\n"))
	if use_cols:
		tmp_data=load(textiter,datastr,skiprows=skip_rows,usecols=use_cols)
	else:
		tmp_data=load(textiter,datastr,skiprows=skip_rows)
	if filename is not None:
		textiter.close()
	return transpose(tmp_data)

def loadmeta(filename,sample_col=1,edge_col=2,type_col=3):
	infile = open(filename,"r")
	rows=[]
#	path=filename[0:-len(filename.split("/")[-1])]
	file=""
	sample="None"
	type="None"
	edge="None"
	lines=infile.readlines()
	for line in lines:
		if not line[0] == "#":
			s=line.rstrip().split("\t") #dela upp raden efter tabbar
			file=s[0].rstrip() #ta bort radreturer...
			if len(s) > sample_col and s[sample_col].rstrip() != "":
				sample=s[sample_col].rstrip()
			if len(s) > edge_col and  s[edge_col].rstrip() != "":
				edge=s[edge_col].rstrip()
			if len(s) > type_col and s[type_col].rstrip() != "":
				type=s[type_col].rstrip()
			rows.append([file,sample,edge,type])

	return rows

def makemeta(path,regexp):
	files=sorted(os.listdir(path))
	#print files
	endre=re.compile(regexp)
	for f in files:
		a=endre.match(f)
		if a:
			b=a.group(1)
			s=b.split("_")
			#print f
			print f + "\t" + reduce(lambda x,y:x+"\t"+y,s[1:])
