from pyppl import proc

"""
@name:
	pExpFiles2Mat
@description:
	Convert expression files to expression matrix
	File names will be used as sample names (colnames)
@input:
	`expdir:file`:  the directory containing the expression files, could be gzipped
@output:
	`expfile:file`: the expression matrix
"""
pExpFiles2Mat = proc()
pExpFiles2Mat.input    = "expdir:file"
pExpFiles2Mat.output   = "expfile:file:{{expdir.fn}}.exp.mat"
pExpFiles2Mat.lang     = "Rscript"
pExpFiles2Mat.args     = {"header": False}
pExpFiles2Mat.script   = """
setwd("{{expdir}}")
cbind.fill = function (x1, x2) {
	y = merge(x1, x2, by='row.names', all=T, sort=F)
	rownames(y) = y[, "Row.names"]
	y = y[, -1, drop=F]
	cnames      = c(colnames(x1), colnames(x2))
	if (!is.null(cnames)) {
		colnames(y) = cnames
	}
	return (y)
}
exp = c()
for (efile in list.files()) {
	sample = tools::file_path_sans_ext(basename(efile))
	if (grepl ('.gz$', efile)) efile = gzip (efile)
	tmp    = read.table (efile, sep="\\t", header=F, row.names = 1, check.names=F)
	colnames (tmp) = tools::file_path_sans_ext(basename(efile))
	exp    = cbind.fill (exp, tmp)
}

write.table (exp, "{{expfile}}", col.names=T, row.names=T, sep="\\t", quote=F)
"""

"""
@name:
	pDEGByEdgeR
@description:
	Call DEG from expression matrix
@input:
	`expfile:file`: the expression matrix
	`group1`:       columns of group1 (separated by comma)
	`group2`:       columns of group2 (separated by comma)
	`group1name`:   the name of group1
	`group2name`:   the name of group2   
@output:
	`degdir:dir`:   the output directory containing DEGs and plots
@args:
	`filter`:  the pair (X,Y) on how to filter the data by cpm (`d <- d[rowSums(cpm(d)>X) >= Y,]`). Default: "1,2"
		- keep genes with at least X counts per million (CPM) in at least Y samples
	`pval`:    the cutoff of DEGs (default: .05)
	`paired`:  whether the samples are paired, default: False
	`bcvplot`: whether to plot biological coefficient of variation, default: True
	`displot`: whether to plot biological coefficient of variation, default: True
	`fcplot`:  whether to plot fold changes, default: True
@requires:
	[edgeR](https://bioconductor.org/packages/release/bioc/html/edger.html)
"""
pDEGByEdgeR = proc ()
pDEGByEdgeR.input     = "expfile:file, group1, group2, group1name, group2name"
pDEGByEdgeR.output    = "degdir:dir:{{expfile.fn}}.{{group1name}}-{{group2name}}.deg"
pDEGByEdgeR.args      = {'filter': "1,2", 'pval': 0.05, 'paired': False, 'bcvplot': True, 'displot': True, 'fcplot': True}
pDEGByEdgeR.defaultSh = "Rscript"
pDEGByEdgeR.script    = """
library('edgeR')
group1  = unlist(strsplit("{{group1}}", ","))
group2  = unlist(strsplit("{{group2}}", ","))

expmatrix = read.table ("{{expfile}}",  header=T, row.names = 1, check.names=F, sep="\\t")
g1names   = match (group1, colnames(expmatrix))
g2names   = match (group2, colnames(expmatrix))
expmatrix = expmatrix [, c(g1names, g2names)]
pairs = vector(mode="numeric")
group = vector(mode="character")
ng1   = length(g1names)
ng2   = length(g2names)
if ({{proc.args.paired | str(_).upper()}}) {
	for (i in 1:ng1) {
		pairs = c(pairs, i, i)
		group = c(group, "{{group1name}}", "{{group2name}}")
	}
	pairs  = factor(pairs)
	group  = factor(group)
	design = model.matrix(~pairs+group)
} else {
	group  = c(rep("{{group1name}}", ng1), rep("{{group2name}}", ng2))
	group  = factor(group)
	design = model.matrix(~group)
}

# filter
dobj   = DGEList(counts=expmatrix, group=group)
filter = noquote(unlist(strsplit("{{proc.args.filter}}", ",")))
fX     = as.numeric (filter[1])
fY     = as.numeric (filter[2])
dobj   = dobj[rowSums(cpm(dobj)>fX) >= fY, ]
dobj$samples$lib.size = colSums(dobj$counts)

# normalize
dobj = calcNormFactors(dobj, method="TMM")

if ({{proc.args.bcvplot | str(_).upper()}}) {
	bcvplot = file.path ("{{degdir}}", "bcvplot.png")
	png (file=bcvplot)
	plotMDS (dobj, method="bcv", col=as.numeric(dobj$samples$group))
	legend("bottomleft", as.character(unique(dobj$samples$group)), col=2:1, pch=20)
	dev.off()
}

disp <- estimateDisp (dobj, design)
if ({{proc.args.displot | str(_).upper()}}) {
	displot = file.path ("{{degdir}}", "displot.png")
	png (file=displot)
	plotBCV (disp)
	dev.off()
}

fit    = glmFit (disp, design)
fit    = glmLRT (fit)

if ({{proc.args.fcplot | str(_).upper()}}) {
	deg    = decideTestsDGE(fit, p.value = {{proc.args.pval}})
	fcplot = file.path ("{{degdir}}", "fcplot.png")
	png (file=fcplot)
	tags = rownames(disp)[as.logical(deg)]
	plotSmear (fit, de.tags=tags)
	abline(h = c(-2, 2), col = "blue")
	dev.off()
}

out    = topTags (fit, n=nrow(fit$table), p.value = {{proc.args.pval}})
write.table (out$table, file.path("{{degdir}}", "degs.txt"), quote=F, sep="\\t")
"""

