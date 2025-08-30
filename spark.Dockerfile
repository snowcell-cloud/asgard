FROM apache/spark-py:v3.4.0

USER root

# Install required packages
RUN apt-get update && \
    apt-get install -y curl unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create python symlink for compatibility and set PYTHONPATH for PySpark
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Set up PySpark environment
RUN PY4J_JAR=$(find /opt/spark/python/lib -name "py4j-*.zip" | head -1) && \
    echo "PYTHONPATH=/opt/spark/python:$PY4J_JAR:\$PYTHONPATH" >> /etc/environment

# Set environment variables for PySpark
ENV PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Download Hadoop AWS and AWS SDK JAR files for S3A support
RUN cd /opt/spark/jars && \
    curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

# Create work directory and ensure proper permissions
RUN mkdir -p /opt/spark/work-dir && \
    chown -R 185:185 /opt/spark/work-dir

# Copy SQL transformation script
COPY sql_transform_embedded.py /opt/spark/sql_transform.py
RUN chmod +x /opt/spark/sql_transform.py && chown 185:185 /opt/spark/sql_transform.py

# Switch back to spark user
USER 185

WORKDIR /opt/spark/work-dir
