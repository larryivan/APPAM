from pathlib import Path


rule render_mqpar_batch:
    conda:
        config["runtime_env"]
    input:
        samples=config["sample_table"],
        template=config["mqpar_template"],
        mzmls=MZML_TARGETS
    output:
        mqpar="<maxquant>/batch/mqpar.xml"
    log:
        "<results>/logs/render_mqpar/batch.log"
    params:
        sample_ids=SAMPLE_IDS,
        combined_dir=lambda wildcards, output: str(Path(output.mqpar).parent / "combined")
    script:
        "../scripts/render_mqpar_rule.py"


rule run_maxquant_batch:
    conda:
        config["runtime_env"]
    input:
        mqpar=rules.render_mqpar_batch.output.mqpar,
        mzmls=MZML_TARGETS
    output:
        protein_groups="<maxquant>/batch/combined/txt/proteinGroups.txt",
        peptides="<maxquant>/batch/combined/txt/peptides.txt",
        evidence="<maxquant>/batch/combined/txt/evidence.txt"
    log:
        "<results>/logs/run_maxquant/batch.log"
    params:
        run_dir=lambda wildcards, input: str(Path(input.mqpar).parent),
        dotnet_bin=config["dotnet_bin"],
        maxquant_cmd_dll=config["maxquant_cmd_dll"]
    threads:
        int(config["threads"])
    shell:
        r"""
        mkdir -p "$(dirname {log:q})"
        (cd {params.run_dir:q} && {params.dotnet_bin:q} {params.maxquant_cmd_dll:q} mqpar.xml) > {log:q} 2>&1
        test -s {output.protein_groups:q}
        test -s {output.peptides:q}
        test -s {output.evidence:q}
        """


rule paleoproteomics_qc_batch:
    conda:
        config["runtime_env"]
    input:
        protein_groups=rules.run_maxquant_batch.output.protein_groups,
        peptides=rules.run_maxquant_batch.output.peptides,
        evidence=rules.run_maxquant_batch.output.evidence
    output:
        json="<results>/reports/maxquant/batch.qc.json",
        html="<results>/reports/maxquant/batch.qc.html"
    params:
        analysis_id="batch"
    log:
        "<results>/logs/paleoproteomics_qc/batch.log"
    script:
        "../scripts/paleoproteomics_qc.py"


rule render_mqpar_sample:
    wildcard_constraints:
        sample=SAMPLE_ID_REGEX
    conda:
        config["runtime_env"]
    input:
        samples=config["sample_table"],
        template=config["mqpar_template"],
        mzmls=lambda wildcards: [f"{config['results_dir']}/mzml/{wildcards.sample}.mzML"]
    output:
        mqpar="<maxquant>/samples/{sample}/mqpar.xml"
    log:
        "<results>/logs/render_mqpar/samples/{sample}.log"
    params:
        sample_ids=lambda wildcards: [wildcards.sample],
        combined_dir=lambda wildcards, output: str(Path(output.mqpar).parent / "combined")
    script:
        "../scripts/render_mqpar_rule.py"


rule run_maxquant_sample:
    wildcard_constraints:
        sample=SAMPLE_ID_REGEX
    conda:
        config["runtime_env"]
    input:
        mqpar=rules.render_mqpar_sample.output.mqpar,
        mzml=lambda wildcards: f"{config['results_dir']}/mzml/{wildcards.sample}.mzML"
    output:
        protein_groups="<maxquant>/samples/{sample}/combined/txt/proteinGroups.txt",
        peptides="<maxquant>/samples/{sample}/combined/txt/peptides.txt",
        evidence="<maxquant>/samples/{sample}/combined/txt/evidence.txt"
    log:
        "<results>/logs/run_maxquant/samples/{sample}.log"
    params:
        run_dir=lambda wildcards, input: str(Path(input.mqpar).parent),
        dotnet_bin=config["dotnet_bin"],
        maxquant_cmd_dll=config["maxquant_cmd_dll"]
    threads:
        int(config["threads"])
    shell:
        r"""
        mkdir -p "$(dirname {log:q})"
        (cd {params.run_dir:q} && {params.dotnet_bin:q} {params.maxquant_cmd_dll:q} mqpar.xml) > {log:q} 2>&1
        test -s {output.protein_groups:q}
        test -s {output.peptides:q}
        test -s {output.evidence:q}
        """


rule paleoproteomics_qc_sample:
    wildcard_constraints:
        sample=SAMPLE_ID_REGEX
    conda:
        config["runtime_env"]
    input:
        protein_groups=rules.run_maxquant_sample.output.protein_groups,
        peptides=rules.run_maxquant_sample.output.peptides,
        evidence=rules.run_maxquant_sample.output.evidence
    output:
        json="<results>/reports/maxquant/samples/{sample}.qc.json",
        html="<results>/reports/maxquant/samples/{sample}.qc.html"
    params:
        analysis_id=lambda wildcards: wildcards.sample
    log:
        "<results>/logs/paleoproteomics_qc/samples/{sample}.log"
    script:
        "../scripts/paleoproteomics_qc.py"


rule paleoproteomics_qc_report:
    conda:
        config["runtime_env"]
    input:
        QC_INPUT_TARGETS
    output:
        json="<results>/reports/paleoproteomics-qc.json",
        html="<results>/reports/paleoproteomics-qc.html"
    params:
        mode=MAXQUANT_MODE
    log:
        "<results>/logs/paleoproteomics_qc/report.log"
    script:
        "../scripts/merge_paleoproteomics_qc.py"
