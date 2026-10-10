# Lightweight stand-in for RIOT's `riot/riotbuild` image, used for the
# Woodpecker PoC. It contains just enough to compile RIOT for the `native*`
# boards and run the resulting tests on the agent host.
#
# The production RIOT CI uses the much larger (~15 GB) `riot/riotbuild` image
# from riotdocker. This image exists so the PoC can run on a disk-constrained
# machine. Swap `image:` in the pipelines for `riot/riotbuild:latest` to use
# the real thing.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        make \
        git \
        python3 \
        python3-pip \
        python3-pexpect \
        python3-serial \
        ccache \
        pkg-config \
        libssl-dev \
        ca-certificates \
        xxd \
        file \
        xxhash \
        gcc-multilib \
        g++-multilib \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ccache on PATH, cached in a shared location (mounted by the agent if desired)
ENV CCACHE_DIR=/cache/.ccache
ENV CCACHE_BASEDIR=/woodpecker/src

# RIOT's native build runs the produced binary directly on the host/agent, so
# the image needs a normal toolchain only. Make sure a git identity exists for
# any tooling that shells out to git.
RUN git config --system user.name "riot-poc" \
 && git config --system user.email "riot-poc@example.invalid"

WORKDIR /woodpecker/src
