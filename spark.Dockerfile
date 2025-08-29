FROM apache/spark-py:v3.4.0

USER root

# Install AWS CLI and additional Python packages
RUN apt-get update && apt-get install -y curl && \
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Download Hadoop AWS and AWS SDK JAR files for S3A support
RUN cd /opt/spark/jars && \
    curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.2/hadoop-aws-3.3.2.jar && \
    curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.1026/aws-java-sdk-bundle-1.11.1026.jar

# Create work directory
RUN mkdir -p /opt/bitnami/spark/work-dir

# Switch back to spark user
USER 185

WORKDIR /opt/spark/work-dir
