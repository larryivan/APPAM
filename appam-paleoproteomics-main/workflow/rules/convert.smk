rule thermo_raw_to_mzml:
    wildcard_constraints:
        sample=RAW_SAMPLE_ID_REGEX
    input:
        raw=_raw_input
    output:
        mzml="<results>/thermo/{sample}.mzML"
    log:
        "<results>/logs/thermo_raw_to_mzml/{sample}.log"
    params:
        thermo_raw_file_parser=config["thermo_raw_file_parser"],
    threads:
        int(config["threads"])
    shell:
        """
        {params.thermo_raw_file_parser:q} -i={input.raw:q} -b={output.mzml:q} -f=2 -m=0 > {log:q} 2>&1
        """


rule bruker_d_to_mzml:
    wildcard_constraints:
        sample=D_SAMPLE_ID_REGEX
    input:
        bruker=_d_input
    output:
        mzml="<results>/bruker/{sample}.mzML"
    log:
        "<results>/logs/bruker_d_to_mzml/{sample}.log"
    params:
        timsconvert_bin=config["timsconvert_bin"],
        outdir=lambda wildcards, output: output.mzml[:-5],
    threads:
        int(config["threads"])
    shell:
        """
        {params.timsconvert_bin:q} --input {input.bruker:q} --outdir {params.outdir:q} --mode raw > {log:q} 2>&1
        mv {params.outdir:q}/*.mzML {output.mzml:q}
        """


rule finalize_raw_mzml:
    wildcard_constraints:
        sample=RAW_SAMPLE_ID_REGEX
    input:
        mzml=rules.thermo_raw_to_mzml.output.mzml
    output:
        mzml="<results>/mzml/{sample}.mzML"
    log:
        "<results>/logs/finalize_raw_mzml/{sample}.log"
    params:
        openms_fileconverter=config["openms_fileconverter"],
    threads:
        int(config["threads"])
    shell:
        """
        {params.openms_fileconverter:q} -in {input.mzml:q} -out {output.mzml:q} -out_type mzML -force_MaxQuant_compatibility > {log:q} 2>&1
        """


rule finalize_bruker_mzml:
    wildcard_constraints:
        sample=D_SAMPLE_ID_REGEX
    input:
        mzml=rules.bruker_d_to_mzml.output.mzml
    output:
        mzml="<results>/mzml/{sample}.mzML"
    log:
        "<results>/logs/finalize_bruker_mzml/{sample}.log"
    params:
        openms_fileconverter=config["openms_fileconverter"],
    threads:
        int(config["threads"])
    shell:
        """
        {params.openms_fileconverter:q} -in {input.mzml:q} -out {output.mzml:q} -out_type mzML -force_MaxQuant_compatibility > {log:q} 2>&1
        """
