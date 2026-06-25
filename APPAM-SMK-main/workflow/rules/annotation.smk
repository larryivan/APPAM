# workflow/rules/annotation.smk
import os


REFINED_BINS = f"{RESULTS_DIR}/metawrap/bin_refinement/{{sample}}/metawrap_50_10_bins"
ANNOTATION_THREADS = int(config["params"].get("annotation_threads", 8))


rule prokka_annotation:
    conda: config["tools"].get("prokka_env", "../envs/APPAM-ENV-B.yaml")
    input:
        bins_dir=REFINED_BINS
    output:
        outdir=directory(f"{RESULTS_DIR}/annotation/prokka/{{sample}}"),
        done=f"{RESULTS_DIR}/annotation/prokka/{{sample}}/prokka.done"
    log:
        f"{LOGS_DIR}/annotation/prokka/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/annotation/prokka/{{sample}}.txt"
    threads: ANNOTATION_THREADS
    resources:
        mem_mb=32000
    shell:
        r"""
        mkdir -p {output.outdir} $(dirname {log})
        : > {log}
        shopt -s nullglob
        for bin in {input.bins_dir}/*.fa; do
            bin_name="$(basename "$bin" .fa)"
            bin_out="{output.outdir}/$bin_name"
            rm -rf "$bin_out"
            prokka "$bin" \
                --outdir "$bin_out" \
                --prefix "$bin_name" \
                --cpus {threads} \
                --kingdom Bacteria \
                --metagenome \
                --force >> {log} 2>&1
        done
        touch {output.done}
        """


rule eggnog_annotation:
    conda: config["tools"].get("eggnog_env", "../envs/APPAM-ENV-B.yaml")
    input:
        prokka_done=f"{RESULTS_DIR}/annotation/prokka/{{sample}}/prokka.done",
        prokka_dir=f"{RESULTS_DIR}/annotation/prokka/{{sample}}"
    output:
        outdir=directory(f"{RESULTS_DIR}/annotation/eggnog/{{sample}}"),
        done=f"{RESULTS_DIR}/annotation/eggnog/{{sample}}/eggnog.done"
    params:
        db=config["databases"]["eggnog_db"]
    log:
        f"{LOGS_DIR}/annotation/eggnog/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/annotation/eggnog/{{sample}}.txt"
    threads: ANNOTATION_THREADS
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {output.outdir} $(dirname {log})
        : > {log}
        shopt -s nullglob
        for faa in {input.prokka_dir}/*/*.faa; do
            prefix="$(basename "$faa" .faa)"
            emapper.py \
                -i "$faa" \
                --itype proteins \
                --data_dir {params.db} \
                -o "$prefix" \
                --output_dir {output.outdir} \
                --cpu {threads} \
                --override >> {log} 2>&1
        done
        touch {output.done}
        """


rule abricate_annotation:
    conda: config["tools"].get("abricate_env", "../envs/APPAM-ENV-B.yaml")
    input:
        bins_dir=REFINED_BINS
    output:
        outdir=directory(f"{RESULTS_DIR}/annotation/abricate/{{sample}}"),
        combined=f"{RESULTS_DIR}/annotation/abricate/{{sample}}/abricate.tsv",
        done=f"{RESULTS_DIR}/annotation/abricate/{{sample}}/abricate.done"
    params:
        db=config["params"].get("abricate_db", "vfdb"),
        minid=config["params"].get("abricate_minid", 80),
        mincov=config["params"].get("abricate_mincov", 80)
    log:
        f"{LOGS_DIR}/annotation/abricate/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/annotation/abricate/{{sample}}.txt"
    threads: ANNOTATION_THREADS
    resources:
        mem_mb=16000
    shell:
        r"""
        mkdir -p {output.outdir} $(dirname {log})
        : > {log}
        : > {output.combined}
        shopt -s nullglob
        first=1
        for bin in {input.bins_dir}/*.fa; do
            bin_name="$(basename "$bin" .fa)"
            out="{output.outdir}/$bin_name.tsv"
            abricate --db {params.db} --minid {params.minid} --mincov {params.mincov} "$bin" > "$out" 2>> {log}
            if [ "$first" -eq 1 ]; then
                cat "$out" >> {output.combined}
                first=0
            else
                tail -n +2 "$out" >> {output.combined}
            fi
        done
        touch {output.done}
        """


rule rgi_annotation:
    conda: config["tools"].get("rgi_env", "../envs/APPAM-ENV-B.yaml")
    input:
        bins_dir=REFINED_BINS
    output:
        outdir=directory(f"{RESULTS_DIR}/annotation/rgi/{{sample}}"),
        done=f"{RESULTS_DIR}/annotation/rgi/{{sample}}/rgi.done"
    params:
        mode=config["databases"].get("rgi_db_mode", "online")
    log:
        f"{LOGS_DIR}/annotation/rgi/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/annotation/rgi/{{sample}}.txt"
    threads: ANNOTATION_THREADS
    resources:
        mem_mb=32000
    shell:
        r"""
        mkdir -p {output.outdir} $(dirname {log})
        : > {log}
        shopt -s nullglob
        local_flag=""
        if [ "{params.mode}" = "local" ]; then
            local_flag="--local"
        fi
        for bin in {input.bins_dir}/*.fa; do
            bin_name="$(basename "$bin" .fa)"
            rgi main \
                --input_sequence "$bin" \
                --output_file "{output.outdir}/$bin_name" \
                --input_type contig \
                --num_threads {threads} \
                $local_flag \
                --clean >> {log} 2>&1
        done
        touch {output.done}
        """


rule antismash_annotation:
    conda: config["tools"].get("antismash_env", "../envs/APPAM-ENV-A.yaml")
    input:
        bins_dir=REFINED_BINS
    output:
        outdir=directory(f"{RESULTS_DIR}/annotation/antismash/{{sample}}"),
        done=f"{RESULTS_DIR}/annotation/antismash/{{sample}}/antismash.done"
    log:
        f"{LOGS_DIR}/annotation/antismash/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/annotation/antismash/{{sample}}.txt"
    threads: ANNOTATION_THREADS
    resources:
        mem_mb=64000
    shell:
        r"""
        mkdir -p {output.outdir} $(dirname {log})
        : > {log}
        shopt -s nullglob
        for bin in {input.bins_dir}/*.fa; do
            bin_name="$(basename "$bin" .fa)"
            bin_out="{output.outdir}/$bin_name"
            rm -rf "$bin_out"
            antismash "$bin" \
                --output-dir "$bin_out" \
                --cpus {threads} \
                --genefinding-tool prodigal >> {log} 2>&1
        done
        touch {output.done}
        """
