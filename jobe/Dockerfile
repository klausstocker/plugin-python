# Jobe-in-a-box: a Dockerised Jobe server (see https://github.com/trampgeek/jobe)
# With thanks to David Bowes (d.h.bowes@lancaster.ac.uk) who did all the hard work
# on this originally.

FROM docker.io/ubuntu:24.04 AS catch2-build
ARG CATCH2_VERSION=3.16.0
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates && \
    git clone --depth 1 --branch "v${CATCH2_VERSION}" https://github.com/catchorg/Catch2.git /tmp/catch2 && \
    cmake -S /tmp/catch2 -B /tmp/catch2-build \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/catch2 \
        -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_SHARED_LIBS=OFF \
        -DCATCH_BUILD_TESTING=OFF -DCATCH_INSTALL_DOCS=OFF && \
    cmake --build /tmp/catch2-build --parallel 2 && \
    cmake --install /tmp/catch2-build && \
    printf '%s\n' "$CATCH2_VERSION" > /opt/catch2/VERSION
COPY jobe/catch2_runner.cpp /tmp/catch2_runner.cpp
RUN g++ -std=c++17 -O2 -I/opt/catch2/include -c /tmp/catch2_runner.cpp \
    -o /opt/catch2/lib/letto-catch2-runner.o

FROM docker.io/ubuntu:24.04
COPY --from=catch2-build /opt/catch2 /opt/catch2
COPY jobe/catch2-compile.sh /usr/local/bin/letto-catch2-compile
RUN sed -i 's/\r$//' /usr/local/bin/letto-catch2-compile && \
    chmod 755 /usr/local/bin/letto-catch2-compile

# https://github.com/opencontainers/image-spec/blob/master/annotations.md
LABEL \
    org.opencontainers.image.authors="richard.lobb@canterbury.ac.nz,j.hoedjes@hva.nl,d.h.bowes@herts.ac.uk" \
    org.opencontainers.image.title="JobeInABox" \
    org.opencontainers.image.description="JobeInABox" \
    org.opencontainers.image.documentation="https://github.com/trampgeek/jobeinabox" \
    org.opencontainers.image.source="https://github.com/trampgeek/jobeinabox"

ARG TZ=Pacific/Auckland
ARG JOBE_VERSION=master
ARG API_KEYS=""
# Set up the (apache) environment variables
ENV APACHE_RUN_USER=www-data
ENV APACHE_RUN_GROUP=www-data
ENV APACHE_LOG_DIR=/var/log/apache2
ENV APACHE_LOCK_DIR=/var/lock/apache2
ENV APACHE_PID_FILE=/var/run/apache2.pid
ENV LANG=C.UTF-8

# Copy apache virtual host file for later use
COPY jobe/000-jobe.conf /

# Mount secrets
# Set timezone
# Install extra packages
# Redirect apache logs to stdout
# Configure apache
# Configure php
# Get jobe
# Handle jobe API keys
# Install jobe
# Clean up
RUN ln -snf /usr/share/zoneinfo/"$TZ" /etc/localtime && \
    echo "$TZ" > /etc/timezone && \
    apt-get update && \
    apt-get --no-install-recommends install -yq \
    acl \
    apache2 \
    build-essential \
    fp-compiler \
    git \
    libapache2-mod-php \
    nano \
    nodejs \
    octave \
    default-jdk \
    php \
    php-cli \
    php-mbstring \
    php-intl \
    python3 \
    python3-numpy \
    python3-pip \
    python3-setuptools \
    pylint \
    sqlite3 \
    sudo \
    tzdata \
    unzip && \
    pylint --reports=no --score=n --generate-rcfile > /etc/pylintrc && \
    ln -sf /proc/self/fd/1 /var/log/apache2/access.log && \
    ln -sf /proc/self/fd/1 /var/log/apache2/error.log && \
    sed -i "s/export LANG=C/export LANG=$LANG/" /etc/apache2/envvars && \
    sed -i '1 i ServerName localhost' /etc/apache2/apache2.conf && \
    sed -i 's/ServerTokens\ OS/ServerTokens \Prod/g' /etc/apache2/conf-enabled/security.conf && \
    sed -i 's/ServerSignature\ On/ServerSignature \Off/g' /etc/apache2/conf-enabled/security.conf && \
    rm /etc/apache2/sites-enabled/000-default.conf && \
    mv /000-jobe.conf /etc/apache2/sites-enabled/ && \
    mkdir -p /var/crash && \
    chmod 777 /var/crash && \
    echo '<!DOCTYPE html><html lang="en"><title>Jobe</title><h1>Jobe</h1></html>' > /var/www/html/index.html && \
    git clone --single-branch --branch ${JOBE_VERSION} https://github.com/trampgeek/jobe.git /var/www/html/jobe && \
    apache2ctl start && \
    cd /var/www/html/jobe && \
    if [ -n "${API_KEYS}" ]; then \
    sed -i 's/$require_api_keys = false/$require_api_keys = true/' /var/www/html/jobe/app/Config/Jobe.php && \
    sed -i "s/'2AAA7A.*/$API_KEYS/" /var/www/html/jobe/app/Config/Jobe.php \
    ; fi && \
    /usr/bin/python3 /var/www/html/jobe/install --max_uid=500 && \
    chown -R ${APACHE_RUN_USER}:${APACHE_RUN_GROUP} /var/www/html && \
    apt-get -y autoremove --purge && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

COPY jobe/Catch2cTask.php jobe/Catch2cppTask.php /var/www/html/jobe/app/Libraries/
COPY jobe/CompilecTask.php jobe/CompilecppTask.php /var/www/html/jobe/app/Libraries/
COPY jobe/catch2_compile.py /usr/local/libexec/letto-catch2-compile.py
COPY jobe/start-jobe.sh /usr/local/bin/start-jobe
# Catch2 is required in every final image, not an optional runtime download.
RUN test -s /opt/catch2/VERSION && \
    test -s /opt/catch2/lib/libCatch2.a && \
    test -s /opt/catch2/lib/letto-catch2-runner.o && \
    test -r /opt/catch2/include/catch2/catch_test_macros.hpp && \
    test -x /usr/local/bin/letto-catch2-compile && \
    python3 -m py_compile /usr/local/libexec/letto-catch2-compile.py && \
    php -l /var/www/html/jobe/app/Libraries/Catch2cTask.php && \
    php -l /var/www/html/jobe/app/Libraries/Catch2cppTask.php && \
    php -l /var/www/html/jobe/app/Libraries/CompilecTask.php && \
    php -l /var/www/html/jobe/app/Libraries/CompilecppTask.php && \
    sed -i 's/\r$//' /usr/local/bin/start-jobe && \
    chmod 755 /usr/local/bin/start-jobe && \
    rm -f /tmp/jobe_language_cache_file

# Expose apache
EXPOSE 80

# Healthcheck every minute, minimaltest.py should complete within 2 seconds
# If you're running docker version 25.0 or later, you could consider
# changing the following line to
# HEALTHCHECK --start-period=30s --start-interval=5s --interval=5m --timeout=2s \
HEALTHCHECK --interval=1m --timeout=2s \
    CMD /usr/bin/python3 /var/www/html/jobe/minimaltest.py || exit 1

# Start apache
ENTRYPOINT ["/usr/local/bin/start-jobe"]
CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]
