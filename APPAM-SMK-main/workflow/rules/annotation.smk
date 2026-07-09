# workflow/rules/annotation.smk
import os


REFINED_BINS = FINAL_BINS_PATTERN
ANNOTATION_THREADS = int(config["params"].get("annotation_threads", 8))


rule prokka_annotation:
    conda: config["tools"].get("prokka_env", "../../../docker/tools/environments/prokka.yml")
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
        mkdir -p {output.outdir:q} "$(dirname {log:q})"
        : > {log:q}
        shopt -s nullglob
        bins=({input.bins_dir:q}/*.fa)
        if [ "${{#bins[@]}}" -eq 0 ]; then
            echo "No MAG FASTA files found under {input.bins_dir}" >> {log:q}
            exit 1
        fi
        for bin in "${{bins[@]}}"; do
            bin_name="$(basename "$bin" .fa)"
            bin_out={output.outdir:q}/"$bin_name"
            rm -rf "$bin_out"
            prokka "$bin" \
                --outdir "$bin_out" \
                --prefix "$bin_name" \
                --cpus {threads} \
                --kingdom Bacteria \
                --metagenome \
                --force >> {log:q} 2>&1
        done
        touch {output.done:q}
        """


rule eggnog_annotation:
    conda: config["tools"].get("eggnog_env", "../../../docker/tools/environments/eggnog_py310.yml")
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
        mkdir -p {output.outdir:q} "$(dirname {log:q})"
        : > {log:q}
        shopt -s nullglob
        faa_files=({input.prokka_dir:q}/*/*.faa)
        if [ "${{#faa_files[@]}}" -eq 0 ]; then
            echo "No Prokka protein FASTA files found under {input.prokka_dir}" >> {log:q}
            exit 1
        fi
        for faa in "${{faa_files[@]}}"; do
            prefix="$(basename "$faa" .faa)"
            emapper.py \
                -i "$faa" \
                --itype proteins \
                --data_dir {params.db:q} \
                -o "$prefix" \
                --output_dir {output.outdir:q} \
                --cpu {threads} \
                --override >> {log:q} 2>&1
        done
        touch {output.done:q}
        """


rule abricate_annotation:
    conda: config["tools"].get("abricate_env", "../../../docker/tools/environments/abricate.yml")
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
        mkdir -p {output.outdir:q} "$(dirname {log:q})"
        : > {log:q}
        : > {output.combined:q}
        shopt -s nullglob
        bins=({input.bins_dir:q}/*.fa)
        if [ "${{#bins[@]}}" -eq 0 ]; then
            echo "No MAG FASTA files found under {input.bins_dir}" >> {log:q}
            exit 1
        fi
        first=1
        for bin in "${{bins[@]}}"; do
            bin_name="$(basename "$bin" .fa)"
            out={output.outdir:q}/"$bin_name.tsv"
            abricate --db {params.db:q} --minid {params.minid} --mincov {params.mincov} "$bin" > "$out" 2>> {log:q}
            if [ "$first" -eq 1 ]; then
                cat "$out" >> {output.combined:q}
                first=0
            else
                tail -n +2 "$out" >> {output.combined:q}
            fi
        done
        touch {output.done:q}
        """


rule rgi_annotation:
    conda: config["tools"].get("rgi_env", "../../../docker/tools/environments/rgi.yml")
    input:
        bins_dir=REFINED_BINS
    output:
        outdir=directory(f"{RESULTS_DIR}/annotation/rgi/{{sample}}"),
        done=f"{RESULTS_DIR}/annotation/rgi/{{sample}}/rgi.done"
    params:
        mode=config["databases"].get("rgi_db_mode", "global"),
        db=config["databases"].get("rgi_db", "")
    log:
        f"{LOGS_DIR}/annotation/rgi/{{sample}}.log"
    benchmark:
        f"{BENCHMARK_DIR}/annotation/rgi/{{sample}}.txt"
    threads: ANNOTATION_THREADS
    resources:
        mem_mb=32000
    shell:
        r"""
        mkdir -p {output.outdir:q} "$(dirname {log:q})"
        : > {log:q}
        shopt -s nullglob
        bins=({input.bins_dir:q}/*.fa)
        if [ "${{#bins[@]}}" -eq 0 ]; then
            echo "No MAG FASTA files found under {input.bins_dir}" >> {log:q}
            exit 1
        fi
        for bin in "${{bins[@]}}"; do
            bin_name="$(basename "$bin" .fa)"
            bin_abs="$(readlink -f "$bin")"
            output_prefix="$(cd {output.outdir:q} && pwd)/$bin_name"
            if [ {params.mode:q} = "local" ]; then
                if [ ! -d {params.db:q} ]; then
                    echo "RGI local database directory not found: {params.db}" >> {log:q}
                    exit 1
                fi
                (
                    cd {params.db:q}
                    rgi main --input_sequence "$bin_abs" --output_file "$output_prefix" \
                        --input_type contig --num_threads {threads} --local --clean
                ) >> {log:q} 2>&1
            else
                rgi main --input_sequence "$bin_abs" --output_file "$output_prefix" \
                    --input_type contig --num_threads {threads} --clean >> {log:q} 2>&1
            fi
        done
        touch {output.done:q}
        """


rule antismash_annotation:
    conda: config["tools"].get("antismash_env", "../../../docker/tools/environments/antismash.yml")
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
        mkdir -p {output.outdir:q} "$(dirname {log:q})"
        : > {log:q}
        shopt -s nullglob
        bins=({input.bins_dir:q}/*.fa)
        if [ "${{#bins[@]}}" -eq 0 ]; then
            echo "No MAG FASTA files found under {input.bins_dir}" >> {log:q}
            exit 1
        fi
        for bin in "${{bins[@]}}"; do
            bin_name="$(basename "$bin" .fa)"
            bin_out={output.outdir:q}/"$bin_name"
            rm -rf "$bin_out"
            antismash "$bin" \
                --output-dir "$bin_out" \
                --cpus {threads} \
                --genefinding-tool prodigal >> {log:q} 2>&1
        done
        touch {output.done:q}
        """
