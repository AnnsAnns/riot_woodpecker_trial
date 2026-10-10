# Job image = the real RIOT build container plus redis-tools.
#
# Murdock's worker image (riot/murdock-worker) adds redis-tools so that
# `.murdock`'s test-result cache (`redis-cli get/set`) works, and configures
# ccache to use a shared redis backend. We do the same on top of riotbuild.
#
#   docker build -t riotbuild-cached:poc poc/riotbuild-cached
FROM riot/riotbuild:latest

RUN apt-get update \
 && apt-get install -y --no-install-recommends redis-tools \
 && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
