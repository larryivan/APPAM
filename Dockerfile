# 使用mambaforge作为基础镜像，支持mamba包管理器
FROM condaforge/mambaforge:24.3.0-0

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/conda/bin:$PATH \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    NODE_OPTIONS="--max-old-space-size=4096" \
    NVM_DIR="/root/.nvm"

# 预配置时区避免交互提示
RUN ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo 'tzdata tzdata/Areas select Asia' | debconf-set-selections && \
    echo 'tzdata tzdata/Zones/Asia select Shanghai' | debconf-set-selections

# 更新系统包并安装必要的系统依赖
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y --fix-missing \
    curl \
    git \
    gcc \
    g++ \
    make \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    || (DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y --fix-missing \
    curl \
    git \
    gcc \
    g++ \
    make \
    build-essential \
    && rm -rf /var/lib/apt/lists/*)

# 升级mamba并配置conda channels
RUN mamba update -n base -c conda-forge mamba && \
    conda config --add channels defaults && \
    conda config --add channels bioconda && \
    conda config --add channels conda-forge && \
    conda config --set channel_priority flexible

# 创建专用的Python 3.12环境
RUN mamba create -n appam python=3.12.0 -y && \
    conda clean --all -f -y

# 安装 nvm, Node.js 和 npm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
    . "$NVM_DIR/nvm.sh" && \
    nvm install 22 && \
    nvm use 22 && \
    nvm alias default 22

# 更新 PATH 环境变量以包含 Node.js
ENV PATH="$NVM_DIR/versions/node/v22.17.1/bin:$PATH"

# 激活环境并安装生物信息学工具
SHELL ["conda", "run", "-n", "appam", "/bin/bash", "-c"]

# 安装生物信息学工具
RUN mamba install -c bioconda fastqc -y && \
    mamba install -c bioconda adapterremoval -y && \
    mamba install -c bioconda megahit -y && \
    mamba install -c bioconda bwa -y && \
    mamba install -c bioconda freebayes -y && \
    mamba install -c bioconda bcftools samtools metabat2 maxbin2 concoct das_tool -y && \
    mamba install -c bioconda prokka -y && \
    conda clean --all -f -y

# 尝试安装可能有架构兼容性问题的工具（如果失败则跳过）
RUN mamba install -c bioconda gtdbtk -y || echo "gtdbtk installation failed, skipping..." && \
    mamba install -c bioconda checkm-genome -y || echo "checkm-genome installation failed, skipping..." && \
    conda clean --all -f -y

# 安装pip工具
RUN pip install multiqc pydamage

# 复制项目文件
COPY . /app/

# 安装Python后端依赖
WORKDIR /app/backend
RUN pip install -r requirements.txt

# 构建前端应用
WORKDIR /app/frontend

# 安装 pnpm 并设置 npm 配置
RUN . "$NVM_DIR/nvm.sh" && \
    npm install -g pnpm@9.12.0 && \
    npm config set registry https://registry.npmjs.org/ && \
    pnpm config set registry https://registry.npmjs.org/

# 清理 node_modules 和重新安装依赖
RUN . "$NVM_DIR/nvm.sh" && \
    rm -rf node_modules pnpm-lock.yaml && \
    pnpm install --frozen-lockfile=false && \
    pnpm run build

# 创建启动脚本
WORKDIR /app
RUN echo '#!/bin/bash\n\
source /opt/conda/etc/profile.d/conda.sh\n\
conda activate appam\n\
source /root/.nvm/nvm.sh\n\
cd /app/backend\n\
python run.py &\n\
cd /app/frontend\n\
pnpm run preview\n\
' > start.sh && chmod +x start.sh

# 暴露端口
EXPOSE 5001 8082

# 设置启动命令
CMD ["bash", "start.sh"] 