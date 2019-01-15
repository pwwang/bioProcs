library(reticulate)
utils     = import('bioprocs')$utils
runcmd    = utils$runcmd
mem2      = utils$mem2
# key orders not kept!
cmdargs   = utils$cmdargs

cbindfill = function (...) {
	dfs = list(...)
	ret = Reduce(function(...) {
		ret = merge(..., by='row.names', all=T, sort = F)
		rownames(ret) = ret[, "Row.names"]
		ret = ret[, -1, drop=F]
		ret
	}, dfs)
	cnames = unlist(lapply(dfs, colnames))
	if (length(cnames) > 0) {
		colnames(ret) = make.unique(cnames)
	}
	return (ret)
}

rbindfill = function (...) {
	library(data.table)
	dfs = lapply(list(...), as.data.frame)
	ret = as.data.frame(rbindlist(dfs, fill = T, use.names = T))
	rnames = unlist(lapply(dfs, rownames))
	if (length(rnames) > 0) {
		rownames(ret) = make.unique(rnames)
	}
	return (ret)
}

logger = function(..., level = 'INFO') {
	cat(paste0(level, ': ', paste(...), '\n'), file = stderr())
}

log2pyppl = function(..., level = 'LOG') {
	msg = paste(...)
	if (!endsWith(msg, "\n")) msg = paste0(msg, "\n")
	cat(paste0('pyppl.log.', level, ': ', msg), file = stderr())
}

# avoid typos
cbind.fill = cbindfill
rbind.fill = rbindfill

read.table.nodup = function(...) {
	args = list(...)
	if (!'row.names' %in% names(args) || is.null(args$row.names)) {
		return(read.table(...))
	} else {
		# 'row.names' removed
		args$row.names = NULL
		# get it back
		args = c(args, list(row.names = NULL))
		mat = do.call(read.table, args)
		rnames = make.unique(as.character(as.vector(mat[,1,drop = T])))
		mat = mat[,-1,drop=F]
		row.names(mat)  = rnames
		return(mat)
	}
}

update.list = function (list1, list2, recursive = F) {
	names2 = names(list2)
	for (name in names2) {
		if (is.list(list1[[name]]) && is.list(list2[[name]]) && recursive) {
			list1[[name]] = update.list(list1[[name]], list2[[name]], recursive = recursive)
		} else {
			list1[[name]] = list2[[name]]
		}
	}
	return (list1)
}

# allow ifelse to return NULL
ifelse = function(condition, true, false) {
	if(condition) return(true)
	return(false)
}

read.table.inopts = function(infile, inopts, nodup = T) {
	opts = names(inopts)
	optrnames = ifelse('rnames' %in% opts, ifelse(inopts$rnames, 1, NULL), 1)
	params = list(
		infile,
		header      = ifelse('cnames' %in% opts, inopts$cnames, T),
		row.names   = ifelse(nodup, NULL, optrnames),
		sep         = ifelse('delimit' %in% opts, inopts$delimit, "\t"),
		check.names = F,
		skip        = ifelse('skip' %in% opts, inopts$skip, 0)
	)
	d = do.call(read.table, params)
	if (nodup && !is.null(optrnames)) {
		rnames = make.unique(as.character(as.vector(d[,1,drop = T])))
		d = d[, -1, drop = F]
		rownames(d) = rnames
	}
	d
}

# format data.frame to output
pretty.numbers = function(df, formats) {
	# remember set stringsAsFactors as FALSE for the dataframe!!
	if (nrow(df) == 0) {
		return(df)
	}
	allCols      = colnames(df)
	formatedCols = c()
	for (fcols in names(formats)) {
		if (fcols == '.') { # must be last element of formats
			cols = which(!allCols %in% formatedCols)
		} else {
			cols = unlist(strsplit(fcols, '..', fixed = T))
			formatedCols = c(formatedCols, cols)
		}
		cols = intersect(cols, allCols)
		df[, cols] = sprintf(formats[[fcols]], as.numeric(unlist(df[, cols])))
	}
	df
}

# format data.frame to output
pretty.numbers2 = function(df, ...) {
	formats = list(...)
	options(stringsAsFactors = FALSE)
	df = as.data.frame(df)
	if (nrow(df) == 0) 
		return(df)

	allCols      = colnames(df)
	if (is.null(allCols))
		allCols = 1:ncol(df)
	formatedCols = c()
	for (fcols in names(formats)) {
		if (fcols == '.') { # must be last element of formats
			if (length(formatedCols) == 0) {
				cols = allCols
			} else {
				cols = which(!allCols %in% formatedCols)
			}
		} else {
			cols = unlist(strsplit(fcols, '..', fixed = T))
			formatedCols = c(formatedCols, cols)
		}
		cols = intersect(cols, allCols)
		df[, cols] = sprintf(formats[[fcols]], as.numeric(unlist(df[, cols])))
	}
	df
}


bQuote = function(s) {
	paste0('`', s, '`')
}
