"""Plink processes"""

from ..core.proc import Proc
from ..core.config import config


class PlinkSimulation(Proc):
    """Simulate SNPs using PLINK v1.9

    See also <https://www.cog-genomics.org/plink/1.9/input#simulate> and
    <https://pwwang.github.io/biopipen/api/biopipen.ns.snp/#biopipen.ns.snp.PlinkSimulation>

    Input:
        configfile: Configuration file containing the parameters for the simulation.
            The configuration file (in toml, yaml or json format) should contain a
            dictionary of parameters.  The parameters are listed in `envs` except
            `ncores`, which is used for parallelization. You can set parameters
            in `envs` and override them in the configuration file.

    Output:
        outdir: Output directory containing the simulated data
            `plink_sim.bed`, `plink_sim.bim`, and `plink_sim.fam` will be generated.
        gtmat: Genotype matrix file containing the simulated data with rows representing
            SNPs and columns representing samples.

    Envs:
        nsnps (type=int): Number of SNPs to simulate
        ncases (type=int): Number of cases to simulate
        nctrls (type=int): Number of controls to simulate
        plink: Path to PLINK v1.9
        seed (type=int): Random seed. If not set, seed will not be set.
        label: Prefix label for the SNPs.
        prevalence  (type=float): Disease prevalence.
        minfreq (type=float): Minimum allele frequency.
        maxfreq (type=float): Maximum allele frequency.
        hetodds (type=float): Odds ratio for heterozygous genotypes.
        homodds (type=float): Odds ratio for homozygous genotypes.
        missing (type=float): Proportion of missing genotypes.
        args (ns): Additional arguments to pass to PLINK.
            - <more>: see <https://www.cog-genomics.org/plink/1.9/input#simulate>.
        transpose_gtmat (flag): If set, the genotype matrix (`out.gtmat`) will
            be transposed.
        sample_prefix: Use this prefix for the sample names. If not set, the sample
            names will be `per0_per0`, `per1_per1`, `per2_per2`, etc. If set, the
            sample names will be `prefix0`, `prefix1`, `prefix2`, etc.
            This only affects the sample names in the genotype matrix file
            (`out.gtmat`).
    """
    input = "configfile:file"
    output = [
        "outdir:dir:{{in.configfile | stem}}.plink_sim",
        "gtmat:file:{{in.configfile | stem}}.plink_sim/"
        "{{in.configfile | stem}}-gtmat.txt",
    ]
    lang = config.lang.python
    envs = {
        "nsnps": None,
        "ncases": None,
        "nctrls": None,
        "plink": config.exe.plink,
        "seed": None,
        "label": "SNP",
        "prevalence": 0.01,
        "minfreq": 0.0,
        "maxfreq": 1.0,
        "hetodds": 1.0,
        "homodds": 1.0,
        "missing": 0.0,
        "args": {},
        "transpose_gtmat": False,
        "sample_prefix": None,
    }
    script = "file://../scripts/snp/PlinkSimulation.py"


