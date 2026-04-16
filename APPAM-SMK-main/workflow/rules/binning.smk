# workflow/rules/binning.smk
import os
rule metawrap_binning:
    conda: config["tools"]["metawrap_env"]
    input:
        contigs=lambda wc: f"{RESULTS_DIR}/pydamage/{wc.sample}/ancient.contigs.fa"
        if config["params"].get("use_ancient_contigs", False)
        else f"{RESULTS_DIR}/megahit/{wc.sample}/final.contigs.fa",
        se = f"{PREPROCESS_DIR}/{{sample}}.single.fastq"
    output:
        metabat2 = directory(f"{RESULTS_DIR}/metawrap/binning/{{sample}}/metabat2_bins"),
        concoct  = directory(f"{RESULTS_DIR}/metawrap/binning/{{sample}}/concoct_bins"),
        maxbin2  = directory(f"{RESULTS_DIR}/metawrap/binning/{{sample}}/maxbin2_bins")
    params:
        outdir=lambda wc, output: os.path.dirname(output.metabat2),
    log:
        f"{LOGS_DIR}/metawrap_binning/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/metawrap_binning/{{sample}}.txt"
    threads: 48
    shell:
        r"""
        mkdir -p {params.outdir} $(dirname {log})
        metawrap binning -o {params.outdir} -t {threads} \
            --metabat2 --maxbin2 --concoct  \
            -a {input.contigs} \
            --single-end {input.se} &> {log}
        """

rule metawrap_bin_refinement:
    conda: config["tools"]["metawrap_env"]
    input:
        metabat2=f"{RESULTS_DIR}/metawrap/binning/{{sample}}/metabat2_bins",
        maxbin2=f"{RESULTS_DIR}/metawrap/binning/{{sample}}/maxbin2_bins",
        concoct=f"{RESULTS_DIR}/metawrap/binning/{{sample}}/concoct_bins"
    output:
        bins_dir=directory(f"{RESULTS_DIR}/metawrap/bin_refinement/{{sample}}/metawrap_50_10_bins")
    params:
        outdir=lambda wc, output: os.path.dirname(output.bins_dir),
        completeness=config["params"]["bin_completeness"],
        contamination=config["params"]["bin_contamination"],
        checkm_db=config["databases"]["checkm_db"]
    log:
        f"{LOGS_DIR}/metawrap_refinement/{{sample}}.log" 
    benchmark: 
        f"{BENCHMARK_DIR}/metawrap_bin_refinement/{{sample}}.txt"
    threads: 48
    resources:
        mem_mb=128000
    shell:
        r"""
        mkdir -p {params.outdir} $(dirname {log})
        find {input.metabat2} {input.maxbin2} {input.concoct} -name "bin.BinMembers.txt" -delete
        checkm data setRootPath {params.checkm_db}
        metawrap bin_refinement -o {params.outdir} -t {threads} \
            -c {params.completeness} -x {params.contamination} \
            -A {input.metabat2} -B {input.maxbin2} -C {input.concoct} &> {log}
        """

rule checkm:
    conda: "../envs/APPAM-ENV-B.yaml"
    input:
        f"{RESULTS_DIR}/metawrap/bin_refinement/{{sample}}/metawrap_50_10_bins"
    output:
        qa=f"{RESULTS_DIR}/checkm/{{sample}}/bins_qa.txt"
    params:
        outdir=lambda wc, output: os.path.dirname(output.qa)
    log:
        f"{LOGS_DIR}/checkm/{{sample}}.log"
    benchmark: 
        f"{BENCHMARK_DIR}/checkm/{{sample}}.txt"
    threads: 48
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.outdir} $(dirname {log})
        checkm lineage_wf -t {threads} -x fa --tab_table \
            -f {output.qa} {input} {params.outdir} 2> {log}
        """

rule gunc:
    conda: "../envs/APPAM-ENV-A.yaml"
    input:
        f"{RESULTS_DIR}/metawrap/bin_refinement/{{sample}}/metawrap_50_10_bins"
    output:
        result=f"{RESULTS_DIR}/gunc/{{sample}}/GUNC.progenomes_2.1.maxCSS_level.tsv"
    params:
        outdir=lambda wc, output: os.path.dirname(output.result),
        db=config["databases"]["gunc_db"]
    log:
        f"{LOGS_DIR}/gunc/{{sample}}.log"
    threads: 24
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.outdir} $(dirname {log})
        gunc run --input_dir {input} -t {threads} \
            --out_dir {params.outdir} --db_file {params.db} 2> {log}
        """
