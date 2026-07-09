from pathlib import Path


rule render_mqpar:
    conda:
        config["runtime_env"]
    input:
        samples=config["sample_table"],
        template=config["mqpar_template"],
        mzmls=expand("<results>/mzml/{sample}.mzML", sample=SAMPLE_IDS),
    output:
        mqpar="<maxquant>/mqpar/all_samples.mqpar.xml"
    log:
        "<results>/logs/render_mqpar.log"
    params:
        mzml_dir="<results>/mzml",
    script:
        "../scripts/render_mqpar_rule.py"


rule run_maxquant:
    conda:
        config["runtime_env"]
    input:
        mqpar=rules.render_mqpar.output.mqpar,
        mzmls=expand("<results>/mzml/{sample}.mzML", sample=SAMPLE_IDS),
    output:
        protein_groups="<maxquant>/combined/txt/proteinGroups.txt",
        peptides="<maxquant>/combined/txt/peptides.txt",
        evidence="<maxquant>/combined/txt/evidence.txt"
    log:
        "<results>/logs/run_maxquant.log"
    params:
        maxquant_output_dir=lambda wildcards, output: str(Path(output.protein_groups).parents[2]),
        dotnet_bin=config["dotnet_bin"],
        maxquant_cmd_dll=config["maxquant_cmd_dll"],
    shell:
        """
        (cd {params.maxquant_output_dir:q} && {params.dotnet_bin:q} {params.maxquant_cmd_dll:q} mqpar/all_samples.mqpar.xml) > {log:q} 2>&1
        """


rule paleoproteomics_qc:
    conda:
        config["runtime_env"]
    input:
        protein_groups=rules.run_maxquant.output.protein_groups,
        peptides=rules.run_maxquant.output.peptides,
        evidence=rules.run_maxquant.output.evidence
    output:
        json="<results>/reports/paleoproteomics-qc.json",
        html="<results>/reports/paleoproteomics-qc.html"
    log:
        "<results>/logs/paleoproteomics_qc.log"
    script:
        "../scripts/paleoproteomics_qc.py"
