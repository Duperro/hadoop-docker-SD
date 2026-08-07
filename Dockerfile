FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG HADOOP_VERSION=3.4.3
ARG HADOOP_SHA512=e25be7e57b4d3c5bfe83895844321a21d6cf7331266d524d8983c27cf484e576c3d79b3b60d590f8cddecf16229d0e232de2491b1b61b362ee7d67072c7290e1

ARG SPARK_VERSION=3.5.7
ARG SPARK_SHA512=f3b7d5974d746b9aaecb19104473da91068b698a4d292177deb75deb83ef9dc7eb77062446940561ac9ab7ee3336fb421332b1c877292dab4ac1b6ca30f4f2e0

# Instalar Java y herramientas necesarias
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-11-jdk-headless \
        curl \
        ca-certificates \
        procps \
        iputils-ping \
        net-tools \
        iproute2 \
        python3 \
        python3-pip \
        openssh-client \
        openssl \
        tcpdump \
        tini && \
    rm -rf /var/lib/apt/lists/*

# Variables de Java y Hadoop
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

ENV HADOOP_HOME=/opt/hadoop
ENV HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV HADOOP_COMMON_HOME=/opt/hadoop
ENV HADOOP_HDFS_HOME=/opt/hadoop
ENV HADOOP_MAPRED_HOME=/opt/hadoop
ENV HADOOP_YARN_HOME=/opt/hadoop

ENV SPARK_HOME=/opt/spark
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

ENV PATH="${PATH}:${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin:${SPARK_HOME}/bin:${SPARK_HOME}/sbin"

# Crear usuario para ejecutar Hadoop
RUN useradd --create-home --shell /bin/bash hadoop

# Descargar y verificar Hadoop
RUN curl -fSL \
    "https://downloads.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" \
    -o /tmp/hadoop.tar.gz && \
    echo "${HADOOP_SHA512}  /tmp/hadoop.tar.gz" | sha512sum -c - && \
    mkdir -p "${HADOOP_HOME}" && \
    tar -xzf /tmp/hadoop.tar.gz \
        --strip-components=1 \
        -C "${HADOOP_HOME}" && \
    rm /tmp/hadoop.tar.gz

# Descargar y verificar Apache Spark
RUN curl -fSL \
    "https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz" \
    -o /tmp/spark.tgz && \
    echo "${SPARK_SHA512}  /tmp/spark.tgz" | sha512sum -c - && \
    mkdir -p "${SPARK_HOME}" && \
    tar -xzf /tmp/spark.tgz \
        --strip-components=1 \
        -C "${SPARK_HOME}" && \
    rm /tmp/spark.tgz

# Carpetas utilizadas por los nodos
RUN mkdir -p \
        /data/hdfs/namenode \
        /data/hdfs/datanode \
        /scripts && \
    chown -R hadoop:hadoop \
        "${HADOOP_HOME}" \
        /data \
        /scripts

# Incorporar la configuración de Hadoop
COPY --chown=hadoop:hadoop config/ ${HADOOP_CONF_DIR}/

# Incorporar los scripts de inicio
COPY --chown=hadoop:hadoop scripts/ /scripts/

RUN chmod +x /scripts/*.sh

# Incorporar configuración de Spark
COPY --chown=hadoop:hadoop spark-config/ ${SPARK_HOME}/conf/

RUN chmod +x ${SPARK_HOME}/conf/spark-env.sh

# Instalar dependencias Python del Laboratorio 2
COPY laboratorio2/requirements.txt /tmp/requirements.txt

RUN pip3 install --no-cache-dir \
        -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

USER hadoop
WORKDIR /home/hadoop

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash"]