import os


rule gtdbtk_classify:
    conda: config["tools"].get("gtdbtk_env", "../../../docker/tools/environments/gtdbtk.yml")
    input:
        bins_dir=FINAL_BINS_PATTERN
    output:
        outdir=directory(f"{RESULTS_DIR}/gtdbtk/{{sample}}"),
        done = f"{RESULTS_DIR}/gtdbtk/{{sample}}/classify_wf.done"
    log:
        f"{LOGS_DIR}/gtdbtk/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/gtdbtk/{{sample}}.txt"
    params:
        db=config["databases"]["gtdbtk_db"]
    threads: 16
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {output.outdir:q} "$(dirname {log:q})"

        env GTDBTK_DATA_PATH={params.db:q} gtdbtk classify_wf \
            --genome_dir {input.bins_dir:q} \
            -x fa \
            --out_dir {output.outdir:q} \
            --cpus {threads} \
            &> {log:q}
        touch {output.done:q}
        """
