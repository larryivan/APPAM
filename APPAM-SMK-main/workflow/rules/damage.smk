# workflow/rules/damage.smk
import os
rule bowtie2_index:
    conda: config["tools"]["mapping_env"]
    input:
        contigs=f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa"
    output:
        index_1=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}_index.1.bt2",
        index_2=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}_index.2.bt2",
        index_3=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}_index.3.bt2",
        index_4=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}_index.4.bt2",
        index_rev1=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}_index.rev.1.bt2",
        index_rev2=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}_index.rev.2.bt2"
    params:
        outdir=lambda wc, output: os.path.dirname(output.index_1),
        index_prefix=lambda wc, output: output.index_1.replace(".1.bt2", "")
    log:
        f"{LOGS_DIR}/bowtie2_index/{{sample}}.log"
    benchmark: 
        f"{BENCHMARK_DIR}/bowtie2_index/{{sample}}.txt"
    threads: 24
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.outdir:q} "$(dirname {log:q})"
        bowtie2-build --threads {threads} \
            {input.contigs:q} \
            {params.index_prefix:q} \
            2> {log:q}
        """

rule bowtie2_align:
    conda: config["tools"]["mapping_env"]
    input:
        r1      = f"{PREPROCESS_DIR}/{{sample}}.paired_R1.fastq.gz",
        r2      = f"{PREPROCESS_DIR}/{{sample}}.paired_R2.fastq.gz",
        se      = f"{PREPROCESS_DIR}/{{sample}}.single.fastq.gz",
        contigs = f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa",
        index   = f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}_index.1.bt2"
    output:
        bam = f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam"
    params:
        index_prefix=lambda wc, input: input.index.replace(".1.bt2", "")
    threads: 24
    resources:
        mem_mb=64000
    log:
        f"{LOGS_DIR}/bowtie2/{{sample}}_align.log"
    benchmark:
        f"{BENCHMARK_DIR}/bowtie2_align/{{sample}}.txt"
    script:
        "../scripts/run_bowtie2_align.py"


rule index_bam:
    conda: config["tools"]["mapping_env"]
    input:
        f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam"
    output:
        f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam.bai"
    threads: 24
    resources:
        mem_mb=64000
    log:
        f"{LOGS_DIR}/bowtie2/{{sample}}_index_bam.log"
    benchmark: 
        f"{BENCHMARK_DIR}/bowtie2_index_bam/{{sample}}.txt"
    shell:
        r"""
        mkdir -p "$(dirname {log:q})"
        samtools index -@ {threads} {input:q} 2> {log:q}
        """

rule pydamage:
    conda: config["tools"]["pydamage_env"]
    input:
        bam=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam",
        bai=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam.bai"
    output:
        result=f"{RESULTS_DIR}/pydamage/{{sample}}/pydamage_results.csv"
    params:
        outdir=lambda wc, output: os.path.dirname(output.result),
        window=config["params"]["pydamage_window"]
    log:
        f"{LOGS_DIR}/pydamage/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/pydamage/{{sample}}.txt"
    threads: 24
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.outdir:q}
        mkdir -p "$(dirname {log:q})"
        pydamage -o {params.outdir:q} analyze -w {params.window} -p {threads} --force {input.bam:q} 2> {log:q}
        """
