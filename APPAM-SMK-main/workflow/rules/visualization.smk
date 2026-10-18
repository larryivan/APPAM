VISUALIZATION_CONFIG = config.get("visualization", {})
VISUALIZATION_DIR = f"{RESULTS_DIR}/visualization"
REPORTING_ENV = config["tools"]["reporting_env"]

VISUALIZATION_FIGURE_KEYS = ["reads", "pydamage"]
VISUALIZATION_FIGURE_TARGETS = [
    *expand(f"{VISUALIZATION_DIR}/{{sample}}/reads_length/length_hist.png", sample=SAMPLES),
    *expand(f"{VISUALIZATION_DIR}/{{sample}}/contig_stats/pydamage_props.png", sample=SAMPLES),
]

if config["params"].get("enable_gtdbtk", True):
    VISUALIZATION_FIGURE_KEYS += ["ani", "phylum", "genus", "species"]
    VISUALIZATION_FIGURE_TARGETS += [
        *expand(f"{VISUALIZATION_DIR}/{{sample}}/ani/ani_hist.png", sample=SAMPLES),
        *expand(f"{VISUALIZATION_DIR}/{{sample}}/rose/phylum_rose.png", sample=SAMPLES),
        *expand(f"{VISUALIZATION_DIR}/{{sample}}/rose/genus_rose.png", sample=SAMPLES),
        *expand(f"{VISUALIZATION_DIR}/{{sample}}/rose/species_topn_rose.png", sample=SAMPLES),
        *expand(f"{VISUALIZATION_DIR}/{{sample}}/alpha_diversity/alpha_diversity.tsv", sample=SAMPLES),
    ]

if config["params"].get("enable_checkm2", True):
    VISUALIZATION_FIGURE_KEYS.append("checkm2")
    VISUALIZATION_FIGURE_TARGETS += expand(
        f"{VISUALIZATION_DIR}/{{sample}}/checkm2/checkm2_scatter.png", sample=SAMPLES
    )

if config["params"].get("enable_gunc", True) and config["params"].get("enable_checkm2", True):
    VISUALIZATION_FIGURE_KEYS.append("gunc")
    VISUALIZATION_FIGURE_TARGETS += expand(
        f"{VISUALIZATION_DIR}/{{sample}}/gunc/gunc_css_box_jitter.png", sample=SAMPLES
    )


rule count_read_lengths:
    conda:
        REPORTING_ENV
    input:
        fastq=f"{PREPROCESS_DIR}/{{sample}}.all.single.fastq.gz"
    output:
        counts=f"{VISUALIZATION_DIR}/{{sample}}/reads_length/length_counts.tsv"
    log:
        f"{LOGS_DIR}/visualization/{{sample}}/reads_length.count.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/{{sample}}/reads_length.count.txt"
    threads: 1
    resources:
        mem_mb=2048
    script:
        "../scripts/count_read_lengths.py"


rule plot_read_lengths:
    conda:
        REPORTING_ENV
    input:
        counts=rules.count_read_lengths.output.counts,
        script="workflow/scripts/plot_reads_length.py"
    output:
        png=f"{VISUALIZATION_DIR}/{{sample}}/reads_length/length_hist.png",
        pdf=f"{VISUALIZATION_DIR}/{{sample}}/reads_length/length_hist.pdf",
        table=f"{VISUALIZATION_DIR}/{{sample}}/reads_length/length_bins.tsv"
    params:
        bin_size=int(VISUALIZATION_CONFIG.get("reads_length_bin_size", 10))
    log:
        f"{LOGS_DIR}/visualization/{{sample}}/reads_length.plot.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/{{sample}}/reads_length.plot.txt"
    threads: 1
    resources:
        mem_mb=4096
    shell:
        r"""
        python {input.script:q} \
            --counts {input.counts:q} \
            --output-png {output.png:q} \
            --output-pdf {output.pdf:q} \
            --output-table {output.table:q} \
            --sample {wildcards.sample:q} \
            --bin-size {params.bin_size} \
            --log {log:q}
        """


