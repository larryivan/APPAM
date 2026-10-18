SUMMARY_DIR = f"{RESULTS_DIR}/summaries"


rule mag_summary_per_sample:
    conda:
        config["tools"]["reporting_env"]
    input:
        bins_dir=FINAL_BINS_PATTERN,
        checkm2=lambda wildcards: (
            f"{RESULTS_DIR}/checkm2/{wildcards.sample}/quality_report.tsv"
            if config["params"].get("enable_checkm2", True) else []
        ),
        gtdb_done=lambda wildcards: (
            f"{RESULTS_DIR}/gtdbtk/{wildcards.sample}/classify_wf.done"
            if config["params"].get("enable_gtdbtk", True) else []
        ),
        gunc=lambda wildcards: (
            f"{RESULTS_DIR}/gunc/{wildcards.sample}/GUNC.progenomes_2.1.maxCSS_level.tsv"
            if config["params"].get("enable_gunc", True) else []
        )
    output:
        sample_summary=f"{SUMMARY_DIR}/{{sample}}.MAG_summary.tsv"
    log:
        f"{LOGS_DIR}/summaries/{{sample}}.MAG_summary.log"
    benchmark:
        f"{BENCHMARK_DIR}/summaries/{{sample}}.MAG_summary.txt"
    threads: 1
    resources:
        mem_mb=4096
    script:
        "../scripts/build_mag_summary.py"


rule mag_summary:
    conda:
        config["tools"]["reporting_env"]
    input:
        expand(f"{SUMMARY_DIR}/{{sample}}.MAG_summary.tsv", sample=SAMPLES)
    output:
        table=f"{SUMMARY_DIR}/MAG_summary.tsv"
    log:
        f"{LOGS_DIR}/summaries/MAG_summary.log"
    benchmark:
        f"{BENCHMARK_DIR}/summaries/MAG_summary.txt"
    threads: 1
    resources:
        mem_mb=4096
    script:
        "../scripts/merge_mag_summaries.py"
