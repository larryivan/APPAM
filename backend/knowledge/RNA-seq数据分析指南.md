# RNA-seq数据分析指南

## 简介

RNA-seq（RNA sequencing）是一种用于分析细胞中整个转录组的高通量测序技术。它能够检测基因表达水平、发现新的转录本、识别可变剪接等。

## 实验设计

### 生物学重复
- 建议至少3个生物学重复
- 重复数量影响统计检验的功效

### 测序深度
- 人类样本：20-30 million reads
- 模式生物：10-20 million reads
- 非模式生物：30-50 million reads

### 测序策略
- 单端测序：成本低，适合基因表达分析
- 双端测序：提供更多信息，适合转录本组装

## 数据预处理

### 1. 质量控制
```bash
# 使用FastQC检查数据质量
fastqc sample.fastq.gz -o qc_output/

# 使用MultiQC汇总质量报告
multiqc qc_output/
```

### 2. 序列修剪
```bash
# 使用Trimmomatic去除低质量序列
trimmomatic SE -phred33 sample.fastq.gz \
  sample_trimmed.fastq.gz \
  ILLUMINACLIP:TruSeq3-SE.fa:2:30:10 \
  LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36
```

### 3. 去除rRNA污染
```bash
# 使用SortMeRNA去除rRNA序列
sortmerna --ref rRNA_databases.fasta \
  --reads sample_trimmed.fastq.gz \
  --aligned rRNA_aligned \
  --other clean_reads
```

## 序列比对

### 使用STAR进行比对
```bash
# 建立索引
STAR --runMode genomeGenerate \
  --genomeDir genome_index \
  --genomeFastaFiles genome.fa \
  --sjdbGTFfile annotations.gtf

# 进行比对
STAR --runMode alignReads \
  --genomeDir genome_index \
  --readFilesIn sample_clean.fastq.gz \
  --readFilesCommand zcat \
  --outSAMtype BAM SortedByCoordinate \
  --outFileNamePrefix sample_
```

### 使用Hisat2进行比对
```bash
# 建立索引
hisat2-build genome.fa genome_index

# 进行比对
hisat2 -x genome_index -U sample_clean.fastq.gz \
  -S sample.sam --summary-file sample_summary.txt
```

## 表达量定量

### 1. 基于基因的定量
```bash
# 使用featureCounts
featureCounts -a annotations.gtf -o counts.txt \
  -t exon -g gene_id sample.bam

# 使用HTSeq
htseq-count -f bam -r pos -s no -t exon \
  -i gene_id sample.bam annotations.gtf > counts.txt
```

### 2. 基于转录本的定量
```bash
# 使用Salmon
salmon quant -i transcripts_index -l A \
  -r sample_clean.fastq.gz -o salmon_output
```

## 差异表达分析

### 使用DESeq2（R语言）
```r
library(DESeq2)

# 读取计数数据
countData <- read.table("counts.txt", header=TRUE, row.names=1)

# 创建样本信息
colData <- data.frame(
  condition = factor(c("control", "control", "treated", "treated")),
  row.names = colnames(countData)
)

# 创建DESeq对象
dds <- DESeqDataSetFromMatrix(
  countData = countData,
  colData = colData,
  design = ~ condition
)

# 进行差异表达分析
dds <- DESeq(dds)
results <- results(dds)

# 获取显著差异表达基因
sig_genes <- subset(results, padj < 0.05 & abs(log2FoldChange) > 1)
```

### 使用edgeR（R语言）
```r
library(edgeR)

# 创建DGEList对象
y <- DGEList(counts=countData, group=factor(conditions))

# 过滤低表达基因
keep <- filterByExpr(y)
y <- y[keep, , keep.lib.sizes=FALSE]

# 标准化
y <- calcNormFactors(y)

# 估计离散度
y <- estimateDisp(y, design)

# 进行差异表达分析
fit <- glmQLFit(y, design)
qlf <- glmQLFTest(fit)
```

## 功能富集分析

### Gene Ontology分析
```r
library(clusterProfiler)

# GO富集分析
ego <- enrichGO(gene = sig_genes$gene_id,
                OrgDb = org.Hs.eg.db,
                keyType = 'ENSEMBL',
                ont = "ALL",
                pAdjustMethod = "BH",
                pvalueCutoff = 0.01,
                qvalueCutoff = 0.05)
```

### KEGG通路分析
```r
# KEGG富集分析
kk <- enrichKEGG(gene = sig_genes$gene_id,
                organism = 'hsa',
                pvalueCutoff = 0.05)
```

## 可视化

### 火山图
```r
library(ggplot2)

# 创建火山图
volcano_plot <- ggplot(results_df, aes(x=log2FoldChange, y=-log10(pvalue))) +
  geom_point(aes(color=significant)) +
  scale_color_manual(values=c("black", "red")) +
  theme_minimal() +
  labs(title="Volcano Plot", x="log2 Fold Change", y="-log10 p-value")
```

### 热图
```r
library(pheatmap)

# 创建热图
pheatmap(log2(norm_counts + 1), 
         scale="row", 
         clustering_distance_rows="correlation",
         clustering_distance_cols="correlation")
```

## 高级分析

### 时间序列分析
```r
library(maSigPro)

# 时间序列差异表达分析
time_series_design <- make.design.matrix(edesign, degree=2)
NBp <- p.vector(data, time_series_design, Q=0.05, MT.adjust="BH")
```

### 共表达网络分析
```r
library(WGCNA)

# 构建共表达网络
net <- blockwiseModules(datExpr, power=6, TOMType="unsigned", 
                       minModuleSize=30, reassignThreshold=0)
```

## 质量控制指标

### 比对质量
- 比对率：>80%
- 唯一比对率：>70%
- 基因组覆盖度：均匀分布

### 表达量质量
- 检测到的基因数：>15,000（人类）
- 样本间相关性：>0.9（重复样本）
- 主成分分析：重复样本聚类

## 常见问题与解决方案

### 1. 比对率低
- 检查参考基因组版本
- 调整比对参数
- 检查数据质量

### 2. 批次效应
- 使用ComBat进行批次校正
- 在实验设计中平衡批次

### 3. 样本离群
- 检查样本处理过程
- 使用PCA识别离群样本
- 考虑去除问题样本

## 标准化流程

1. **质量控制**：FastQC + MultiQC
2. **预处理**：Trimmomatic + SortMeRNA
3. **比对**：STAR或Hisat2
4. **定量**：featureCounts或Salmon
5. **差异分析**：DESeq2或edgeR
6. **功能分析**：clusterProfiler
7. **可视化**：ggplot2 + pheatmap

## 推荐资源

- RNA-seqlopedia：RNA-seq基础知识
- Bioconductor：R语言生物信息学包
- Galaxy：在线分析平台
- ENCODE：数据标准和最佳实践 