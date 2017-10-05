import json
import requests
import math
import re
import random
from sys import stderr
from os import path
from hashlib import md5
from mygene import MyGeneInfo
from collections import OrderedDict
genestats  = {}
regstats   = {}
relations  = {}

# read info
with open("{{in.infile}}") as f:
	for line in f:
		line  = line.strip()
		if not line or line.startswith('#'): continue
		parts = line.split("\t")
		if len(parts) >= 5:
			(reg, gene, rstat, gstat, rel) = parts[:5]
			genestats[gene] = gstat
			regstats [reg]  = rstat
			if not reg in relations: relations[reg] = {}
			relations[reg][gene] = rel
		elif len(parts) == 4:
			(reg, gene, gstat, rel) = parts
			genestats[gene] = gstat
			regstats [reg]  = ''
			if not reg in relations: relations[reg] = {}
			relations[reg][gene] = rel
		elif len(parts) == 3:
			(reg, gene, rel) = parts
			genestats[gene] = ''
			regstats [reg]  = ''
			if not reg in relations: relations[reg] = {}
			relations[reg][gene] = rel
		elif len(parts) == 2:
			(reg, gene) = parts
			genestats[gene] = ''
			regstats [reg]  = ''
			if not reg in relations: relations[reg] = {}
			relations[reg][gene] = '+'
		else:
			raise ValueError('Expect more than 2 lines in:\n%s\n' % line)

genes    = sorted(genestats.keys())
genes    = list(set(genes))
scopes   = ['symbol', 'alias']
fields   = ['symbol']
species  = 'human'
uid      = md5(''.join(genes + scopes + fields + [species])).hexdigest()[:8]
igfile   = "{{args.mgcache}}/mygeneinfo.%s" % uid
ogfile   = "{{out.outdir}}/input.genes"
genemap  = {}
genemap2 = {}
if path.isfile(igfile):
	with open(igfile) as f, open(ogfile, 'w') as fout:
		for line in f:
			fout.write(line)
			(query, symbol)  = line.strip().split('\t')
			genemap[query]   = symbol
			genemap2[symbol] = query
else:
	mg       = MyGeneInfo()
	mgret    = mg.getgenes (genes, scopes=scopes, fields=fields, species=species)
	with open (igfile, "w") as fout, open(ogfile, 'w') as fout2:
		for gene in mgret:
			if not 'symbol' in gene: continue
			genemap [gene['query']]  = gene['symbol']
			genemap2[gene['symbol']] = gene['query']
			fout.write("%s\t%s\n" % (gene['query'], gene['symbol']))
			fout2.write("%s\t%s\n" % (gene['query'], gene['symbol']))

if not genemap:
	stderr.write('No genes found.')
	exit(0)

if {{args.enrplot}}:
	import matplotlib
	matplotlib.use('Agg')
	from matplotlib import pyplot as plt
	from matplotlib import gridspec
	from matplotlib import patches

## upload
ENRICHR_URL = 'http://amp.pharm.mssm.edu/Enrichr/addList'
genes_str   = "\n".join(genemap.values())
description = '{{in.infile | fn}}'
payload = {
    'list': (None, genes_str),
    'description': (None, description)
}

response = requests.post(ENRICHR_URL, files=payload)
if not response.ok:
    raise Exception('Error analyzing gene list')

data = json.loads(response.text)

## do enrichment
dbs = "{{args.dbs}}".split(',')
dbs = map (lambda s: s.strip(), dbs)

ENRICHR_URL = 'http://amp.pharm.mssm.edu/Enrichr/enrich'
query_string = '?userListId=%s&backgroundType=%s'

