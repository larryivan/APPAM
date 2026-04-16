# workflow/rules/contigs_filter.smk


rule split_contigs_by_pydamage:
    conda: "../envs/APPAM-ENV-A.yaml"
    input:
        contigs=f"{RESULTS_DIR}/megahit/{{sample}}/final.contigs.fa",
        pydamage=f"{RESULTS_DIR}/pydamage/{{sample}}/pydamage_results.csv"
    output:
        ancient=f"{RESULTS_DIR}/pydamage/{{sample}}/ancient.contigs.fa",
        modern=f"{RESULTS_DIR}/pydamage/{{sample}}/modern.contigs.fa"
    params:
        contig_column=config["params"].get("pydamage_contig_column", "reference"),
        qvalue_column=config["params"].get("pydamage_qvalue_column", "qvalue"),
        qvalue_max=config["params"].get("pydamage_qvalue_max", 0.05),
        predicted_accuracy_column=config["params"].get("pydamage_predicted_accuracy_column", "predicted_accuracy"),
        predicted_accuracy_min=config["params"].get("pydamage_predicted_accuracy_min", 0.5)
    log:
        f"{LOGS_DIR}/pydamage_split/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/pydamage_split/{{sample}}.txt"
    threads: 1
    script:
        "../scripts/contigs_filter.py"
