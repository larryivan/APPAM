# workflow/rules/binning.smk
import os
rule metawrap_binning:
    conda: config["tools"]["metawrap_env"]
    input:
        contigs=lambda wc: f"{RESULTS_DIR}/pydamage/{wc.sample}/ancient.contigs.fa"
        if config["params"].get("use_ancient_contigs", False)
        else f"{RESULTS_DIR}/megahit/{wc.sample}/final.contigs.fa",
        all_se=f"{PREPROCESS_DIR}/{{sample}}.all.single.fastq.gz"
    output:
        metabat2 = directory(f"{RESULTS_DIR}/metawrap/binning/{{sample}}/metabat2_bins"),
        concoct  = directory(f"{RESULTS_DIR}/metawrap/binning/{{sample}}/concoct_bins"),
        maxbin2  = directory(f"{RESULTS_DIR}/metawrap/binning/{{sample}}/maxbin2_bins")
    params:
        outdir=lambda wc, output: os.path.dirname(output.metabat2),
        selected_dir=lambda wc, output: {
            "metabat2": output.metabat2,
            "maxbin2": output.maxbin2,
            "concoct": output.concoct,
        }[UNREFINED_BINNER],
    log:
        f"{LOGS_DIR}/metawrap_binning/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/metawrap_binning/{{sample}}.txt"
    threads: 48
    shell:
        r"""
        mkdir -p {params.outdir:q} "$(dirname {log:q})"
        metawrap binning -o {params.outdir:q} -t {threads} \
            --metabat2 --maxbin2 --concoct  \
            -a {input.contigs:q} \
            --single-end {input.all_se:q} &> {log:q}
        shopt -s nullglob
        selected_bins=({params.selected_dir:q}/*.fa)
        if [ "${{#selected_bins[@]}}" -eq 0 ]; then
            echo "Selected binner produced no FASTA bins: {params.selected_dir}" >> {log:q}
            exit 1
        fi
        """

rule metawrap_bin_refinement:
    conda: config["tools"]["metawrap_env"]
    input:
        metabat2=f"{RESULTS_DIR}/metawrap/binning/{{sample}}/metabat2_bins",
        maxbin2=f"{RESULTS_DIR}/metawrap/binning/{{sample}}/maxbin2_bins",
        concoct=f"{RESULTS_DIR}/metawrap/binning/{{sample}}/concoct_bins"
    output:
        bins_dir=directory(f"{RESULTS_DIR}/metawrap/bin_refinement/{{sample}}/metawrap_50_10_bins")
    params:
        outdir=lambda wc, output: os.path.dirname(output.bins_dir),
        completeness=config["params"]["bin_completeness"],
        contamination=config["params"]["bin_contamination"],
        checkm_db=config["databases"]["checkm_db"]
    log:
        f"{LOGS_DIR}/metawrap_refinement/{{sample}}.log" 
    benchmark: 
        f"{BENCHMARK_DIR}/metawrap_bin_refinement/{{sample}}.txt"
    threads: 48
    resources:
        mem_mb=128000
    shell:
        r"""
        mkdir -p {params.outdir:q} "$(dirname {log:q})"
        find {input.metabat2:q} {input.maxbin2:q} {input.concoct:q} -name "bin.BinMembers.txt" -delete
        checkm data setRoot {params.checkm_db:q}
        metawrap bin_refinement -o {params.outdir:q} -t {threads} \
            -c {params.completeness} -x {params.contamination} \
            -A {input.metabat2:q} -B {input.maxbin2:q} -C {input.concoct:q} &> {log:q}
        """

rule checkm2:
    conda: config["tools"].get("checkm2_env", "../../../docker/tools/environments/checkm2.yml")
    input:
        FINAL_BINS_PATTERN
    output:
        quality=f"{RESULTS_DIR}/checkm2/{{sample}}/quality_report.tsv"
    params:
        outdir=lambda wc, output: os.path.dirname(output.quality),
        db=config["databases"]["checkm2_db"]
    log:
        f"{LOGS_DIR}/checkm2/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/checkm2/{{sample}}.txt"
    threads: 24
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.outdir:q} "$(dirname {log:q})"
        db_path={params.db:q}
        if [ -d "$db_path" ]; then
            db_file="$(find "$db_path" -type f -name 'uniref100.KO.1.dmnd' | head -n 1)"
            if [ -z "$db_file" ]; then
                echo "No CheckM2 uniref100.KO.1.dmnd database found under $db_path" >&2
                exit 1
            fi
        else
            db_file="$db_path"
        fi
        checkm2 predict \
            --input {input:q} \
            --output-directory {params.outdir:q} \
            --database_path "$db_file" \
            --threads {threads} \
            -x fa &> {log}
        test -s {output.quality}
        """

rule checkm:
    conda: config["tools"].get("checkm1_env", "../../../docker/tools/environments/checkm.yml")
    input:
        FINAL_BINS_PATTERN
    output:
        qa=f"{RESULTS_DIR}/checkm/{{sample}}/bins_qa.txt"
    params:
        outdir=lambda wc, output: os.path.dirname(output.qa),
        db=config["databases"]["checkm1_db"]
    log:
        f"{LOGS_DIR}/checkm/{{sample}}.log"
    benchmark: 
        f"{BENCHMARK_DIR}/checkm/{{sample}}.txt"
    threads: 48
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.outdir:q} "$(dirname {log:q})"
        checkm data setRoot {params.db:q}
        checkm lineage_wf -t {threads} -x fa --tab_table \
            -f {output.qa:q} {input:q} {params.outdir:q} 2> {log:q}
        """

rule gunc:
    conda: config["tools"].get("gunc_env", "../../../docker/tools/environments/binning.yml")
    input:
        FINAL_BINS_PATTERN
    output:
        result=f"{RESULTS_DIR}/gunc/{{sample}}/GUNC.progenomes_2.1.maxCSS_level.tsv"
    params:
        outdir=lambda wc, output: os.path.dirname(output.result),
        db=config["databases"]["gunc_db"]
    log:
        f"{LOGS_DIR}/gunc/{{sample}}.log"
    threads: 24
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {params.outdir:q} "$(dirname {log:q})"
        db_path={params.db:q}
        if [ -d "$db_path" ]; then
            db_file="$(find "$db_path" -maxdepth 2 -type f -name '*.dmnd' | head -n 1)"
            if [ -z "$db_file" ]; then
                echo "No GUNC .dmnd database found under $db_path" >&2
                exit 1
            fi
        else
            db_file="$db_path"
        fi
        gunc run --input_dir {input:q} -t {threads} \
            --out_dir {params.outdir:q} --db_file "$db_file" 2> {log:q}
        """
