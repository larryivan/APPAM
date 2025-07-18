import os
import json
from typing import Dict, List, Optional, Any
from .base import BaseTool, ToolResult
from ..services.file_manager import get_project_path, list_files


class BioFileAnalyzerTool(BaseTool):
    """Tool to analyze bioinformatics files in project directory."""

    @property
    def name(self) -> str:
        return "analyze_bio_files"

    @property
    def description(self) -> str:
        return "Analyzes bioinformatics files (FASTQ/FASTA/VCF) in project directory and extracts metadata like sequence counts, quality scores, file sizes, etc."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project to analyze"
                },
                "file_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File types to analyze (e.g., 'fastq', 'fasta', 'vcf')",
                    "default": ["fastq", "fasta", "vcf"]
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum directory depth to scan",
                    "default": 5
                }
            },
            "required": ["project_id"]
        }

    def execute(self, project_id: str, file_types: List[str] = None, max_depth: int = 5) -> ToolResult:
        """Execute the bioinformatics file analysis."""
        if file_types is None:
            file_types = ["fastq", "fasta", "vcf"]
        
        try:
            # Get project path
            project_path = get_project_path(project_id)
            if not project_path or not os.path.exists(project_path):
                return ToolResult(
                    is_success=False,
                    content=f"Project directory not found for project ID: {project_id}"
                )
            
            # Scan for bioinformatics files
            bio_files = self._scan_bio_files(project_id, file_types, max_depth)
            
            if not bio_files:
                return ToolResult(
                    is_success=True,
                    content=f"No bioinformatics files found in project {project_id}"
                )
            
            # Analyze each file
            analysis_results = []
            for file_info in bio_files:
                file_analysis = self._analyze_file(project_id, file_info)
                if file_analysis:
                    analysis_results.append(file_analysis)
            
            # Generate summary
            summary = self._generate_summary(analysis_results)
            
            return ToolResult(
                is_success=True,
                content=summary,
                metadata={
                    "action": "bio_file_analysis",
                    "project_id": project_id,
                    "files_analyzed": len(analysis_results),
                    "file_details": analysis_results
                }
            )
            
        except Exception as e:
            return ToolResult(
                is_success=False,
                content=f"Error analyzing bioinformatics files: {str(e)}",
                error_details=str(e)
            )

    def _scan_bio_files(self, project_id: str, file_types: List[str], max_depth: int) -> List[Dict]:
        """Recursively scan for bioinformatics files in project directory."""
        bio_files = []
        
        # Define extensions for each file type
        file_extensions = {
            'fastq': ['.fastq', '.fq', '.fastq.gz', '.fq.gz'],
            'fasta': ['.fasta', '.fa', '.fas', '.fna', '.faa', '.ffn'],
            'vcf': ['.vcf', '.vcf.gz'],
            'gff': ['.gff', '.gff3', '.gtf'],
            'bed': ['.bed'],
            'sam': ['.sam'],
            'bam': ['.bam']
        }
        
        def scan_directory(path: str, current_depth: int = 0):
            if current_depth > max_depth:
                return
            
            try:
                items = list_files(project_id, path)
                if not items:
                    return
                
                for item in items:
                    if item['is_dir']:
                        # Recursively scan subdirectories
                        sub_path = os.path.join(path, item['name']).replace('\\', '/')
                        if sub_path.startswith('./'):
                            sub_path = sub_path[2:]
                        scan_directory(sub_path, current_depth + 1)
                    else:
                        # Check if file matches requested types
                        file_ext = item.get('extension', '').lower()
                        file_name = item['name'].lower()
                        
                        for file_type in file_types:
                            if file_type in file_extensions:
                                extensions = file_extensions[file_type]
                                if any(file_name.endswith(ext) for ext in extensions):
                                    bio_files.append({
                                        'name': item['name'],
                                        'path': os.path.join(path, item['name']).replace('\\', '/'),
                                        'size': item['size'],
                                        'type': file_type,
                                        'extension': file_ext,
                                        'mtime': item['mtime']
                                    })
                                    break
                        
            except Exception as e:
                print(f"Error scanning directory {path}: {e}")
        
        scan_directory(".")
        return bio_files

    def _analyze_file(self, project_id: str, file_info: Dict) -> Dict:
        """Analyze a single bioinformatics file."""
        try:
            file_path = file_info['path']
            file_type = file_info['type']
            
            # Get absolute path
            abs_path = get_project_path(project_id, file_path)
            if not os.path.exists(abs_path):
                return None
            
            # Basic file info
            analysis = {
                'name': file_info['name'],
                'path': file_path,
                'type': file_type,
                'size_mb': round(file_info['size'] / (1024 * 1024), 2),
                'size_bytes': file_info['size']
            }
            
            # Type-specific analysis
            if file_type == 'fastq':
                analysis.update(self._analyze_fastq(abs_path))
            elif file_type == 'fasta':
                analysis.update(self._analyze_fasta(abs_path))
            elif file_type == 'vcf':
                analysis.update(self._analyze_vcf(abs_path))
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing file {file_info['name']}: {e}")
            return None

    def _analyze_fastq(self, file_path: str) -> Dict:
        """Analyze FASTQ file."""
        try:
            sequence_count = 0
            total_length = 0
            gc_count = 0
            quality_scores = []
            
            # For large files, sample first 1000 sequences
            max_sequences = 1000
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    lines.append(line.strip())
                    if (i + 1) % 4 == 0:  # Every 4 lines is one sequence
                        if len(lines) >= 4:
                            sequence_count += 1
                            seq_line = lines[1]
                            quality_line = lines[3]
                            
                            total_length += len(seq_line)
                            gc_count += seq_line.upper().count('G') + seq_line.upper().count('C')
                            
                            # Calculate average quality for this sequence
                            if quality_line:
                                avg_qual = sum(ord(c) - 33 for c in quality_line) / len(quality_line)
                                quality_scores.append(avg_qual)
                            
                            lines = []
                            
                            if sequence_count >= max_sequences:
                                break
            
            # Calculate statistics
            avg_length = total_length / sequence_count if sequence_count > 0 else 0
            gc_content = (gc_count / total_length * 100) if total_length > 0 else 0
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            return {
                'sequence_count': sequence_count,
                'avg_sequence_length': round(avg_length, 1),
                'total_bases': total_length,
                'gc_content_percent': round(gc_content, 1),
                'avg_quality_score': round(avg_quality, 1),
                'format': 'FASTQ',
                'is_sample': sequence_count >= max_sequences
            }
            
        except Exception as e:
            return {
                'error': f"Failed to analyze FASTQ file: {str(e)}",
                'format': 'FASTQ'
            }

    def _analyze_fasta(self, file_path: str) -> Dict:
        """Analyze FASTA file."""
        try:
            sequence_count = 0
            total_length = 0
            gc_count = 0
            current_seq = ''
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('>'):
                        if current_seq:
                            total_length += len(current_seq)
                            gc_count += current_seq.upper().count('G') + current_seq.upper().count('C')
                        sequence_count += 1
                        current_seq = ''
                    else:
                        current_seq += line
                
                # Process last sequence
                if current_seq:
                    total_length += len(current_seq)
                    gc_count += current_seq.upper().count('G') + current_seq.upper().count('C')
            
            avg_length = total_length / sequence_count if sequence_count > 0 else 0
            gc_content = (gc_count / total_length * 100) if total_length > 0 else 0
            
            return {
                'sequence_count': sequence_count,
                'avg_sequence_length': round(avg_length, 1),
                'total_bases': total_length,
                'gc_content_percent': round(gc_content, 1),
                'format': 'FASTA'
            }
            
        except Exception as e:
            return {
                'error': f"Failed to analyze FASTA file: {str(e)}",
                'format': 'FASTA'
            }

    def _analyze_vcf(self, file_path: str) -> Dict:
        """Analyze VCF file."""
        try:
            variant_count = 0
            chromosomes = set()
            variant_types = {'SNP': 0, 'INDEL': 0, 'OTHER': 0}
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith('#') and line:
                        parts = line.split('\t')
                        if len(parts) >= 5:
                            variant_count += 1
                            chromosomes.add(parts[0])
                            
                            # Classify variant type
                            ref = parts[3]
                            alt = parts[4]
                            if len(ref) == 1 and len(alt) == 1:
                                variant_types['SNP'] += 1
                            elif len(ref) != len(alt):
                                variant_types['INDEL'] += 1
                            else:
                                variant_types['OTHER'] += 1
            
            return {
                'variant_count': variant_count,
                'chromosome_count': len(chromosomes),
                'chromosomes': sorted(list(chromosomes)),
                'snp_count': variant_types['SNP'],
                'indel_count': variant_types['INDEL'],
                'other_variants': variant_types['OTHER'],
                'format': 'VCF'
            }
            
        except Exception as e:
            return {
                'error': f"Failed to analyze VCF file: {str(e)}",
                'format': 'VCF'
            }

    def _generate_summary(self, analysis_results: List[Dict]) -> str:
        """Generate a human-readable summary of the analysis results."""
        if not analysis_results:
            return "No bioinformatics files found in the project."
        
        summary = f"Bioinformatics File Analysis Summary:\n"
        summary += f"Total files analyzed: {len(analysis_results)}\n\n"
        
        # Group by file type
        by_type = {}
        for result in analysis_results:
            file_type = result['type']
            if file_type not in by_type:
                by_type[file_type] = []
            by_type[file_type].append(result)
        
        # Generate summary for each type
        for file_type, files in by_type.items():
            summary += f"{file_type.upper()} Files ({len(files)}):\n"
            
            for file in files:
                summary += f"  📁 {file['name']} ({file['size_mb']} MB)\n"
                
                if file_type == 'fastq':
                    if 'sequence_count' in file:
                        summary += f"    • Sequences: {file['sequence_count']:,}\n"
                        summary += f"    • Avg length: {file['avg_sequence_length']} bp\n"
                        summary += f"    • GC content: {file['gc_content_percent']}%\n"
                        summary += f"    • Avg quality: {file['avg_quality_score']}\n"
                elif file_type == 'fasta':
                    if 'sequence_count' in file:
                        summary += f"    • Sequences: {file['sequence_count']:,}\n"
                        summary += f"    • Avg length: {file['avg_sequence_length']} bp\n"
                        summary += f"    • GC content: {file['gc_content_percent']}%\n"
                elif file_type == 'vcf':
                    if 'variant_count' in file:
                        summary += f"    • Variants: {file['variant_count']:,}\n"
                        summary += f"    • SNPs: {file['snp_count']:,}\n"
                        summary += f"    • INDELs: {file['indel_count']:,}\n"
                        summary += f"    • Chromosomes: {file['chromosome_count']}\n"
                
                if 'error' in file:
                    summary += f"    ⚠️ {file['error']}\n"
            
            summary += "\n"
        
        return summary 