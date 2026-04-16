from pathlib import Path


rule render_mqpar:
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
    input:
        mqpar=rules.render_mqpar.output.mqpar,
        mzmls=expand("<results>/mzml/{sample}.mzML", sample=SAMPLE_IDS),
    output:
        protein_groups="<maxquant>/combined/txt/proteinGroups.txt"
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
