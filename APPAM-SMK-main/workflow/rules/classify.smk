import os


rule gtdbtk_classify:
    conda: "../envs/APPAM-ENV-B.yaml"
    input:
        bins_dir = f"{RESULTS_DIR}/metawrap/bin_refinement/{{sample}}/metawrap_50_10_bins"
    output:
        outdir=directory(f"{RESULTS_DIR}/gtdbtk/{{sample}}"),
        done = f"{RESULTS_DIR}/gtdbtk/{{sample}}/classify_wf.done"
    log:
        f"{LOGS_DIR}/gtdbtk/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/gtdbtk/{{sample}}.txt"
    threads: 16
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {output.outdir} $(dirname {log})

        gtdbtk classify_wf \
            --genome_dir {input.bins_dir} \
            -x fa \
            --out_dir {output.outdir} \
            --cpus {threads} \
            &> {log}
        touch {output.done}
        """