class MatrixEQTL(Proc):
    """Run Matrix eQTL

    See also <https://www.bios.unc.edu/research/genomic_software/Matrix_eQTL/>

    Input:
        geno: Genotype matrix file with rows representing SNPs and columns
            representing samples.
        expr: Expression matrix file with rows representing genes and columns
            representing samples.
        cov: Covariate matrix file with rows representing covariates and columns
            representing samples.

    Output:
        alleqtls: Matrix eQTL output file
        cisqtls: The cis-eQTL file if `snppos` and `genepos` are provided.
            Otherwise it'll be empty.

    Envs:
        model (choice): The model to use.
            - linear: Linear model
            - modelLINEAR: Same as `linear`
            - anova: ANOVA model
            - modelANOVA: Same as `anova`
        pval (type=float): P-value threshold for eQTLs
        transp (type=float): P-value threshold for trans-eQTLs.
            If cis-eQTLs are not enabled (`snppos` and `genepos` are not set),
            this defaults to 1e-5.
            If cis-eQTLs are enabled, this defaults to `None`, which will disable
            trans-eQTL analysis.
        fdr (flag): Do FDR calculation or not (save memory if not).
        snppos: The path of the SNP position file.
            It could be a BED, GFF, VCF or a tab-delimited file with
            `snp`, `chr`, `pos` as the first 3 columns.
        genepos: The path of the gene position file.
            It could be a BED or GFF file.
        dist (type=int): Distance threshold for cis-eQTLs.
        transpose_geno (flag): If set, the genotype matrix (`in.geno`)
            will be transposed.
        transpose_expr (flag): If set, the expression matrix (`in.expr`)
            will be transposed.
        transpose_cov (flag): If set, the covariate matrix (`in.cov`)
            will be transposed.
    """
    input = "geno:file, expr:file, cov:file"
    output = [
        "alleqtls:file:{{in.geno | stem}}.alleqtls.txt",
        "cisqtls:file:{{in.geno | stem}}.cisqtls.txt",
    ]
    lang = config.lang.rscript
    envs = {
        "model": "linear",
        "pval": 1e-3,
        "transp": None,
        "fdr": False,
        "snppos": None,
        "genepos": config.ref.refgene,
        "dist": 250000,
        "transpose_geno": False,
        "transpose_expr": False,
        "transpose_cov": False,
    }
    script = "file://../scripts/snp/MatrixEQTL.R"


class PlinkFromVcf(Proc):
    """Convert VCF to PLINK format.

    The PLINK format consists of 3 files: `.bed`, `.bim`, and `.fam`.

    Requires PLINK v1.9

    "--keep-allele-order" is used to keep the allele order consistent with the
    reference allele first.

    Input:
        invcf: VCF file

    Output:
        outdir: Output directory containing the PLINK files

    Envs:
        plink: Path to PLINK v1.9
        tabix: Path to tabix
        ncores (type=int): Number of cores/threads to use, will pass to plink
            `--threads` option
        vcf_half_call (choice): The current VCF standard does not specify
            how '0/.' and similar GT values should be interpreted.
            - error: error out and reports the line number of the anomaly
            - e: alias for `error`
            - haploid: treat half-calls as haploid/homozygous
            - h: alias for `haploid`
            - missing: treat half-calls as missing
            - m: alias for `missing`
            - reference: treat the missing part as reference
            - r: alias for `reference`
        double_id (flag): set both FIDs and IIDs to the VCF/BCF sample ID.
        vcf_filter (auto): skip variants which failed one or more filters tracked
            by the FILTER field.
            If True, only FILTER with `PASS` or `.` will be kept.
            Multiple filters can be specified by separating them with space or
            as a list.
        vcf_idspace_to: convert all spaces in sample IDs to this character.
        set_missing_var_ids: update variant IDs using a template string,
            with a '@' where the chromosome code should go, and a '#' where the
            base-pair position belongs.
            If `$1`, `$2` ... included, this will run a extra process to set the
            var ids first since plink 1.x doesn't specify `$1` as ref, but
            the first one of all alleles in ASCII-sort order.
            Here `$1` will be bound to reference allele.
            bcftools will be used to set the var ids by replacing `@` with `%CHROM`,
            `#` with `%POS`, and `$1`, `$2`, ... with `%REF`, `%ALT{0}`, ...
            Or you can directly use [bcftools expressions](https://samtools.github.io/bcftools/bcftools.html#query).
        biallelic_only (choice): How to handle multi-allelic sites.
            - true: simply skip all variants where at least two alternate alleles
                are present in the dataset.
            - strict: indiscriminately skip variants with 2+ alternate alleles
                listed even when only one alternate allele actually shows up.
            - list: dump a list of skipped variant IDs to plink.skip.3allele.
        <more>: see <https://www.cog-genomics.org/plink/1.9/> for more options.
            Note that `_` will be replaced by `-` in the argument names.
    """  # noqa: E501
    input = "invcf:file"
    output = "outdir:dir:{{in.invcf | regex_replace: '\\.gz$', '' | stem}}"
    lang = config.lang.python
    envs = {
        "plink": config.exe.plink,
        "tabix": config.exe.tabix,
        "ncores": config.misc.ncores,
        "vcf_half_call": "missing",
        "double_id": True,
        "vcf_filter": True,
        "vcf_idspace_to": "_",
        "set_missing_var_ids": "@_#",
        "biallelic_only": "strict",
    }
    script = "file://../scripts/snp/PlinkFromVcf.py"


