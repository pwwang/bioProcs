"""Tools to analyze single-cell RNA"""

from ..core.proc import Proc
from ..core.config import config

class SeuratLoading(Proc):
    """Seurat - Loading data

    Input:
        metafile: The metadata of the samples
            A tab-delimited file
            Two columns are required:
            - `Sample` to specify the sample names.
            - `RNADir` to assign the path of the data to the samples
              The path will be read by `Read10X()` from `Seurat`

    Output:
        rdsfile: The RDS file with a list of Seurat object
    """
    input = "metafile:file"
    output = "rdsfile:file:{{in.metafile | stem}}.seurat.RDS"
    lang = config.lang.rscript
    script = "file://../scripts/scrna/SeuratLoading.R"

class GeneExpressionInvistigation(Proc):
    """Investigation of expressions of genes of interest

    Input:
        srtobj: The seurat object loaded by SeuratLoading
        genefile: The genes to show their expressions
            Two columns without header. First the gene symbol, then the
            name you want to show in the plot
        groupfile: The group of cells with rownames the groups and
            columns the cells in each sample.

    Output:
        outdir: The output directory with the plots

    Envs:
        cases: The cases
            A dict with keys as the case name and the values as configs:
            - `condition`: The condition to select groups from the count matrix
                (the cells in the groupfile are converted into cell counts)
            - `target`: Which sample to pull expression from
                could be multiple
            - `ncol`: Split the plot to how many columns?
            - `slug`: The file name slug of the plot.
                It may also determine the order of the plots to show in reports
            - `devops`: The options for R plotting devides
                (res, height and width)
    """
    input = "srtobj:file, genefile:file, groupfile:file"
    output = "outdir:dir:{{in.groupfile | stem0}}.exprs"
    lang = config.lang.rscript
    envs = { "cases": {} }
    order = 4
    script = "file://../scripts/scrna/GeneExpressionInvistigation.R"
    plugin_opts = {
        "report": "file://../reports/scrna/GeneExpressionInvistigation.svelte"
    }