head = ["#Rank", "Term name", "P-value", "Z-score", "Combined score", "Overlapping genes", "Adjusted p-value", "Old p-value", "Old adjusted p-value"]
enrn = {{args.enrn}}
for db in dbs:
	user_list_id = data['userListId']
	gene_set_library = db
	response = requests.get(
		ENRICHR_URL + query_string % (user_list_id, gene_set_library)
	)
	if not response.ok:
		raise Exception('Error fetching enrichment results against %s' % db)
	
	data       = json.loads(response.text)
	data       = data[db]
	d2plot     = []
	outfile    = "{{out.outdir}}/%s.txt" % db
	fout       = open (outfile, "w")
	# for network plot
	path2genes = {}
	path2pvals = {}
	genestats2 = {}
	fout.write ("\t".join(head) + "\n")
	for ret in data[:enrn]:
		fout.write ("\t".join(['|'.join(r) if x == 5 else str(r) for x,r in enumerate(ret)]) + "\n")
		if {{args.rmtags}} and "_" in ret[1]: ret[1] = ret[1].split('_')[0]
		if len(path2genes) < {{args.netn}}:
			path2genes[ret[1]] = ret[5]
			for g in ret[5]: genestats2[g] = genestats[genemap2[g]]
			path2pvals[ret[1]] = ret[2]
		d2plot.append (ret)
	fout.close()

	if {{args.netplot}}:
		# cleanup data
		# map genes back
		#genestats  = {}
		#regstats   = {}
		#relations  = {}
		regstats2   = {}
		relations2  = {}
		for reg, rel in relations.items():
			foundreg = False
			for g, stat in rel.items():
				if not g in genemap: continue
				g = genemap[g]
				if not g in genestats2: continue
				foundreg = True
				if not reg in relations2:
					relations2[reg] = {}
				relations2[reg][g] = stat
			if foundreg: 
				regstats2[reg] = regstats[reg]
		
		genemarks  = {g:0 for g in genestats2.keys()}
		plainlinks = []
		for pathw, genes in path2genes.items():
			newgenes = []
			for g in genes:
				if genemarks[g]:
					newg = g + '__' + str(genemarks[g])
					newgenes.append(g + '__' + str(genemarks[g]))
					plainlinks.append((g, newg))
					genestats2[newg] = ''
				else:
					newgenes.append(g)
				genemarks[g] += 1
			path2genes[pathw] = newgenes

		# prepare dot:
		dotstr = ['digraph G {']
		# regulators
		regupcolors = ['#CCFF99', '#99FF33', '#66CC00', '#336600', '#99CC66', '#669933', '#99FFCC', '#33FF99', '#00CC66', '#006633', '#66CC99', '#339966'] # '+'
		regdncolors = ['#FF99CC', '#FF3399', '#CC0066', '#660033', '#CC6699', '#993366', '#FFCC99', '#FF9933', '#CC6600', '#663300', '#CC9966', '#996633'] # '-'
		regplcolors = ['#3399FF'] # ''
		regcolors   = {} # for edge
		for reg, stat in regstats2.items():
			color = random.choice(regupcolors if stat == '+' else regdncolors if stat == '-' else regplcolors)
			regcolors[reg] = color
			dotstr.append('  "%s" [shape=box fontsize=60 height=2 style=filled fillcolor="%s"]' % (reg, color))
		# genes
		geneupcolor = '#00CC00'
		genedncolor = '#FF3333'
		geneplcolor = '#AAAAAA'
		for gene, stat in genestats2.items():
			# fake gene
			if '__' in gene:
				dotstr.append('  "%s" [shape=circle fontsize=50 width=2 height=2 fixedsize=true label="%s" style=filled color="#333333" fillcolor="#DDDDDD"]' % (gene, gene.split('__')[0]))
			else:
				dotstr.append('  "%s" [shape=circle fontsize=50 width=2 height=2 fixedsize=true style=filled color="#333333" fillcolor="%s"]' % (gene, geneupcolor if stat == '+' else genedncolor if stat == '-' else geneplcolor))
		# regulation links
		for reg, rel in relations2.items():
			for gene, stat in rel.items():
				dotstr.append('  "%s" -> "%s" [arrowsize=2 penwidth=8 arrowhead=%s weight=2 color="%s"]' % (reg, gene, ('tee' if stat == '-' else 'normal'), regcolors[reg]))
		# plain links:
		for g1, g2 in plainlinks:
			dotstr.append('  "%s" -> "%s" [dir=none style=dashed width=1 weight=1]' % (g1, g2))
		# subgraphs
		for pathw, genes in path2genes.items():
			dotstr.append('  subgraph cluster_%s { ' % re.sub(r'[^\w]', '', pathw))
			if path2pvals[pathw] < 0.05:
				dotstr.append('    style = filled;')	
				dotstr.append('    color = "#FFCCCC";')	
			dotstr.append('    fontsize = 60;')
			dotstr.append('    label = "%s (p=%.2E)";' % (pathw, path2pvals[pathw]))
			for g in genes:
				dotstr.append('    "%s";' % g)
			dotstr.append('  }')
		dotstr.append('}')
	
		from graphviz import Source
		dotfile = '{{out.outdir}}/%s.net.dot' % db
		src = Source('\n'.join(dotstr), filename = dotfile, format = 'svg', engine = 'fdp')
		src.render()
	
	if {{args.enrplot}}:
		#d2plot   = sorted (d2plot, cmp=lambda x,y: 0 if x[2] == y[2] else (-1 if x[2] < y[2] else 1))
		plotfile = "{{out.outdir}}/%s.png" % db
		gs = gridspec.GridSpec(1, 2, width_ratios=[3, 7]) 
		rownames = [r[1] if len(r[1])<=40 else r[1][:40] + ' ...' for r in d2plot]
		rnidx    = range (len (rownames))
		ax1 = plt.subplot(gs[0])
		plt.title ("{{args.title}}".replace("{db}", db), fontweight='bold')
		
		ax1.xaxis.grid(alpha=.6, ls = '--', zorder = -99)
		plt.subplots_adjust(wspace=.01, left=0.5)
		ax1.barh(rnidx, [len(r[5]) for r in d2plot], color='blue', alpha=.6)
		plt.yticks (rnidx, rownames)
		ax1.yaxis.set_ticks_position('none')
		ax1.tick_params(axis='x', colors='blue')
		ax1.spines['top'].set_visible(False)
		ax1.spines['left'].set_visible(False)
		ax1.spines['right'].set_visible(False)
		ax1.spines['bottom'].set_linewidth(1)
		ax1.invert_xaxis()
		ax1.invert_yaxis()
		xticks = ax1.xaxis.get_major_ticks()
		xticks[0].label1.set_visible(False)
		
		ax2 = plt.subplot(gs[1])
		ax2.xaxis.grid(alpha=.6, ls = '--', zorder = -99)
		ax2.barh(rnidx, [-math.log(r[2], 10) for r in d2plot], color='red', alpha = .6)
		for i, r in enumerate(d2plot):
			t  = str("%.2E" % r[2])
			tx = 0.1
			ty = i + 0.1
			ax2.text(tx, ty, t, fontsize=8)
		ax2.tick_params(axis='x', colors='red')
		ax2.spines['top'].set_visible(False)
		ax2.spines['left'].set_visible(False)
		ax2.spines['right'].set_visible(False)
		ax2.spines['bottom'].set_linewidth(1)
		ax2.invert_yaxis()
		plt.yticks([])
		ng_patch = patches.Patch(color='blue', alpha=.6, label='# overlapped genes')
		pv_patch = patches.Patch(color='red', alpha = .6, label='-log(p-value)')
		plt.figlegend(handles=[ng_patch, pv_patch], labels=['# overlapped genes', '-log(p-value)'], loc="lower center", ncol=2, edgecolor="none")
		plt.savefig(plotfile, dpi=300)