class Plink2GTMat(Proc):
    """Convert PLINK files to genotype matrix.

    Requires PLINK v1.9. The .raw/.traw file is generated by plink and then transformed
    to a genotype matrix file.
    See <https://www.cog-genomics.org/plink/1.9/formats#raw> and
    <https://www.cog-genomics.org/plink/1.9/formats#traw> for more information.

    The allelic dosage is used as the values of genotype matrix.
    "--keep-allele-order" is used to keep the allele order consistent with the
    reference allele first.

    Input:
        indir: Input directory containing the PLINK files.
            Including `.bed`, `.bim`, and `.fam` files

    Output:
        outfile: Genotype matrix file with rows representing SNPs and columns
            representing samples if `envs.transpose` is `False`.

    Envs:
        plink: Path to PLINK v1.9
        ncores (type=int): Number of cores/threads to use, will pass to plink
            `--threads` option
        transpose (flag): If set, the genotype matrix (`out.outfile`) is transposed.
        samid: what to use as sample ID.
            Placeholders include `{fid}` and `{iid}` for family and individual IDs,
            respectively.
        varid: what to use as variant ID.
            Placeholders include `{chr}`, `{pos}`, `{rs}`, `{ref}`, and `{alt}` for
            chromosome, position, rsID, reference allele, and alternate allele,
            respectively.
        trans_chr: A dictionary to translate chromosome numbers to chromosome names.
        missing_id: what to use as the rs if missing.
    """
    input = "indir:dir"
    output = "outfile:file:{{in.indir | stem}}-gtmat.txt"
    lang = config.lang.python
    envs = {
        "plink": config.exe.plink,
        "ncores": config.misc.ncores,
        "transpose": False,
        "samid": "{fid}_{iid}",
        "varid": "{chr}_{pos}_{varid}_{ref}_{alt}",
        "trans_chr": {"23": "X", "24": "Y", "25": "XY", "26": "M"},
        "missing_id": "NA",
    }
    script = "file://../scripts/snp/Plink2GTMat.py"


class PlinkIBD(Proc):
    """Run PLINK IBD analysis (identity by descent)

    See also <https://www.cog-genomics.org/plink/1.9/ibd>

    Input:
        indir: Input directory containing the PLINK files.
            Including `.bed`, `.bim`, and `.fam` files

    Output:
        outdir: Output file containing the IBD results.
            Including [`.genome`](https://www.cog-genomics.org/plink/1.9/formats#genome)
            file for the original IBD report from PLINK, and `.ibd.png` for the
            heatmap of `PI_HAT` values.

    Envs:
        plink: Path to PLINK v1.9
        ncores (type=int): Number of cores/threads to use, will pass to plink
            `--threads` option
        highld: High LD regions to be excluded from the analysis.
            If not set, no regions will be excluded.
        samid: what to use as sample ID.
            Placeholders include `{fid}` and `{iid}` for family and individual IDs,
            respectively
        indep (type=auto): LD pruning parameters. Either a list of numerics or a string
            concatenated by `,` to specify
            1) consider a window of N SNPs (e.g. 50),
            2) calculate LD between each pair of SNPs in the window (e.g. 5),
            3) remove one of a pair of SNPs if the LD is greater than X (e.g. 0.2).
        pihat (type=float): PI_HAT threshold for IBD analysis.
            See also <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5007749/>
        plot (flag): If set, plot the heatmap of `PI_HAT` values.
        anno: The annotation file for the samples, used to plot on the heatmap.
            Names must match the ones that are transformed by `args.samid`.
        seed (type=int): Random seed for the analysis.
        devpars (ns): The device parameters for the plot.
            - width (type=int): Width of the plot
            - height (type=int): Height of the plot
            - res (type=int): Resolution of the plot
    """
    input = "indir:dir"
    output = "outdir:dir:{{in.indir | stem}}.ibd"
    lang = config.lang.rscript
    envs = {
        "plink": config.exe.plink,
        "ncores": config.misc.ncores,
        "highld": None,
        "samid": "{fid}_{iid}",
        "indep": [50, 5, 0.2],
        "pihat": 0.1875,
        "plot": True,
        "anno": None,
        "seed": 8525,
        "devpars": {"width": 1000, "height": 1000, "res": 100},
    }
    script = "file://../scripts/snp/PlinkIBD.R"
    plugin_opts = {"report": "file://../reports/snp/PlinkIBD.svelte"}


