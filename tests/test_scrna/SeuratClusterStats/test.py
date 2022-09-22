from pipen import Proc
from biopipen.core.config import config
from biopipen.ns.scrna import SeuratClustering, SeuratClusterStats
from biopipen.core.testing import get_pipeline


class PrepareSeurat(Proc):
    """Prepare the data

    Requires:
        - name: Seurat
          check: |
            {{proc.lang}} <(echo "library(Seurat)")
    """

    input = "name"
    input_data = ["pbmc_small"]
    output = "outfile:file:{{in.name}}.RDS"
    lang = config.lang.rscript
    script = """
        library(Seurat)
        pbmc_small$Sample = pbmc_small$letter.idents
        saveRDS(pbmc_small, {{out.outfile | quote}})
    """


class SeuratClustering(SeuratClustering):
    requires = PrepareSeurat


class SeuratClusterStats(SeuratClusterStats):
    requires = SeuratClustering
    envs = {
        "exprs": {
            "ridgeplots.1": {
                "title": "Gene expressions in g1",
                "subset": "groups == 'g1'",
            },
            "ridgeplots.2": {
                "title": "Gene expressions in g2",
                "subset": "groups == 'g2'",
            },
            "vlnplots": {"boxplot": {}, "pt.size": 0},
            "dotplot": {"plus": "RotatedAxis()"},
            "heatmap": {"downsample": "average"},
        }
    }


def pipeline():
    return get_pipeline(__file__, plugins=["no:report"]).set_starts(
        PrepareSeurat
    )


def testing(pipen):
    outfile = (
        pipen.procs[-1].workdir.joinpath(
            "0",
            "output",
            "pbmc_small.cluster_stats",
        )
    )
    assert outfile.is_dir()


if __name__ == "__main__":
    pipen = pipeline()
    pipen.run()
    testing(pipen)
