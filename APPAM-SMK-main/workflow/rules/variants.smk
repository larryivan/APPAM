# workflow/rules/variants.smk
import os
rule freebayes:
    conda: "../envs/APPAM-ENV-A.yaml"
    input:
        bam=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam",
        bai=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam.bai",
        ref=f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa"
    output:
        vcf=f"{RESULTS_DIR}/variants/{{sample}}/{{sample}}.raw.vcf"
    params:
        outdir=lambda wc, output: os.path.dirname(output.vcf),
        freq=config["params"]["freebayes_freq"],
        qual=config["params"]["freebayes_qual"]
    log:
        f"{LOGS_DIR}/freebayes/{{sample}}.log"
    threads: 16
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.outdir} $(dirname {log})

        freebayes -f {input.ref} -F {params.freq} -p 1 -q {params.qual} {input.bam} > {output.vcf} 2> {log}
        """

rule bcftools:
    conda: "../envs/APPAM-ENV-A.yaml"
    input:
        vcf=f"{RESULTS_DIR}/variants/{{sample}}/{{sample}}.raw.vcf",
        ref=f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa"
    output:
        filtered_vcf=f"{RESULTS_DIR}/variants/{{sample}}/{{sample}}.filtered.vcf.gz",
        consensus=f"{RESULTS_DIR}/consensus/{{sample}}_consensus.fa.gz"
    params:
        variants_dir=lambda wc, output: os.path.dirname(output.filtered_vcf),
        consensus_dir=lambda wc, output: os.path.dirname(output.consensus),
        qual=config["params"]["bcftools_qual"],
        qual_low=config["params"]["bcftools_qual_low"]
    log:
        f"{LOGS_DIR}/bcftools/{{sample}}.log"
    threads: 16
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.variants_dir} {params.consensus_dir} $(dirname {log})

        bcftools view -v snps,mnps \
            -i 'QUAL >= {params.qual} || (QUAL >= {params.qual_low} && INFO/AO >= 2)' \
            {input.vcf} | bgzip > {output.filtered_vcf} 2> {log}

        bcftools index -t {output.filtered_vcf}

        cat {input.ref} | bcftools consensus {output.filtered_vcf} | bgzip > {output.consensus}
        """