class PlinkHWE(Proc):
    """Hardy-Weinberg Equilibrium report and filtering

    See also <https://www.cog-genomics.org/plink/1.9/basic_stats#hardy>

    Input:
        indir: Input directory containing the PLINK files.
            Including `.bed`, `.bim`, and `.fam` files

    Output:
        outdir: Output file containing the HWE results.
            Including [`.hwe`](https://www.cog-genomics.org/plink/1.9/formats#hwe)
            file for the original HWE report from PLINK and
            `.hardy.fail` for the variants that failed the HWE test.
            It also includes binary files `.bed`, `.bim`, and `.fam` if `envs.filter`
            is `True`.

    Envs:
        plink: Path to PLINK v1.9
        ncores (type=int): Number of cores/threads to use, will pass to plink
            `--threads` option
        cutoff (type=float): P-value cutoff for HWE test
        filter (flag): If set, filter the variants that failed the HWE test.
        plot (flag): If set, plot the distribution of HWE p-values.
        devpars (ns): The device parameters for the plot.
            - width (type=int): Width of the plot
            - height (type=int): Height of the plot
            - res (type=int): Resolution of the plot
    """
    input = "indir:dir"
    output = "outdir:dir:{{in.indir | stem}}.hwe"
    lang = config.lang.rscript
    envs = {
        "plink": config.exe.plink,
        "ncores": config.misc.ncores,
        "cutoff": 1e-5,
        "filter": False,
        "plot": True,
        "devpars": {"width": 1000, "height": 800, "res": 100},
    }
    script = "file://../scripts/snp/PlinkHWE.R"
    plugin_opts = {"report": "file://../reports/snp/PlinkHWE.svelte"}


class PlinkHet(Proc):
    """Calculation of sample heterozygosity.

    Input:
        indir: Input directory containing the PLINK files.
            Including `.bed`, `.bim`, and `.fam` files

    Output:
        outdir: Output file containing the heterozygosity results.
            Including [`.het`](https://www.cog-genomics.org/plink/1.9/formats#het)
            file for the original heterozygosity report from PLINK and
            `.het.fail` for the samples that failed the heterozygosity test.
            It also includes binary files `.bed`, `.bim`, and `.fam` if `envs.filter`
            is `True`.

    Envs:
        plink: Path to PLINK v1.9
        ncores (type=int): Number of cores/threads to use, will pass to plink
            `--threads` option
        cutoff (type=float): Heterozygosity cutoff, samples with heterozygosity
            beyond `mean - cutoff * sd` or `mean + cutoff * sd` will be considered
            as outliers.
        filter (flag): If set, filter the samples that failed the heterozygosity test.
        plot (flag): If set, plot the distribution of heterozygosity values.
        devpars (ns): The device parameters for the plot.
            - width (type=int): Width of the plot
            - height (type=int): Height of the plot
            - res (type=int): Resolution of the plot
    """
    input = "indir:dir"
    output = "outdir:dir:{{in.indir | stem}}.het"
    lang = config.lang.rscript
    envs = {
        "plink": config.exe.plink,
        "ncores": config.misc.ncores,
        "cutoff": 3.0,
        "filter": False,
        "plot": True,
        "devpars": {"width": 1000, "height": 800, "res": 100},
    }
    script = "file://../scripts/snp/PlinkHet.R"
    plugin_opts = {"report": "file://../reports/snp/PlinkHet.svelte"}


