import cmdy
from pathlib import Path

DESTDIR = Path(__file__).parent / "reference"
REFFA_URL = (
    "http://hgdownload.cse.ucsc.edu/"
    "goldenpath/%(genome)s/bigZips/%(genome)s.fa.gz"
)
CHROMS = [
    "chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8", "chr9",
    "chr10", "chr11", "chr12", "chr13", "chr14", "chr15", "chr16", "chr17",
    "chr18", "chr19", "chr20", "chr21", "chr22", "chrX", "chrY", "chrM",
]


def download_reffa(genome):
    """Download genome reference sequences"""
    outdir = DESTDIR / genome
    outdir.mkdir(exist_ok=True, parents=True)
    url = REFFA_URL % {"genome": genome}
    outfile = outdir / "allchrs.fa.gz"
    reffa = outdir / "chrs.fa"
    cmdy.aria2c(a=2, x=2, o=outfile, _=url)
    cmdy.seqkit.grep(p=CHROMS, _=outfile, _dupkey=True).r() > reffa
    cmdy.samtools.faidx(reffa)

if __name__ == "__main__":
    download_reffa("hg19")
    download_reffa("hg38")