"""
@name:
	pMArrayLimma
@description:
	Call degs of microarray data by limma
@input:
	`expfile:file`: The expression matrix
	`group1`:      The 1st group
	`group2`:      The 2nd group
	`group1name`:  The name of 1st group
	`group2name`:  The name of 2nd group
@output:
	`degdir:dir`:   the output directory containing DEGs and plots
@args:
	`norm`:    the normalization methods, separated by comma. Support normalization methods: `quan` (quantile). Default: "quan"
	`boxplot`: draw boxplot? Default: True
	`paired`:  whether the samples are paired, default: False
	`filter`:  the pair (X,Y) on how to filter the data by expression (`d <- d[rowSums(d>X) >= Y,]`). Default: "1,2"
		- keep genes with at least X exp in at least Y samples
	`pval`:    the pvalue cutoff of DEGs (default: .05)
	`qval`:    the qvalue cutoff of DEGs (default: .05)
	`heatmap`: whether to plot heatmap, default: True
	`hmn`:     Number of gene used for heatmap, default: 50
	`hmmar`:   Margins for heatmap, default: "10,7"
	`volplot`: whether to plot the volcano plot, default: True
@requires:
	[limma](https://bioconductor.org/packages/release/bioc/html/limma.html)
	[ggplot2](https://bioconductor.org/packages/release/bioc/html/ggplot2.html)
"""
pMArrayLimma = proc()
pMArrayLimma.input  = "expfile:file, group1, group2, group1name, group2name"
pMArrayLimma.output = "degdir:dir:{{expfile.fn}}.{{group1name}}-{{group2name}}.deg"
pMArrayLimma.args   = {'norm': "quan", 'boxplot': True, 'paired': False, "filter": "1,2", "qval": .05, "pval": .05, "heatmap": True, "hmn": 50, "volplot": True, "hmmar": "10,7"}
pMArrayLimma.lang   = "Rscript"
pMArrayLimma.script = """
library(limma)
library(ggplot2)
group1  = unlist(strsplit("{{group1}}", ","))
group2  = unlist(strsplit("{{group2}}", ","))

expmatrix = read.table ("{{expfile}}",  header=T, row.names = 1, check.names=F, sep="\\t")
g1names   = match (group1, colnames(expmatrix))
g2names   = match (group2, colnames(expmatrix))
expmatrix = expmatrix [, c(g1names, g2names)]

# filter
filter     = noquote(unlist(strsplit("{{proc.args.filter}}", ",")))
fX         = as.numeric (filter[1])
fY         = as.numeric (filter[2])
expmatrix  = expmatrix[rowSums(expmatrix>fX) >= fY, ]

if ("quan" %in% unlist(strsplit("{{proc.args.norm}}", ","))) {
	expmatrix = normalizeBetweenArrays (expmatrix)
}

if ({{proc.args.boxplot | str(_).upper()}}) {
	png (file = file.path("{{degdir}}", "boxplot.png"), res=300, width=2000, height=2000)
	boxplot (expmatrix, las=2)
	dev.off()	
}

pairs = vector(mode="numeric")
group = vector(mode="character")
ng1   = length(g1names)
ng2   = length(g2names)
if ({{proc.args.paired | str(_).upper()}}) {
	for (i in 1:ng1) {
		pairs = c(pairs, i, i)
		group = c(group, "{{group1name}}", "{{group2name}}")
	}
	pairs  = factor(pairs)
	group  = factor(group)
	design = model.matrix(~pairs+group)
} else {
	group  = c(rep("{{group1name}}", ng1), rep("{{group2name}}", ng2))
	group  = factor(group)
	design = model.matrix(~group)
}

fit    = lmFit (expmatrix, design)
fit    = eBayes(fit)
out    = topTable (fit, number = nrow(expmatrix), sort.by="p")
out    = out[out$adj.P.Val<{{proc.args.qval}} & out$P.Value<{{proc.args.pval}},]

degfile = file.path("{{degdir}}", "degs.txt")
write.table (out, degfile, quote=F, sep="\\t")

if ({{proc.args.heatmap | str(_).upper()}}) {
	hmn  = min (nrow(out), {{proc.args.hmn}})
	exps = expmatrix[row.names(out[1:hmn, ]), ]
	hmfile = file.path("{{degdir}}", "heatmap.png")
	png (file = hmfile, res=300, width=2000, height=2000)
	heatmap(as.matrix(exps), margins = c({{proc.args.hmmar}}))
	dev.off()
}

if ({{proc.args.volplot | str(_).upper()}}) {
	dat = data.frame(out, n_log10_adj_pval = -c(log10(out$adj.P.Val)), col=ifelse(abs(out$logFC)>2 & out$adj.P.Val<0.01, 'A', ifelse(abs(out$logFC)>2, 'B', 'C')))
	a<-ggplot(dat, aes(x = logFC, y = n_log10_adj_pval, col=col))
	a<-a+ylab("-log10(adjusted P value)\n")
	a<-a+xlab("logFC")
	a<-a+theme_classic(base_size = 12)
	a<-a+theme(legend.position="none")
	a<-a+geom_point()
	a<-a+geom_vline(xintercept=c(2, -2))
	a<-a+geom_hline(yintercept = -log10(0.01))
	volfile = file.path("{{degdir}}", "volcano.png")
	png (file = volfile, res=300, width=2000, height=2000)
	plot(a)
	dev.off()
}
"""