class PlinkCallRate(Proc):
    """Calculation of call rate for the samples and variants.

    Input:
        indir: Input directory containing the PLINK files.
            Including `.bed`, `.bim`, and `.fam` files

    Output:
        outdir: Output file containing the call rate results.
            Including [`.imiss`](https://www.cog-genomics.org/plink/1.9/formats#imiss)
            file for missing calls for samples,
            [`.lmiss`](https://www.cog-genomics.org/plink/1.9/formats#lmiss) for
            missing calls for variants, `.samplecr.fail` for the samples fail
            sample call rate cutoff (`args.samplecr`), and `.varcr.fail` for the SNPs
            fail snp call rate cutoff (`args.varcr`).
            It also includes binary files `.bed`, `.bim`, and `.fam`.

    Envs:
        plink: Path to PLINK v1.9
        ncores (type=int): Number of cores/threads to use, will pass to plink
            `--threads` option
        samplecr (type=float): Sample call rate cutoff
        varcr (type=float): Variant call rate cutoff
        max_iter (type=int): Maximum number of iterations to run the call rate
            calculation.
            Since the sample and variant call rates are affected by each other,
            it may be necessary to iterate the calculation to get the stable results.
        plot (flag): If set, plot the distribution of call rates.
        devpars (ns): The device parameters for the plot.
            - width (type=int): Width of the plot
            - height (type=int): Height of the plot
            - res (type=int): Resolution of the plot
    """
    input = "indir:dir"
    output = "outdir:dir:{{in.indir | stem}}.callrate"
    lang = config.lang.rscript
    envs = {
        "plink": config.exe.plink,
        "ncores": config.misc.ncores,
        "samplecr": 0.95,
        "varcr": 0.95,
        "max_iter": 3,
        "plot": True,
        "devpars": {"width": 1000, "height": 800, "res": 100},
    }
    script = "file://../scripts/snp/PlinkCallRate.R"
    plugin_opts = {"report": "file://../reports/snp/PlinkCallRate.svelte"}


class PlinkFilter(Proc):
    """Filter samples and variants for PLINK files.

    Input:
        indir: Input directory containing the PLINK files.
            Including `.bed`, `.bim`, and `.fam` files
        samples_file_keep: File containing the sample IDs to keep.
        variants_file_keep: File containing the variant IDs to keep.
        samples_file_remove: File containing the sample IDs to remove.
        variants_file_remove: File containing the variant IDs to remove.

    Output:
        outdir: Output directory containing the filtered PLINK files.
            Including `.bed`, `.bim`, and `.fam` files

    Envs:
        plink: Path to PLINK v1.9
        ncores (type=int): Number of cores/threads to use, will pass to plink
            `--threads` option
        samples_keep (auto): Sample IDs to keep.
            A list of sample IDs or string concatenated by `,`.
            If either `in.samples_file_keep` or `envs.samples_file_keep` is set,
            this will be ignored.
        variants_keep (auto): Variant IDs to keep.
            A list of variant IDs or string concatenated by `,`.
            If either `in.variants_file` or `envs.variants_file` is set,
            this will be ignored.
        samples_remove (auto): Sample IDs to remove.
            A list of sample IDs or string concatenated by `,`.
            If either `in.samples_file_remove` or `envs.samples_file_remove` is set,
            this will be ignored.
        variants_remove (auto): Variant IDs to remove.
            A list of variant IDs or string concatenated by `,`.
            If either `in.variants_file_remove` or `envs.variants_file_remove` is set,
            this will be ignored.
        samples_file_keep: File containing the sample IDs to keep.
            If `in.samples_file_keep` is set, this will be ignored.
        variants_file_keep: File containing the variant IDs to keep.
            If `in.variants_file_keep` is set, this will be ignored.
        samples_file_remove: File containing the sample IDs to remove.
            If `in.samples_file_remove` is set, this will be ignored.
        variants_file_remove: File containing the variant IDs to remove.
            If `in.variants_file_remove` is set, this will be ignored.
        chr: Chromosome to keep.
            For example, `1-4 22 XY` will keep chromosomes 1 to 4, 22, and XY.
        not_chr: Chromosome to remove.
            For example, `1-4 22 XY` will remove chromosomes 1 to 4, 22, and XY.
        autosome (flag): Excludes all unplaced and non-autosomal variants
        autosome_xy (flag): Does `autosome` but does not exclude the pseudo-autosomal
            region of X.
        snps_only (auto): Excludes all variants with one or more multi-character
            allele codes. With 'just-acgt', variants with single-character allele codes
            outside of {'A', 'C', 'G', 'T', 'a', 'c', 'g', 't', <missing code>}
            are also excluded.
    """
    input = [
        "indir:dir",
        "samples_file_keep:file",
        "variants_file_keep:file",
        "samples_file_remove:file",
        "variants_file_remove:file",
    ]
    output = "outdir:dir:{{in.indir | stem}}.filtered"
    lang = config.lang.python
    envs = {
        "plink": config.exe.plink,
        "ncores": config.misc.ncores,
        "samples_keep": None,
        "variants_keep": None,
        "samples_remove": None,
        "variants_remove": None,
        "samples_file_keep": None,
        "variants_file_keep": None,
        "samples_file_remove": None,
        "variants_file_remove": None,
        "chr": None,
        "not_chr": None,
        "autosome": False,
        "autosome_xy": False,
        "snps_only": False,
    }
    script = "file://../scripts/snp/PlinkFilter.py"


