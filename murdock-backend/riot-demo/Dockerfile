FROM riot/riotbuild:latest

# process_result.py uses orjson. The RIOT image does not include it.
RUN pip install --no-cache-dir orjson

COPY murdock-backend/riot-demo/riot-run.py /usr/local/bin/riot-run.py
COPY murdock-scripts/process_result.py /opt/murdock-scripts/process_result.py
COPY murdock-scripts/common.py /opt/murdock-scripts/common.py

RUN chmod +x /usr/local/bin/riot-run.py

WORKDIR /murdock
