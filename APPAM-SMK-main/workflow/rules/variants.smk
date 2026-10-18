from pathlib import Path


rule freebayes_variants:
    conda:
        config["tools"]["freebayes_env"]
    input:
        bam=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam",
        bai=f"{RESULTS_DIR}/bowtie2/{{sample}}/{{sample}}.sorted.bam.bai",
        reference=f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa"
    output:
        vcf=f"{RESULTS_DIR}/variants/{{sample}}/{{sample}}.raw.vcf"
    params:
        outdir=lambda wildcards, output: str(Path(output.vcf).parent),
        min_fraction=float(config.get("variants", {}).get("min_alternate_fraction", 0.33)),
        min_base_quality=int(config.get("variants", {}).get("min_base_quality", 20))
    log:
        f"{LOGS_DIR}/variants/freebayes/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/variants/freebayes/{{sample}}.txt"
    threads: 1
    resources:
        mem_mb=16384
    shell:
        r"""
        mkdir -p {params.outdir:q} "$(dirname {log:q})"
        freebayes \
            --fasta-reference {input.reference:q} \
            --min-alternate-fraction {params.min_fraction} \
            --ploidy 1 \
            --min-base-quality {params.min_base_quality} \
            {input.bam:q} \
            > {output.vcf:q} 2> {log:q}
        test -s {output.vcf:q}
        """


rule filter_variants_and_consensus:
    conda:
        config["tools"]["bcftools_env"]
    input:
        vcf=rules.freebayes_variants.output.vcf,
        reference=f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa"
    output:
        filtered_vcf=f"{RESULTS_DIR}/variants/{{sample}}/{{sample}}.filtered.vcf.gz",
        filtered_vcf_index=f"{RESULTS_DIR}/variants/{{sample}}/{{sample}}.filtered.vcf.gz.tbi",
        consensus=f"{RESULTS_DIR}/consensus/{{sample}}.consensus.fa.gz"
    params:
        variants_dir=lambda wildcards, output: str(Path(output.filtered_vcf).parent),
        consensus_dir=lambda wildcards, output: str(Path(output.consensus).parent),
        quality=int(config.get("variants", {}).get("min_variant_quality", 30)),
        rescue_quality=int(config.get("variants", {}).get("rescue_variant_quality", 20)),
        rescue_observations=int(config.get("variants", {}).get("rescue_alternate_observations", 2))
    log:
        f"{LOGS_DIR}/variants/bcftools/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/variants/bcftools/{{sample}}.txt"
    threads: 1
    resources:
        mem_mb=8192
    shell:
        r"""
        mkdir -p {params.variants_dir:q} {params.consensus_dir:q} "$(dirname {log:q})"
        bcftools view \
            --types snps,mnps \
            --include 'QUAL >= {params.quality} || (QUAL >= {params.rescue_quality} && INFO/AO >= {params.rescue_observations})' \
            --output-type z \
            --output {output.filtered_vcf:q} \
            {input.vcf:q} \
            > {log:q} 2>&1
        bcftools index --tbi --output {output.filtered_vcf_index:q} {output.filtered_vcf:q} >> {log:q} 2>&1
        bcftools consensus --fasta-ref {input.reference:q} {output.filtered_vcf:q} \
            2>> {log:q} | bgzip -c > {output.consensus:q}
        test -s {output.filtered_vcf:q}
        test -s {output.consensus:q}
        """
