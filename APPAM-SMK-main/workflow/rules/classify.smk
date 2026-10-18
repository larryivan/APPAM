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
        db=config["databases"]["gtdbtk_db"],
        # The ANI screen sketches every reference genome (about 46 GB for
        # r226) in GTDB-Tk's temporary directory. /tmp usually sits on the
        # small root disk, where two samples at once fill it and skani fails
        # on a missing markers.bin, so keep it beside the run's results.
        tmpdir=lambda wc, output: os.path.join(output.outdir, "tmp"),
    threads: 16
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {output.outdir:q} {params.tmpdir:q} "$(dirname {log:q})"
        gtdbtk_tmp={params.tmpdir:q}
        trap 'rm -rf "$gtdbtk_tmp"' EXIT

        env GTDBTK_DATA_PATH={params.db:q} gtdbtk classify_wf \
            --genome_dir {input.bins_dir:q} \
            -x fa \
            --out_dir {output.outdir:q} \
            --cpus {threads} \
            --tmpdir "$gtdbtk_tmp" \
            &> {log:q}
        touch {output.done:q}
        """