rule plot_pydamage_contigs:
    conda:
        REPORTING_ENV
    input:
        pydamage=f"{RESULTS_DIR}/pydamage/{{sample}}/pydamage_results.csv",
        script="workflow/scripts/plot_contig_stats.py"
    output:
        png=f"{VISUALIZATION_DIR}/{{sample}}/contig_stats/pydamage_props.png",
        pdf=f"{VISUALIZATION_DIR}/{{sample}}/contig_stats/pydamage_props.pdf",
        table=f"{VISUALIZATION_DIR}/{{sample}}/contig_stats/pydamage_props.tsv"
    params:
        qvalue_column=config["params"].get("pydamage_qvalue_column", "qvalue"),
        qvalue_max=float(config["params"].get("pydamage_qvalue_max", 0.05)),
        accuracy_column=config["params"].get("pydamage_predicted_accuracy_column", "predicted_accuracy"),
        accuracy_min=float(config["params"].get("pydamage_predicted_accuracy_min", 0.5))
    log:
        f"{LOGS_DIR}/visualization/{{sample}}/contig_stats.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/{{sample}}/contig_stats.txt"
    threads: 1
    resources:
        mem_mb=4096
    shell:
        r"""
        python {input.script:q} \
            --pydamage {input.pydamage:q} \
            --output-png {output.png:q} \
            --output-pdf {output.pdf:q} \
            --output-table {output.table:q} \
            --sample {wildcards.sample:q} \
            --qvalue-column {params.qvalue_column:q} \
            --qvalue-max {params.qvalue_max} \
            --accuracy-column {params.accuracy_column:q} \
            --accuracy-min {params.accuracy_min} \
            --log {log:q}
        """


rule plot_gtdb_ani:
    conda:
        REPORTING_ENV
    input:
        gtdb_done=f"{RESULTS_DIR}/gtdbtk/{{sample}}/classify_wf.done",
        script="workflow/scripts/plot_ani_hist.py"
    output:
        png=f"{VISUALIZATION_DIR}/{{sample}}/ani/ani_hist.png",
        pdf=f"{VISUALIZATION_DIR}/{{sample}}/ani/ani_hist.pdf",
        table=f"{VISUALIZATION_DIR}/{{sample}}/ani/ani_hist.tsv"
    params:
        gtdbtk_dir=lambda wildcards, input: str(input.gtdb_done).rsplit("/", 1)[0],
        start=int(VISUALIZATION_CONFIG.get("ani_bin_start", 95)),
        end=int(VISUALIZATION_CONFIG.get("ani_bin_end", 100)),
        step=int(VISUALIZATION_CONFIG.get("ani_bin_step", 1))
    log:
        f"{LOGS_DIR}/visualization/{{sample}}/ani.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/{{sample}}/ani.txt"
    threads: 1
    resources:
        mem_mb=4096
    shell:
        r"""
        python {input.script:q} \
            --gtdbtk-dir {params.gtdbtk_dir:q} \
            --output-png {output.png:q} \
            --output-pdf {output.pdf:q} \
            --output-table {output.table:q} \
            --sample {wildcards.sample:q} \
            --start {params.start} \
            --end {params.end} \
            --step {params.step} \
            --log {log:q}
        """


rule plot_taxonomy_rose:
    conda:
        REPORTING_ENV
    input:
        gtdb_done=f"{RESULTS_DIR}/gtdbtk/{{sample}}/classify_wf.done",
        script="workflow/scripts/plot_rose_chart.py"
    output:
        phylum_png=f"{VISUALIZATION_DIR}/{{sample}}/rose/phylum_rose.png",
        phylum_pdf=f"{VISUALIZATION_DIR}/{{sample}}/rose/phylum_rose.pdf",
        phylum_table=f"{VISUALIZATION_DIR}/{{sample}}/rose/phylum_counts.tsv",
        genus_png=f"{VISUALIZATION_DIR}/{{sample}}/rose/genus_rose.png",
        genus_pdf=f"{VISUALIZATION_DIR}/{{sample}}/rose/genus_rose.pdf",
        genus_table=f"{VISUALIZATION_DIR}/{{sample}}/rose/genus_counts.tsv",
        species_png=f"{VISUALIZATION_DIR}/{{sample}}/rose/species_topn_rose.png",
        species_pdf=f"{VISUALIZATION_DIR}/{{sample}}/rose/species_topn_rose.pdf",
        species_table=f"{VISUALIZATION_DIR}/{{sample}}/rose/species_topn_counts.tsv"
    params:
        gtdbtk_dir=lambda wildcards, input: str(input.gtdb_done).rsplit("/", 1)[0],
        min_fraction=float(VISUALIZATION_CONFIG.get("rose_chart_min_fraction", 0.01)),
        species_top_n=int(VISUALIZATION_CONFIG.get("species_top_n", 10))
    log:
        f"{LOGS_DIR}/visualization/{{sample}}/rose.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/{{sample}}/rose.txt"
    threads: 1
    resources:
        mem_mb=4096
    shell:
        r"""
        python {input.script:q} \
            --gtdbtk-dir {params.gtdbtk_dir:q} \
            --sample {wildcards.sample:q} \
            --phylum-png {output.phylum_png:q} \
            --phylum-pdf {output.phylum_pdf:q} \
            --phylum-table {output.phylum_table:q} \
            --genus-png {output.genus_png:q} \
            --genus-pdf {output.genus_pdf:q} \
            --genus-table {output.genus_table:q} \
            --species-png {output.species_png:q} \
            --species-pdf {output.species_pdf:q} \
            --species-table {output.species_table:q} \
            --min-fraction {params.min_fraction} \
            --species-top-n {params.species_top_n} \
            --log {log:q}
        """


