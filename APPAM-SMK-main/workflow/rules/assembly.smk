# workflow/rules/assembly.smk
import os
rule megahit:
    conda: "../envs/APPAM-ENV-A.yaml"
    input:
        se = f"{PREPROCESS_DIR}/{{sample}}.single.fastq"
    output:
        contigs = f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa",
        done    = f"{RESULTS_DIR}/megahit/{{sample}}/done"
    params:
        outdir=lambda wc, output: os.path.dirname(output.contigs),
        min_contig_len = config["params"]["min_contig_len"]
    log:
        f"{LOGS_DIR}/megahit/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/megahit/{{sample}}.txt"
    threads: 48
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p $(dirname {log})
        rm -rf {params.outdir}

        megahit \
            -r {input.se} \
            -o {params.outdir} \
            --min-contig-len {params.min_contig_len} \
            -t {threads} 2> {log}

        touch {output.done}
        rm -rf {params.outdir}/intermediate_files
        """
