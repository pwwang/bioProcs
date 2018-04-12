"""
Reader and writer for tsv file.
"""
import sys, inspect
from pyppl import Box
from bioprocs.utils import alwaysList
from collections import OrderedDict

def _getargs(args, func):
	argnames = inspect.getargspec(func).args
	return {k:v for k, v in args.items() if k in argnames}

__all__ = ['TsvMeta', 'TsvRecord', 'TsvReader', 'TsvWriter', 'tsvops']

class NoSuchReader(Exception):
	pass

class NoSuchWriter(Exception):
	pass

class TsvMeta(OrderedDict):
	"""
	Tsv meta data
	"""
	def __init__(self, *args):
		"""
		arg could be a string, a tuple or a list:
		'a', ('b': int) or ['c', 'd']
		"""
		super(TsvMeta, self).__init__()
		self.add(*args)

	def __repr__(self):
		return 'TsvMeta(%s)' % ', '.join([k if not v else '%s=%s'%(k,v.__name__) for k,v in self.items()])

	def __getattr__(self, name):
		if not name.startswith('_OrderedDict'):
			return self[name]
		super(TsvMeta, self).__getattr__(name)
		
	def __setattr__(self, name, val):
		if not name.startswith('_OrderedDict'):
			self[name] = val
		else:
			super(TsvMeta, self).__setattr__(name, val)
	
	def add(self, *args):
		for arg in args:
			if isinstance(arg, list):
				for a in arg: self[a] = None
			elif isinstance(arg, tuple):
				if arg[1] and not callable(arg[1]):
					raise TypeError('Expect callable for meta value.')
				self[arg[0]] = arg[1]
			else:
				self[arg] = None
	
	def append(self, *args):
		self.add(*args)
		
	def prepend(self, *args):
		preps = []
		for arg in args:
			if isinstance(arg, list):
				for a in arg: preps.append((a, None))
			elif isinstance(arg, tuple):
				if arg[1] and not callable(arg[1]):
					raise TypeError('Expect callable for meta value.')
				preps.append(arg)
			else:
				preps.append((arg, None))
				
		preps += self.items()
		self.clear()
		for k, v in preps:
			self[k] = v
		
class TsvRecord(dict):
		
	def __repr__(self):
		return 'TsvRecord(%s)' % (', '.join([k + '=' + repr(v) for k, v in self.items()]))
	
	def __getattr__(self, name):
		return self[name]

	def __setattr__(self, name, val):
		self[name] = val
		
class TsvReaderBase(object):
	def __init__(self, infile, delimit = '\t', comment = '#', skip = 0):
		openfunc = open
		if infile.endswith('.gz'):
			import gzip
			openfunc = gzip.open

		self.meta    = TsvMeta()
		self.file    = openfunc(infile)
		self.delimit = delimit
		self.comment = comment
		self.tell    = 0
		
		if skip > 0:
			for _ in range(skip):
				self.file.readline()
		self.tell = self.file.tell()
		
	def autoMeta(self, prefix = 'COL'):
		line = self.file.readline()
		while self.comment and line.startswith(self.comment):
			line = self.file.readline()
		self.rewind()
		line = line.rstrip('\n').split(self.delimit)
		cols = [prefix + str(i+1) for i in range(len(line))]
		self.meta.add(*cols)

	def _parse(self, line):
		record = TsvRecord()
		for i, key in enumerate(self.meta.keys()):
			try:
				record[key] = self.meta[key](line[i]) if self.meta[key] else line[i]
			except IndexError:
				record[key] = ''
		return record

	def next(self):
		line = self.file.readline()
		while self.comment and line.startswith(self.comment):
			line = self.file.readline()
		line = line.rstrip('\n')
		# empty lines not allowed
		if not line: raise StopIteration()
		return self._parse(line.split(self.delimit))

	def dump(self):
		return [r for r in self]

	def rewind(self):
		self.file.seek(self.tell)

	def __iter__(self):
		return self

	def __del__(self):
		self.close()
			
	def close(self):
		if self.file:
			self.file.close()

class TsvReaderBed(TsvReaderBase):
	META = [
		('CHR'   , None),
		('START' , int),
		('END'   , int),
		('NAME'  , None),
		('SCORE' , float),
		('STRAND', None)
	]

	def __init__(self, infile, skip = 0, comment = '#', delimit = '\t'):
		super(TsvReaderBed, self).__init__(infile, skip = skip, comment = comment, delimit = delimit)
		self.meta = TsvMeta(*TsvReaderBed.META)
		self.index = 1

	def _parse(self, line):
		r = super(TsvReaderBed, self)._parse(line)
		if not r.NAME: 
			r.NAME = 'BED' + str(self.index)
			self.index += 1
		if not r.SCORE: r.SCORE   = 0.0
		if not r.STRAND: r.STRAND = '+'
		return r
		