rule compute_taxonomy_alpha_diversity:
    conda:
        REPORTING_ENV
    input:
        gtdb_done=f"{RESULTS_DIR}/gtdbtk/{{sample}}/classify_wf.done",
        script="workflow/scripts/compute_alpha_diversity.py"
    output:
        table=f"{VISUALIZATION_DIR}/{{sample}}/alpha_diversity/alpha_diversity.tsv"
    params:
        gtdbtk_dir=lambda wildcards, input: str(input.gtdb_done).rsplit("/", 1)[0]
    log:
        f"{LOGS_DIR}/visualization/{{sample}}/alpha_diversity.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/{{sample}}/alpha_diversity.txt"
    threads: 1
    resources:
        mem_mb=2048
    shell:
        r"""
        python {input.script:q} \
            --gtdbtk-dir {params.gtdbtk_dir:q} \
            --output-table {output.table:q} \
            --sample {wildcards.sample:q} \
            --rank phylum --rank genus --rank species \
            --log {log:q}
        """


rule plot_checkm2_quality:
    conda:
        REPORTING_ENV
    input:
        quality=f"{RESULTS_DIR}/checkm2/{{sample}}/quality_report.tsv",
        script="workflow/scripts/plot_checkm_scatter.py"
    output:
        png=f"{VISUALIZATION_DIR}/{{sample}}/checkm2/checkm2_scatter.png",
        pdf=f"{VISUALIZATION_DIR}/{{sample}}/checkm2/checkm2_scatter.pdf",
        table=f"{VISUALIZATION_DIR}/{{sample}}/checkm2/checkm2_scatter.tsv"
    log:
        f"{LOGS_DIR}/visualization/{{sample}}/checkm2.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/{{sample}}/checkm2.txt"
    threads: 1
    resources:
        mem_mb=4096
    shell:
        r"""
        python {input.script:q} \
            --quality-report {input.quality:q} \
            --output-png {output.png:q} \
            --output-pdf {output.pdf:q} \
            --output-table {output.table:q} \
            --sample {wildcards.sample:q} \
            --log {log:q}
        """


rule plot_gunc_quality:
    conda:
        REPORTING_ENV
    input:
        gunc=f"{RESULTS_DIR}/gunc/{{sample}}/GUNC.progenomes_2.1.maxCSS_level.tsv",
        checkm2=f"{RESULTS_DIR}/checkm2/{{sample}}/quality_report.tsv",
        script="workflow/scripts/plot_gunc_css.py"
    output:
        png=f"{VISUALIZATION_DIR}/{{sample}}/gunc/gunc_css_box_jitter.png",
        pdf=f"{VISUALIZATION_DIR}/{{sample}}/gunc/gunc_css_box_jitter.pdf",
        table=f"{VISUALIZATION_DIR}/{{sample}}/gunc/gunc_css_box_jitter.tsv"
    log:
        f"{LOGS_DIR}/visualization/{{sample}}/gunc.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/{{sample}}/gunc.txt"
    threads: 1
    resources:
        mem_mb=4096
    shell:
        r"""
        python {input.script:q} \
            --gunc-report {input.gunc:q} \
            --quality-report {input.checkm2:q} \
            --output-png {output.png:q} \
            --output-pdf {output.pdf:q} \
            --output-table {output.table:q} \
            --sample {wildcards.sample:q} \
            --log {log:q}
        """


rule visualization_report:
    conda:
        REPORTING_ENV
    input:
        summary=rules.mag_summary.output.table,
        figures=VISUALIZATION_FIGURE_TARGETS
    output:
        html=f"{VISUALIZATION_DIR}/report.html",
        data=f"{VISUALIZATION_DIR}/report-data.json"
    params:
        visualization_dir=lambda wildcards, output: str(output.html).rsplit("/", 1)[0],
        samples=SAMPLES,
        figure_keys=VISUALIZATION_FIGURE_KEYS
    log:
        f"{LOGS_DIR}/visualization/report.log"
    benchmark:
        f"{BENCHMARK_DIR}/visualization/report.txt"
    threads: 1
    resources:
        mem_mb=2048
    script:
        "../scripts/build_visualization_report.py"
