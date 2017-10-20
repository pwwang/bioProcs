from pyppl import Proc
from . import params
"""
A set of procs to handle sequences
"""

"""
@name:
	pConsv
@description:
	Get the conservation scores of regions.
	It uses wigFix to find the conservation scores.
	But first you have to convert those wigFix.gz files to bigWig files using ucsc-wigToBigWig
@input:
	`bedfile:file`: The bedfile with regions in the same chromosome
	`bwdir:file`:   The bigwig directory, the bigwig files must be named as "chrN.*"
	- For example: `chr1.phyloP30way.bw`
@output:
	`outdir:dir`    The output file, containing the output file, random regions and their scores if pvalue is calulated
@args:
	`bin-bwtool`:   The path of bwtool executable. Default: `bwtool`
	`bin-bedtools`: The path of bedtools executable. Default: `bedtools`
	`calcp`:        Whether to calculate the pvalue for not for each region.
	`nperm`:        The number of permutations of pvalue is calcuated.
	`seed`:         The seed to generate the random regions.
	`gsize`:        The genome size file for generating random regions.
	- Can be a local file or a file hosted at UCSC: http://hgdownload.cse.ucsc.edu/goldenPath/<genome>/bigZips/<genome>.chrom.sizes
@requires:
	[bwtool](https://github.com/CRG-Barcelona/bwtool)
	[bedtools](http://bedtools.readthedocs.io/en/latest/content/bedtools-suite.html) if `calcp` is `True`
"""
pConsv = Proc()
pConsv.input  = "bedfile:file, bwdir:file"
pConsv.output = "outdir:dir:{{bedfile | fn}}.consv"
pConsv.args   = {"calcp": True, "nperm": 10000, "seed": 0, "gsize": "", "bin-bwtool": "bwtool", "bin-bedtools": "bedtools"}
pConsv.lang   = "python"
pConsv.script = """
from subprocess import Popen
from sys import exit, stderr
from os  import path
from glob import glob
from urllib import urlretrieve

def consv4bed (bedfile, avglen = True):
	chrbeds   = {}
	totalen   = 0
	nrecord   = 0
	fn        = path.splitext (path.basename (bedfile))[0]
	with open (bedfile) as f:
		for line in f:
			line  = line.strip()
			if not line or line.startswith("#"): continue
			parts = line.split("\\t")
			if not chrbeds.has_key (parts[0]):
				chrbeds[parts[0]] = open ( path.join("{{outdir}}", "%s.%s.bed" % (fn, parts[0])), "w" )
			chrbeds[parts[0]].write (line + "\\n")
			totalen += int (parts[2]) - int (parts[1])
			nrecord += 1
	if nrecord == 0:
		stderr.write ("Input file is empty: %s" % bedfile)
		exit (1)
	
	# get consv for each chrom bed file
	for chrom, fh in chrbeds.iteritems():
		fh.close()
		bwfile = glob ("{{bwdir}}/%s.*" % chrom)[0]
		cmd    = "{{args.bin-bwtool}} summary %s %s %s -skip-median -header -fill=0" % (fh.name, bwfile, path.join("{{outdir}}", "%s.%s.consv.txt" % (fn, chrom)))	
		try:
			Popen (cmd, shell=True).wait()
		except Exception as ex:
			stderr.write ( "Failed to get conservation scores for bedfile: %s" % bedfile)
			stderr.write ( "Error: %s" % ex)
			exit (1)
	if avglen: return int (totalen / nrecord)

def pval (score, permscores):
	for i, pscore in enumerate (permscores):
		if pscore < score:
			return float (i) / float ({{args.nperm}})
	return 0.0

avglen = consv4bed ("{{bedfile}}")
if {{args.calcp}}:
	# generate a random bed file with region width avglen
	gsize = "{{args.gsize}}"
	if gsize.startswith ("http"):
		gsizebname = path.basename (gsize)
		gsizefile  = path.join ("{{outdir}}", gsizebname)
		urlretrieve (gsize, gsizefile)
		gsize      = gsizefile
	permfile = path.join ("{{outdir}}", "permutations.bed")
	cmd = 'bedtools random -n {{args.nperm}} -l %s -g %s -seed {{args.seed}} > "%s"' % (avglen, gsize, permfile)
	try:
		Popen (cmd, shell=True).wait()
	except Exception as ex:
		stderr.write( "Failed to generated permutation file: %s" % ex)
		exit (1)
	
	consv4bed (permfile, False)
	
	# get scores
	permscores = []
	for pfile in glob ("{{outdir}}/permutations.*.consv.txt"):
		with open (pfile) as f:
			for line in f:
				line = line.strip()
				if not line or line.startswith("#"): continue
				permscores.append (float(line.split("\\t")[7]))
	permscores = sorted (permscores, reverse=True)
	
	outfile    = path.join ("{{outdir}}", "result.consv.txt")
	fout       = open (outfile, "w")
	for ofile in glob ("{{outdir}}/{{bedfile | fn}}.*.consv.txt"):
		with open (ofile) as f:
			for line in f:
				line = line.strip()
				if not line: continue
				if line.startswith ("#"):
					fout.write (line + "\\tpvalue\\n")
					continue
				score = float(line.split("\\t")[7])
				fout.write (line + "\\t%.2E\\n" % pval(score, permscores))
	fout.close()
"""


"""
@name:
	pPromoters
@description:
	Get the promoter regions in bed format of a gene list give in genefile.
@input:
	`genefile:file`: the gene list file
@output:
	`outfile:file`: the bed file containing the promoter region
@args:
	`up`: the upstream to the tss, default: 2000
	`down`: the downstream to the tss, default: 2000
	`genome`: the genome, default: hg19
@require:
	[python-mygene](http://mygene.info/)
"""
pPromoters              = Proc(desc = 'Get the promoter regions in bed format of a gene list give in genefile.')
pPromoters.input        = "genefile:file"
pPromoters.output       = "outfile:file:{{in.genefile | fn}}-promoters.bed"
pPromoters.args.up      = 2000
pPromoters.args.down    = 2000
pPromoters.args.genome  = params.genome.value
pPromoters.errhow       = 'retry'
pPromoters.lang         = params.python.value
pPromoters.script       = "file:scripts/seq/pPromoters.py"