"""
@name:
	pRawCounts2
@description:
	Convert raw counts to another unit
@input:
	`expfile:file`: the expression matrix
	- rows are genes, columns are samples, if not use `args.transpose = True`
@output:
	`outfile:file`: the converted expression matrix
@args:
	`transpose`: transpose the input matrix? default: False
	`log2`:      whether to take log2? default: False
	`unit`:      convert to which unit? default: cpm (or rpkm, tmm)
	`header`:    whether input file has header? default: True
	`rownames`:  the index of the column as rownames. default: 1
	`glenfile`:  the gene length file, for RPKM
	- no head, row names are genes, have to be exact the same order and length as the rownames of expfile
@requires:
	[edgeR](https://bioconductor.org/packages/release/bioc/html/edger.html) if cpm or rpkm is chosen
	[coseq](https://rdrr.io/rforge/coseq/man/transform_RNAseq.html) if tmm is chosen
"""
pRawCounts2 = proc ()
pRawCounts2.input     = "expfile:file"
pRawCounts2.output    = "outfile:file:{{expfile.fn}}.{{proc.args.unit}}.txt"
pRawCounts2.args      = {'transpose': False, 'unit': 'cpm', 'header': True, 'rownames': 1, 'log2': False, 'glenfile': ''}
pRawCounts2.defaultSh = "Rscript"
pRawCounts2.script    = """
data  = read.table ("{{expfile}}", sep="\\t", header={{proc.args.header | str(_).upper()}}, row.names = {{proc.args.rownames}}, check.names=F)
if ({{proc.args.transpose | str(_).upper()}}) data = t (data)

if ("{{proc.args.unit}}" == 'cpm') {
	library('edgeR')
	ret = cpm (data, log = {{proc.args.log2 | str(_).upper()}})
} else if ("{{proc.args.unit}}" == 'rpkm') {
	library('edgeR')
	genelen = read.table ("{{proc.args.glenfile}}", header=F, row.names = 1, check.names = F)
	ret = rpkm (data, log = {{proc.args.log2 | str(_).upper()}}, gene.length = as.vector(genelen))
} else {
	library('coseq')
	ret = transform_RNAseq(data, norm="TMM")
	ret = ret$normCounts
	if ({{proc.args.log2 | str(_).upper()}})
		ret = log2(ret)
}

rnames = TRUE
cnames = TRUE
if ({{proc.args.transpose | str(_).upper()}}) {
	rnames = {{proc.args.header | str(_).upper()}}
	cnames = {{proc.args.rownames}} == 1
} else {
	rnames = {{proc.args.rownames}} == 1
	cnames = {{proc.args.header | str(_).upper()}}
}

write.table (ret, "{{outfile}}", quote=F, row.names=rnames, col.names=cnames, sep="\\t")
"""