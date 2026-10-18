import os


PREPROCESS_METHOD = config["params"].get("preprocess_method", "fastp").lower()

if PREPROCESS_METHOD not in {"adapter_removal", "fastp"}:
    raise ValueError(
        "params.preprocess_method must be either 'adapter_removal' or 'fastp'. "
        f"Got: {PREPROCESS_METHOD}"
    )


if PREPROCESS_METHOD == "fastp":
    rule fastp_preprocess:
        conda: config["tools"]["preprocessing_env"]
        input:
            r1=sample_r1,
            r2=sample_r2
        output:
            paired_r1=f"{PREPROCESS_DIR}/{{sample}}.paired_R1.fastq.gz",
            paired_r2=f"{PREPROCESS_DIR}/{{sample}}.paired_R2.fastq.gz",
            se=f"{PREPROCESS_DIR}/{{sample}}.single.fastq.gz",
            all_se=f"{PREPROCESS_DIR}/{{sample}}.all.single.fastq.gz",
            html=f"{PREPROCESS_DIR}/{{sample}}.fastp.html",
            json=f"{PREPROCESS_DIR}/{{sample}}.fastp.json"
        params:
            outdir=lambda wc, output: os.path.dirname(output.se),
            detect_adapter_flag="--detect_adapter_for_pe"
            if config["params"].get("fastp_detect_adapter_for_pe", True)
            else "",
            adapter1=config["params"]["adapter1"],
            adapter2=config["params"]["adapter2"]
        log:
            f"{LOGS_DIR}/fastp/{{sample}}.log"
        benchmark:
            f"{BENCHMARK_DIR}/fastp/{{sample}}.txt"
        threads: 24
        resources:
            mem_mb=64000
        shell:
            r"""
            mkdir -p {params.outdir:q} $(dirname {log:q})
            tmpdir=$(mktemp -d)
            trap 'rm -rf "$tmpdir"' EXIT

            unpaired_r1="$tmpdir/{wildcards.sample}.unpaired_R1.fastq.gz"
            unpaired_r2="$tmpdir/{wildcards.sample}.unpaired_R2.fastq.gz"
            merged="$tmpdir/{wildcards.sample}.merged.fastq.gz"

            fastp \
                --in1 {input.r1:q} \
                --in2 {input.r2:q} \
                --out1 {output.paired_r1:q} \
                --out2 {output.paired_r2:q} \
                --unpaired1 "$unpaired_r1" \
                --unpaired2 "$unpaired_r2" \
                --merged_out "$merged" \
                --merge \
                --adapter_sequence {params.adapter1:q} \
                --adapter_sequence_r2 {params.adapter2:q} \
                {params.detect_adapter_flag} \
                --html {output.html:q} \
                --json {output.json:q} \
                --thread {threads} \
                > {log:q} 2>&1

            for f in "$merged" "$unpaired_r1" "$unpaired_r2"; do
                if [ ! -e "$f" ]; then
                    printf '' | gzip -c > "$f"
                fi
            done

            cat "$merged" "$unpaired_r1" "$unpaired_r2" > {output.se:q}
            cat {output.paired_r1:q} {output.paired_r2:q} {output.se:q} > {output.all_se:q}
            """