class PlinkFreq(Proc):
    """Calculate allele frequencies for the variants.

    Input:
        indir: Input directory containing the PLINK files.
            Including `.bed`, `.bim`, and `.fam` files

    Output:
        outdir: Output file containing the allele frequency results.
            By default, it includes
            [`.frq`](https://www.cog-genomics.org/plink/1.9/formats#frq)
            file for the allele frequency report from PLINK.
            Modifiers can be added to change this behavior.
            See `envs.modifier` for more information.
            When `envs.filter != no`, it also includes binary files `.bed`, `.bim`,
            and `.fam` after filtering with `envs.cutoff`.

    Envs:
        plink: Path to PLINK v1.9
        ncores (type=int): Number of cores/threads to use, will pass to plink
            `--threads` option
        modifier (choice): The modifier of `--freq` to control the output behavior.
            - none: No modifier, only the `.frq` file will be generated.
            - counts: write allele count report to `.frq.count`.
            - case-control: write case-control association report to `.frq.cc`.
            - cc: Alias for `case-control`.
            - x: write genotype count report to `.frqx`
        gz (flag): If set, compress the output files.
        cutoff (auto): Cutoffs to mark or filter the variants.
            If a float is given, default column will be used based on the modifier.
            For `modifier="none"`, it defaults to `MAF`.
            For `modifier="counts"`, it defaults to `C1`.
            For `modifier="case-control"`, it defaults to `MAF_A`.
            For `modifier="cc"`, it defaults to `MAF_A`.
            For `modifier="x"`, it defaults to `C(HOM A1)`.
            Or this could be a dictionary to specify the column names and cutoffs.
            For example, `{"MAF": 0.05}`.
        filter (auto): The direction of filtering variants based on `cutoff`.
            If a single value is given, it will apply to all columns provided in
            `cutoff`. If a dictionary is given, it will apply to the corresponding
            column. If a column cannot be found in the dictionary, it defaults to
            `no`.
            no: Do not filter variants (no binary files are generated in outdir).
            gt: Filter variants with MAF greater than `cutoff`.
            lt: Filter variants with MAF less than `cutoff`.
            ge: Filter variants with MAF greater than or equal to `cutoff`.
            le: Filter variants with MAF less than or equal to `cutoff`.
        plot (flag): If set, plot the distribution of allele frequencies.
        devpars (ns): The device parameters for the plot.
            - width (type=int): Width of the plot
            - height (type=int): Height of the plot
            - res (type=int): Resolution of the plot
    """
    input = "indir:dir"
    output = "outdir:dir:{{in.indir | stem}}.freq"
    lang = config.lang.rscript
    envs = {
        "plink": config.exe.plink,
        "ncores": config.misc.ncores,
        "modifier": "none",
        "gz": False,
        "cutoff": {},
        "filter": {},
        "plot": True,
        "devpars": {"width": 1000, "height": 800, "res": 100},
    }
    script = "file://../scripts/snp/PlinkFreq.R"
    plugin_opts = {"report": "file://../reports/snp/PlinkFreq.svelte"}