class TsvReaderBed12(TsvReaderBase):
	META = [
		('CHR'         , None),
		('START'       , int),
		('END'         , int),
		('NAME'        , None),
		('SCORE'       , float),
		('STRAND'      , None),
		('THICKSTART'  , int),
		('THICKEND'    , int),
		('ITEMRGB'     , None),
		('BLOCKCOUNT'  , int),
		('BLOCKSIZES'  , None),
		('BLOCKSTARTS' , None)
	]

	def __init__(self, infile, skip = 0, comment = '#', delimit = '\t'):
		super(TsvReaderBed12, self).__init__(infile, skip = skip, comment = comment, delimit = delimit)
		self.meta = TsvMeta(*TsvReaderBed12.META)
		
class TsvReaderBedpe(TsvReaderBase):
	META = [
		('CHR1'    , None),
		('START1'  , int),
		('END1'    , int),
		('CHR2'    , None),
		('START2'  , int),
		('END2'    , int),
		('NAME'    , None),
		('SCORE'   , float),
		('STRAND1' , None),
		('STRAND2' , None)
	]

	def __init__(self, infile, skip = 0, comment = '#', delimit = '\t'):
		super(TsvReaderBedpe, self).__init__(infile, skip = skip, comment = comment, delimit = delimit)
		self.meta = TsvMeta(*TsvReaderBedpe.META)

class TsvReaderBedx(TsvReaderBase):
	META = [
		('CHR'   , None),
		('START' , int),
		('END'   , int),
		('NAME'  , None),
		('SCORE' , float),
		('STRAND', None)
	]

	def __init__(self, infile, skip = 0, comment = '#', delimit = '\t', xcols = None, headprefix = ''):
		super(TsvReaderBedx, self).__init__(infile, skip = skip, comment = comment, delimit = delimit)
		self.meta = TsvMeta(*TsvReaderBedx.META)
		
		xmeta = OrderedDict()
		if not xcols:
			pass
		elif isinstance(xcols, list):
			for xcol in xcols:
				xmeta[xcol] = None
		elif isinstance(xcols, dict):
			for xcol, callback in xcols.items():
				if not callable(callback):
					raise TypeError('Expect callable for xcols values.')
				xmeta[xcol] = callback
		else:
			xmeta[xcols] = None
		self.meta.add(*xmeta.items())
		
class TsvReaderHead(TsvReaderBase):

	def __init__(self, infile, comment = '#', delimit = '\t', skip = 0, tmeta = None):
		super(TsvReaderHead, self).__init__(infile, skip = skip, comment = comment, delimit = delimit)
		self.meta = TsvMeta()
		
		header = self.file.readline().strip('#\t\n ').split(delimit)
		self.tell = self.file.tell()
		row1   = self.file.readline().strip().split(delimit)
		if len(row1) == len(header) + 1:
			header.insert(0, 'ROWNAMES')
		metatype = OrderedDict()
		for head in header:
			metatype[head] = None if not tmeta or not isinstance(tmeta, dict) or not head in tmeta or not callable(tmeta[head]) else tmeta[head]
		self.meta.add(*metatype.items())
		
		self.rewind()

class TsvReaderNometa(TsvReaderHead):

	def __init__(self, infile, comment = '#', delimit = '\t', skip = 0, head = True, tmeta = None):
		if head:
			super(TsvReaderNometa, self).__init__(infile, skip = skip, comment = comment, delimit = delimit, tmeta = tmeta)
		else:
			super(TsvReaderHead, self).__init__(infile, skip = skip, comment = comment, delimit = delimit)
	
	def _parse(self, line):
		return line
		
class TsvWriterBase(object):
	def __init__(self, outfile, delimit = '\t'):
		openfunc = open
		if outfile.endswith('.gz'):
			import gzip
			openfunc = gzip.open
		
		self.delimit = delimit
		self.meta    = TsvMeta()
		self.file    = open(outfile, 'w')
	
	def writeHead(self, prefix = '', delimit = None, transform = None):
		delimit = delimit or self.delimit
		keys = self.meta.keys()
		if callable(transform): 
			keys = transform(keys)
		elif isinstance(transform, dict):
			keys = [key if not key in transform or not callable(transform[key]) else transform[key](key) for key in keys]
		self.file.write(prefix + delimit.join(keys) + '\n')

	def write(self, record, delimit = None):
		delimit = delimit or self.delimit
		outs = []
		for key in self.meta.keys():
			outs.append(str(record[key]))
		self.file.write(delimit.join(outs) + '\n')

	def __del__(self):
		self.close()
			
	def close(self):
		if self.file:
			self.file.close()
			
