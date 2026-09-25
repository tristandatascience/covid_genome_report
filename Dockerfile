FROM mambaorg/micromamba:bookworm

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        git git-lfs unzip procps curl perl fonts-dejavu-core poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Application (Flask + pysam + reportlab) et typage HLA (arcasHLA + kallisto + samtools + T1K)
RUN micromamba install -y -n base -c conda-forge -c bioconda \
        arcas-hla flask pysam samtools t1k reportlab

ENV PATH=/opt/conda/bin:$PATH

# Base de référence IMGT/HLA — clonage du dépôt (le dépôt IMGT distribue
# désormais hla.dat sous forme zippée : on la décompresse), puis
# reconstruction de la référence une fois pour toutes dans l'image.
RUN PKG=$(ls -d /opt/conda/share/arcas-hla-*/scripts | head -1 | xargs dirname) && \
    git lfs install --force && \
    rm -rf "$PKG/dat/IMGTHLA" && \
    git clone https://github.com/ANHIG/IMGTHLA.git "$PKG/dat/IMGTHLA" && \
    cd "$PKG/dat/IMGTHLA" && \
    { [ -f hla.dat ] || unzip -o hla.dat.zip; } && \
    cd / && arcasHLA reference --rebuild

# Références chr6 pour le décodage des fichiers CRAM — quatre saveurs
# (GRCh37/GRCh38 majuscules Ensembl + hg19/hg38 soft-maskés UCSC),
# chacune en double nommage ("6" et "chr6"), bgzip + index faidx.
RUN mkdir -p /opt/refs && cd /opt/refs && \
    curl -fsSL -o c38.fa.gz https://ftp.ensembl.org/pub/release-112/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.chromosome.6.fa.gz && \
    curl -fsSL -o c37.fa.gz https://ftp.ensembl.org/pub/grch37/release-87/fasta/homo_sapiens/dna/Homo_sapiens.GRCh37.dna.chromosome.6.fa.gz && \
    curl -fsSL -o m38.fa.gz https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr6.fa.gz && \
    curl -fsSL -o m37.fa.gz https://hgdownload.soe.ucsc.edu/goldenPath/hg19/chromosomes/chr6.fa.gz && \
    zcat c37.fa.gz | sed '1s/.*/>6/'     >  chr6.GRCh37.fa && \
    zcat c37.fa.gz | sed '1s/.*/>chr6/'  >> chr6.GRCh37.fa && \
    zcat c38.fa.gz | sed '1s/.*/>6/'     >  chr6.GRCh38.fa && \
    zcat c38.fa.gz | sed '1s/.*/>chr6/'  >> chr6.GRCh38.fa && \
    zcat m37.fa.gz | sed '1s/.*/>chr6/'  >  chr6.hg19m.fa && \
    zcat m37.fa.gz | sed '1s/.*/>6/'     >> chr6.hg19m.fa && \
    zcat m38.fa.gz | sed '1s/.*/>chr6/'  >  chr6.hg38m.fa && \
    zcat m38.fa.gz | sed '1s/.*/>6/'     >> chr6.hg38m.fa && \
    rm -f c37.fa.gz c38.fa.gz m37.fa.gz m38.fa.gz && \
    for f in chr6.GRCh37 chr6.GRCh38 chr6.hg19m chr6.hg38m; do \
        bgzip -f $f.fa && samtools faidx $f.fa.gz; \
    done

# Index T1K pour le typage HLA rapide depuis FASTQ (base IPD-IMGT/HLA)
RUN mkdir -p /opt/t1k && cd /opt/t1k && t1k-build.pl -o hlaidx --download IPD-IMGT/HLA

WORKDIR /srv
COPY app/ .

EXPOSE 8080
CMD ["python", "app.py"]
