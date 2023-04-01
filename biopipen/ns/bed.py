"""Tools to handle BED files"""
from ..core.proc import Proc
from ..core.config import config


class BedLiftOver(Proc):
    """Liftover a BED file using liftOver

    Input:
        inbed: The input BED file

    Output:
        outbed: The output BED file

    Envs:
        liftover: The path to liftOver
        chain: The map chain file for liftover

    Requires:
        liftOver:
            - check: {{proc.envs.liftover}} 2>&1 | grep "usage"
    """
    input = "inbed:file"
    output = "outbed:file:{{in.inbed | basename}}"
    envs = {
        "liftover": config.exe.liftover,
        "chain": config.path.liftover_chain,
    }
    lang = config.lang.bash
    script = "file://../scripts/bed/BedLiftOver.sh"


class Bed2Vcf(Proc):
    """Convert a BED file to a valid VCF file with minimal information

    Input:
        inbed: The input BED file

    Output:
        outvcf: The output VCF file

    Envs:
        sample: The sample name to be used in the VCF file
            You can use a lambda function (in string) to generate
            the sample name from the stem of input file
        ref: The reference fasta file, used to grab the reference allele.
            To add contigs in header, the `fai` file is also required at
            `<ref>.fai`
        genome: The genome assembly, added as `source` in header
        base: 0 or 1, whether the coordinates in BED file are 0- or 1-based
        headers: The header lines to be added to the VCF file
        infos: The INFO dicts to be added to the VCF file
        formats: The FORMAT dicts to be added to the VCF file
            The keys 'ID', 'Description', 'Type', and 'Number' are required.
        converters: A dict of converters to be used for each INFO or FORMAT
            The key is the ID of an INFO or FORMAT, and the value is
            Any converts return `None` will skip the record
        nonexisting_contigs: Whether to `keep` or `drop` the non-existing
            contigs in `ref`.
        helpers: Raw code to be executed to provide some helper functions
            since only lambda functions are supported in converters
        index: Sort and index output file

    Requires:
        cyvcf2:
            - check: {{proc.lang}} -c "import cyvcf2"
        pysam:
            - check: {{proc.lang}} -c "import pysam"
        bcftools:
            - if: {{proc.envs.index}}
            - check: {{proc.envs.bcftools}} --version
    """
    input = "inbed:file"
    output = (
        "outvcf:file:{{in.inbed | stem}}.vcf{{'.gz' if envs.index else ''}}"
    )
    lang = config.lang.python
    envs = {
        "bcftools": config.exe.bcftools,
        "sample": "lambda stem: stem",
        "ref": config.ref.reffa,
        "genome": config.ref.genome,
        "nonexisting_contigs": "drop",
        "base": 0,
        "index": True,
        "headers": [],
        "infos": [],
        "formats": [],
        "converters": {},
        "helpers": "",
    }
    script = "file://../scripts/bed/Bed2Vcf.py"


class BedConsensus(Proc):
    """Find consensus regions from multiple BED files.

    Unlike `bedtools merge/cluster`, it does not find the union regions nor
    intersect regions. Instead, it finds the consensus regions using the
    distributions of the scores of the bins

                                         bedtools cluster
    Bedfile A            |----------|    1
    Bedfile B          |--------|        1
    Bedfile C              |------|      1

    BedConsensus         |--------|      with cutoff >= 2
    bedtools intesect      |----|
    bedtools merge     |------------|
    Distribution       |1|2|3333|2|1|    (later normalized into 0~1)

    Input:
        bedfiles: Input BED files

    Output:
        outbed: The output BED file

    Envs:
        bedtools: The path to bedtools
        cutoff: The cutoff to determine the ends of consensus regions
            If `cutoff` < 1, it applies to the normalized scores (0~1), which
            is the percentage of the number of files that cover the region.
            If `cutoff` >= 1, it applies to the number of files that cover the
            region directly.
        chrsize: The chromosome sizes file
        distance: When the distance between two bins is smaller than this value,
            they are merged into one bin using `bedtools merge -d`. `0` means
            no merging.
    """
    input = "bedfiles:files"
    output = (
        "outbed:file:{{in.bedfiles | first | stem | append: '_consensus'}}.bed"
    )
    lang = config.lang.python
    envs = {
        "bedtools": config.exe.bedtools,
        "cutoff": 0.5,
        "distance": 1,
        "chrsize": config.ref.chrsize,
    }
    script = "file://../scripts/bed/BedConsensus.py"
