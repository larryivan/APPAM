import os


rule megahit:
    conda: config["tools"]["assembly_env"]
    input:
        r1=f"{PREPROCESS_DIR}/{{sample}}.paired_R1.fastq.gz",
        r2=f"{PREPROCESS_DIR}/{{sample}}.paired_R2.fastq.gz",
        se=f"{PREPROCESS_DIR}/{{sample}}.single.fastq.gz"
    output:
        contigs=f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa",
        done=f"{RESULTS_DIR}/megahit/{{sample}}/done"
    params:
        outdir=lambda wc, output: os.path.dirname(output.contigs),
        min_contig_len=config["params"]["min_contig_len"]
    log:
        f"{LOGS_DIR}/megahit/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/megahit/{{sample}}.txt"
    threads: 48
    resources:
        mem_mb=64000
    script:
        "../scripts/run_megahit.py"
