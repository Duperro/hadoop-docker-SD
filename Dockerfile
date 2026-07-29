FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG HADOOP_VERSION=3.4.3
ARG HADOOP_SHA512=e25be7e57b4d3c5bfe83895844321a21d6cf7331266d524d8983c27cf484e576c3d79b3b60d590f8cddecf16229d0e232de2491b1b61b362ee7d67072c7290e1

# Instalar Java y herramientas necesarias
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-11-jdk-headless \
        curl \
        ca-certificates \
        procps \
        iputils-ping \
        net-tools \
        openssh-client \
        tini && \
    rm -rf /var/lib/apt/lists/*

# Variables de Java y Hadoop
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV HADOOP_HOME=/opt/hadoop
ENV HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV PATH="${PATH}:${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin"

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

# Carpetas utilizadas por los nodos
RUN mkdir -p \
        /data/hdfs/namenode \
        /data/hdfs/datanode \
        /scripts && \
    chown -R hadoop:hadoop \
        "${HADOOP_HOME}" \
        /data \
        /scripts

# Incorporar los archivos XML y la lista de workers
COPY --chown=hadoop:hadoop config/ ${HADOOP_CONF_DIR}/

# Incorporar los scripts de inicio
COPY --chown=hadoop:hadoop scripts/ /scripts/

RUN chmod +x /scripts/*.sh

USER hadoop
WORKDIR /home/hadoop

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash"]