class TsvWriterNometa(TsvWriterBase):
	
	def writeHead(self, prefix = '', delimit = None, transform = None):
		transform = transform or (lambda keys: [str(key) for key in keys])
		super(TsvWriterNometa, self).writeHead(prefix, delimit, transform)
		
	def write(self, record, delimit = None):
		delimit = delimit or self.delimit
		self.file.write(delimit.join([str(r) for r in record]) + '\n')
		
class TsvWriterBed(TsvWriterBase):
		
	def __init__(self, outfile, delimit = '\t'):
		super(TsvWriterBed, self).__init__(outfile)
		self.meta = TsvMeta(*TsvReaderBed.META)
		
class TsvReader(object):
	# inopts: 
	# - delimit, comment, skip
	# - ftype
	# - cnames
	def __new__(cls, infile, **inopts):
		inopts2 = {'delimit': '\t', 'comment': '#', 'skip': 0, 'ftype': '', 'cnames': ''}
		inopts2.update(inopts)
		inopts = inopts2
		ftype  = inopts['ftype']
		cnames = inopts['cnames']
		if not isinstance(cnames, dict):
			cnames = alwaysList(cnames)
		del inopts['ftype']
		del inopts['cnames']
		
		if not ftype:
			inopts = _getargs(inopts, TsvReaderBase.__init__)
			reader = TsvReaderBase(infile, **inopts)
		else:
			klass = 'TsvReader' + ftype[0].upper() + ftype[1:].lower()
			if not klass in globals():
				raise NoSuchReader(klass)
			klass  = globals()[klass]
			inopts = _getargs(inopts, klass.__init__)
			reader = klass(infile, **inopts)
		if cnames:
			metas = cnames if isinstance(cnames, list) else cnames.items()
			reader.meta.add(*metas)
		return reader
				
			
class TsvWriter(object):
	def __new__(cls, outfile, **outopts):
		outopts2 = {'delimit': '\t', 'ftype': '', 'cnames': ''}
		outopts2.update(outopts)
		outopts  = outopts2
		ftype    = outopts['ftype']
		cnames   = outopts['cnames']
		if not isinstance(cnames, dict):
			cnames = alwaysList(cnames)
		del outopts['ftype']
		del outopts['cnames']
		
		if not ftype:
			outopts = _getargs(outopts, TsvWriterBase.__init__)
			writer = TsvWriterBase(outfile, **outopts)
		else:
			klass = 'TsvWriter' + ftype[0].upper() + ftype[1:].lower()
			if not klass in globals():
				raise NoSuchWriter(klass)
			klass = globals()[klass]
			outopts = _getargs(outopts, klass.__init__)
			writer = klass(outfile, **outopts)
		if cnames:
			metas = cnames if isinstance(cnames, list) else cnames.items()
			writer.meta.add(*metas)
		return writer
		
