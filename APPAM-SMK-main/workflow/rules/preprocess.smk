import os


PREPROCESS_METHOD = config["params"].get("preprocess_method", "adapter_removal").lower()

if PREPROCESS_METHOD not in {"adapter_removal", "fastp"}:
    raise ValueError(
        "params.preprocess_method must be either 'adapter_removal' or 'fastp'. "
        f"Got: {PREPROCESS_METHOD}"
    )

if PREPROCESS_METHOD == "fastp":
    rule fastp_preprocess:
        conda: "../envs/APPAM-ENV-A.yaml"
        input:
            r1=lambda wc: f"{RAW_DATA_DIR}/{wc.sample}_R1.fastq.gz",
            r2=lambda wc: f"{RAW_DATA_DIR}/{wc.sample}_R2.fastq.gz"
        output:
            se=f"{PREPROCESS_DIR}/{{sample}}.single.fastq",
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
            mkdir -p {params.outdir} $(dirname {log})
            tmpdir=$(mktemp -d)
            trap 'rm -rf "$tmpdir"' EXIT

            trimmed_r1="$tmpdir/{wildcards.sample}.trimmed_R1.fastq.gz"
            trimmed_r2="$tmpdir/{wildcards.sample}.trimmed_R2.fastq.gz"
            unpaired_r1="$tmpdir/{wildcards.sample}.unpaired_R1.fastq.gz"
            unpaired_r2="$tmpdir/{wildcards.sample}.unpaired_R2.fastq.gz"
            merged="$tmpdir/{wildcards.sample}.merged.fastq.gz"

            fastp \
                --in1 {input.r1} \
                --in2 {input.r2} \
                --out1 "$trimmed_r1" \
                --out2 "$trimmed_r2" \
                --unpaired1 "$unpaired_r1" \
                --unpaired2 "$unpaired_r2" \
                --merged_out "$merged" \
                --merge \
                --adapter_sequence {params.adapter1} \
                --adapter_sequence_r2 {params.adapter2} \
                {params.detect_adapter_flag} \
                --html {output.html} \
                --json {output.json} \
                --thread {threads} \
                > {log} 2>&1

            for f in "$merged" "$trimmed_r1" "$trimmed_r2" "$unpaired_r1" "$unpaired_r2"; do
                if [ ! -s "$f" ]; then
                    printf "" | gzip -c > "$f"
                fi
            done

            zcat "$merged" "$trimmed_r1" "$trimmed_r2" "$unpaired_r1" "$unpaired_r2" > {output.se} 2>> {log}
            """
else:
    rule fastqc:
        conda: "../envs/APPAM-ENV-A.yaml"
        input:
            r1=lambda wc: f"{RAW_DATA_DIR}/{wc.sample}_R1.fastq.gz",
            r2=lambda wc: f"{RAW_DATA_DIR}/{wc.sample}_R2.fastq.gz"
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
            mkdir -p {params.outdir} $(dirname {log})
            fastqc {input.r1} {input.r2} -o {params.outdir} -t {threads} 2> {log}
            """

    rule adapter_removal:
        conda: "../envs/APPAM-ENV-A.yaml"
        input:
            r1=lambda wc: f"{RAW_DATA_DIR}/{wc.sample}_R1.fastq.gz",
            r2=lambda wc: f"{RAW_DATA_DIR}/{wc.sample}_R2.fastq.gz"
        output:
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
            mkdir -p {params.outdir} $(dirname {log})
            AdapterRemoval --file1 {input.r1} --file2 {input.r2} \
                --basename {params.basename} \
                --threads {threads} \
                --trimns --trimqualities \
                --adapter1 {params.adapter1} \
                --adapter2 {params.adapter2} \
                --collapse \
                --gzip  \
                2> {log}
            """

    rule collapse_to_single_end:
        conda: "../envs/APPAM-ENV-A.yaml"
        input:
            collapsed=f"{PREPROCESS_DIR}/{{sample}}.collapsed.gz",
            collapsed_trunc=f"{PREPROCESS_DIR}/{{sample}}.collapsed.truncated.gz",
            singleton=f"{PREPROCESS_DIR}/{{sample}}.singleton.truncated.gz"
        output:
            se=f"{PREPROCESS_DIR}/{{sample}}.single.fastq"
        log:
            f"{LOGS_DIR}/adapter_removal/{{sample}}.collapse.log"
        threads: 24
        resources:
            mem_mb=64000
        shell:
            r"""
            mkdir -p $(dirname {log})
            zcat {input.collapsed} {input.collapsed_trunc} {input.singleton} > {output.se} 2> {log}
            """