else:
    rule fastqc:
        conda: config["tools"]["preprocessing_env"]
        input:
            r1=sample_r1,
            r2=sample_r2
        output:
            html_r1=f"{PREPROCESS_DIR}/{{sample}}_R1_fastqc.html",
            zip_r1=f"{PREPROCESS_DIR}/{{sample}}_R1_fastqc.zip",
            html_r2=f"{PREPROCESS_DIR}/{{sample}}_R2_fastqc.html",
            zip_r2=f"{PREPROCESS_DIR}/{{sample}}_R2_fastqc.zip"
        params:
            outdir=lambda wc, output: os.path.dirname(output.html_r1)
        log:
            f"{LOGS_DIR}/fastqc/{{sample}}.log"
        benchmark:
            f"{BENCHMARK_DIR}/fastqc/{{sample}}.txt"
        threads: 24
        resources:
            mem_mb=64000
        shell:
            r"""
            mkdir -p {params.outdir:q} $(dirname {log:q})
            tmpdir=$(mktemp -d)
            trap 'rm -rf "$tmpdir"' EXIT
            mkdir -p "$tmpdir/r1" "$tmpdir/r2"

            fastqc {input.r1:q} -o "$tmpdir/r1" -t {threads} > {log:q} 2>&1
            fastqc {input.r2:q} -o "$tmpdir/r2" -t {threads} >> {log:q} 2>&1
            mv "$(find "$tmpdir/r1" -maxdepth 1 -name '*_fastqc.html' -print -quit)" {output.html_r1:q}
            mv "$(find "$tmpdir/r1" -maxdepth 1 -name '*_fastqc.zip' -print -quit)" {output.zip_r1:q}
            mv "$(find "$tmpdir/r2" -maxdepth 1 -name '*_fastqc.html' -print -quit)" {output.html_r2:q}
            mv "$(find "$tmpdir/r2" -maxdepth 1 -name '*_fastqc.zip' -print -quit)" {output.zip_r2:q}
            """

    rule adapter_removal:
        conda: config["tools"]["preprocessing_env"]
        input:
            r1=sample_r1,
            r2=sample_r2
        output:
            paired_r1=f"{PREPROCESS_DIR}/{{sample}}.pair1.truncated.gz",
            paired_r2=f"{PREPROCESS_DIR}/{{sample}}.pair2.truncated.gz",
            collapsed=f"{PREPROCESS_DIR}/{{sample}}.collapsed.gz",
            collapsed_trunc=f"{PREPROCESS_DIR}/{{sample}}.collapsed.truncated.gz",
            singleton=f"{PREPROCESS_DIR}/{{sample}}.singleton.truncated.gz",
            settings=f"{PREPROCESS_DIR}/{{sample}}.settings"
        params:
            basename=lambda wc, output: output.collapsed.replace(".collapsed.gz", ""),
            outdir=lambda wc, output: os.path.dirname(output.collapsed),
            adapter1=config["params"]["adapter1"],
            adapter2=config["params"]["adapter2"]
        log:
            f"{LOGS_DIR}/adapter_removal/{{sample}}.log"
        benchmark:
            f"{BENCHMARK_DIR}/adapter_removal/{{sample}}.txt"
        threads: 24
        resources:
            mem_mb=64000
        shell:
            r"""
            mkdir -p {params.outdir:q} $(dirname {log:q})
            AdapterRemoval --file1 {input.r1:q} --file2 {input.r2:q} \
                --basename {params.basename:q} \
                --threads {threads} \
                --trimns --trimqualities \
                --adapter1 {params.adapter1:q} \
                --adapter2 {params.adapter2:q} \
                --collapse \
                --gzip \
                2> {log:q}
            """

    rule normalize_adapter_removal_reads:
        input:
            paired_r1=f"{PREPROCESS_DIR}/{{sample}}.pair1.truncated.gz",
            paired_r2=f"{PREPROCESS_DIR}/{{sample}}.pair2.truncated.gz",
            collapsed=f"{PREPROCESS_DIR}/{{sample}}.collapsed.gz",
            collapsed_trunc=f"{PREPROCESS_DIR}/{{sample}}.collapsed.truncated.gz",
            singleton=f"{PREPROCESS_DIR}/{{sample}}.singleton.truncated.gz"
        output:
            paired_r1=f"{PREPROCESS_DIR}/{{sample}}.paired_R1.fastq.gz",
            paired_r2=f"{PREPROCESS_DIR}/{{sample}}.paired_R2.fastq.gz",
            se=f"{PREPROCESS_DIR}/{{sample}}.single.fastq.gz",
            all_se=f"{PREPROCESS_DIR}/{{sample}}.all.single.fastq.gz"
        log:
            f"{LOGS_DIR}/adapter_removal/{{sample}}.normalize.log"
        benchmark:
            f"{BENCHMARK_DIR}/adapter_removal/{{sample}}.normalize.txt"
        threads: 1
        resources:
            mem_mb=1024
        shell:
            r"""
            mkdir -p $(dirname {log:q})
            cp {input.paired_r1:q} {output.paired_r1:q}
            cp {input.paired_r2:q} {output.paired_r2:q}
            cat {input.collapsed:q} {input.collapsed_trunc:q} {input.singleton:q} > {output.se:q}
            cat {output.paired_r1:q} {output.paired_r2:q} {output.se:q} > {output.all_se:q}
            printf 'paired and single-end read streams retained\n' > {log:q}
            """