class SimRead (object):
	
	def __init__(self, *files, **kwargs):

		length = len(files)
		
		self.match   = SimRead._defaultMatch
		self.do      = None
		self.comment = ["#"] * length
		self.delimit = ["\t"] * length
		self.skip    = [0] * length
		self.debug   = kwargs['debug'] if 'debug' in kwargs else False
		self.ftype   = [''] * length
		self.cnames  = [''] * length

		if 'match' in kwargs:
			self.match = kwargs['match']
		if 'do' in kwargs:
			self.do    = kwargs['do']
		if 'delimit' in kwargs and kwargs['delimit']:
			if not isinstance(kwargs['delimit'], (tuple, list)):
				self.delimit = [kwargs['delimit']] * length
			else:
				self.delimit[:len(kwargs['delimit'])] = list(kwargs['delimit'])
		if 'skip' in kwargs and kwargs['skip']:
			if not isinstance(kwargs['skip'], (tuple, list)):
				self.skip = [kwargs['skip']] * length
			else:
				self.skip[:len(kwargs['skip'])] = list(kwargs['skip'])
		if 'comment' in kwargs and kwargs['comment']:
			if not isinstance(kwargs['comment'], (tuple, list)):
				self.comment = [kwargs['comment']] * length
			else:
				self.comment[:len(kwargs['comment'])] = list(kwargs['comment'])
		if 'ftype' in kwargs and kwargs['ftype']:
			if not isinstance(kwargs['ftype'], (tuple, list)):
				self.ftype = [kwargs['ftype']] * length
			else:
				self.ftype[:len(kwargs['ftype'])] = list(kwargs['ftype'])
		if 'cnames' in kwargs and kwargs['cnames']:
			if not isinstance(kwargs['cnames'], (tuple, list)):
				self.cnames = [kwargs['cnames']] * length
			else:
				self.cnames[:len(kwargs['cnames'])] = list(kwargs['cnames'])

		self.readers = []
		for i, fn in enumerate(files):
			inopts = {
				'ftype'  : self.ftype[i],
				'cnames' : self.cnames[i],
				'delimit': self.delimit[i],
				'skip'   : self.skip[i],
				'comment': self.comment[i]
			}
			reader = TsvReader(fn, **inopts)
			if not reader.meta: reader.autoMeta()
			self.readers.append(reader)
			
	@staticmethod
	def compare(a, b, reverse = False):
		print a, b
		if not reverse:
			return 0 if a < b else 1 if a > b else -1
		else:
			return 0 if a > b else 1 if a < b else -1
			
	@staticmethod
	def _defaultMatch(*lines):
		data = [line[0] for line in lines]
		mind = min(data)
		if data.count(mind) == len(lines):
			return -1
		else:
			return data.index(mind)

	def run (self):
		if not self.do:
			raise AttributeError('You would like to do something when lines are matched.')
		try:
			lines = [next(reader) for reader in self.readers]
		except StopIteration:
			return
		if self.debug:
			sys.stderr.write('- Lines initiated ...\n')
			
		while True:
			if self.debug:
				sys.stderr.write('\n'.join([('  > FILE %s: [' % (i+1)) + str(line) + ']' for i, line in enumerate(lines)]) + '\n')
			if not all(lines): break
			
			try:
				m = self.match(*lines)
			except Exception as ex:
				msgs = [str(ex) + ' in MATCH function:']
				for k, line in enumerate(lines):
					msgs.append('File %s: %s' % (k+1, line))
				raise type(ex)('\n'.join(msgs) + '\n')
			if self.debug:
				sys.stderr.write('  Match returns: %s\n' % m)
			if m < 0:
				if self.debug:
					sys.stderr.write('  All lines matched, do stuff.\n')
				try:
					self.do(*lines)
				except Exception as ex:
					msgs = [str(ex) + ' in DO function:']
					for k, line in enumerate(lines):
						msgs.append('File %s: %s' % (k+1, line))
					raise type(ex)('\n'.join(msgs) + '\n')
				m = 0
			if self.debug:
				sys.stderr.write('- File %s is behind, read it ...\n' % (m+1))
			try:
				lines[m] = next(self.readers[m])			
			except StopIteration:
				break

def tsvops(infile, outfile, inopts, outopts, ops = None):

	inopts2 = Box(delimit = '\t', comment = '#', skip = 0, ftype = '', cnames = '')
	inopts2.update(inopts)
	inopts = inopts2
	
	outopts2 = Box(delimit = '\t', headPrefix = '', headDelimit = '\t', headTransform = None, head = True, ftype = '', cnames = '')
	outopts2.update(outopts)
	outopts = outopts2
	
	inftype       = inopts['ftype']
	outftype      = outopts['ftype']
	head          = outopts['head']
	headPrefix    = outopts['headPrefix']
	headDelimit   = outopts['headDelimit']
	headTransform = outopts['headTransform']
	del outopts['head']
	del outopts['headPrefix']
	del outopts['headDelimit']
	del outopts['headTransform']
	
	reader = TsvReader(infile, **inopts)
	if not reader.meta: reader.autoMeta()
	
	if not outftype and not outopts['cnames']:
		outftype = 'reader'
		
	if outftype == 'reader':
		del outopts['ftype']
		writer = TsvWriter(outfile, **outopts)
		writer.meta.prepend(*reader.meta.items())
	else:
		writer = TsvWriter(outfile, **outopts)
		
	if head:
		writer.writeHead(prefix = headPrefix, delimit = headDelimit, transform = headTransform)
	
	for r in reader:
		if callable(ops):
			r = ops(r)
			if not r: continue
		writer.write(r)

	