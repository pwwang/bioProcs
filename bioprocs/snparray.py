from pyppl import Proc, Box
from . import params
#from .utils import runcmd, helpers

"""
@name:
	pGistic
@description:
	Runing GISTIC to get CNV results.
	see: ftp://ftp.broadinstitute.org/pub/GISTIC2.0/GISTICDocumentation_standalone.htm
@input:
	`segfile:file`: Segmentation File
	`mkfile:file` : Markers File
	`alfile:file` : Array List File
	`cnvfile:file`: CNV File
@output:
	`outdir:dir`: The output directory
		- All Lesions File (all_lesions.conf_XX.txt, where XX is the confidence level)
		- Amplification Genes File (amp_genes.conf_XX.txt, where XX is the confidence level)
		- Deletion Genes File (del_genes.conf_XX.txt, where XX is the confidence level)
		- Gistic Scores File (scores.gistic)
		- Segmented Copy Number (raw_copy_number.pdf)
@args:
	`gistic`: The path to gistic.
	`genome`: The genome used to select refgene file from refgenefiles.
	`mcr`:    The mcr path
	`params`: Other params for gistic
"""
pGistic             = Proc(desc = 'Runing GISTIC to get CNV results.')
pGistic.input       = 'segfile:file, mkfile:file, alfile:file, cnvfile:file'
pGistic.output      = 'outdir:dir:{{i.segfile | fn}}.gistic'
pGistic.args.gistic = params.gistic.value
pGistic.args.genome = params.genome.value
pGistic.args.mcr    = params.mcr # 2.0 requires r2014a
pGistic.args.params = Box()
pGistic.lang        = params.python.value
pGistic.script      = "file:scripts/snparray/pGistic.py"

"""
@name:
	pSNP6Genotype
@description:
	Call genotypes from GenomeWideSNP_6 CEL file
@input:
	`celfile:file`: the CEL file
@output:
	`outfile:file`: the outfile containing probe name and genotypes
	- format: `<Probe name>\t<genotype>`
	- `<genotype>` = 0: AA, 1: AB, 2: BB
@requires:
	[bioconductor-crlmm](http://bioconductor.org/packages/release/bioc/html/crlmm.html)
"""
pSNP6Genotype        = Proc()
pSNP6Genotype.input  = "celfile:file"
pSNP6Genotype.output = "outfile:file:{{celfile | fn}}.geno.txt"
pSNP6Genotype.lang   = "Rscript"
pSNP6Genotype.script = """
require(oligoClasses)
library(crlmm)

crlmmResult <- crlmm("{{celfile}}", SNRMin=0)
gts = calls(crlmmResult) - 1
#outfile = paste (sep="/", "/data2/junwenwang/panwen/output/TCGA-genotypes/LUAD/gts", paste(basename(args[1]), "gts", sep="."))

write.table(gts, file="{{outfile}}", sep="\\t", row.names=TRUE, quote=FALSE, col.names=FALSE)
"""

"""
@name:
	pGenoToAvInput
@description:
	Convert the genotype called by pSNP6Genotype to [ANNOVAR input file](http://annovar.openbioinformatics.org/en/latest/user-guide/input/#annovar-input-file) using dbSNP identifiers.	
@input:
	`genofile:file`: the genofile generated by pSNP6Genotype, must be sorted by probe names
	`annofile:flie`: the annotation file downloaded from http://www.affymetrix.com/support/technical/annotationfilesmai.affx
		- Could be in .gz format
@output:
	`outfile:file`: the avinput file
@requires:
	[python-read2](https://github.com/pwwang/read2)
"""
pGenoToAvInput = Proc()
pGenoToAvInput.input  = "genofile:file, annofile:file"
pGenoToAvInput.output = "outfile:file:{{genofile | fn}}.avinput"
pGenoToAvInput.script = """
#!/usr/bin/env python
from read2 import read2

fout = open ("{{outfile}}", "w")
def rmatch (line1, line2):
	line2 = [item[1:-1] for item in line2]
	if line1[0].startswith ("#"): return -1
	if line2[0].startswith ("#") or line2[0].startswith("Probe Set ID"): return 1
	tomatch = line2[0]
	if line1[0] < tomatch: return -1
	if line1[0] > tomatch: return 1
	return 0
	
def ract (line1, line2):
	line2 = [item[1:-1] for item in line2]
	snp   = line2[1]
	chr   = line2[2]
	pos   = line2[3]
	allA  = line2[8]
	allB  = line2[9]
	comm  = line1
	comm.pop(0)
	fout.write (" ".join([chr,pos,pos,allA, allB, snp, "|".join(comm)]) + "\\n")

r = read2 ("{{genofile}}", "{{annofile}}")
r.delimit ("\\t", ",")
r.match (rmatch)
r.act (ract)
r.run()

fout.close()
"""