FROM apache/spark-py:v3.4.0

USER root

# Install required packages
RUN apt-get update && \
    apt-get install -y curl unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Download Hadoop AWS and AWS SDK JAR files for S3A support
RUN cd /opt/spark/jars && \
    curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

# Create work directory
RUN mkdir -p /opt/bitnami/spark/work-dir

# Switch back to spark user
USER 185

WORKDIR /opt/spark/work-dir
