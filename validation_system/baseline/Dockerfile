FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git less \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git init \
    && git remote add origin https://github.com/pallets/click.git \
    && git fetch --depth=1 origin cf19179e8e2fd54c601378cec9e0d21bb12b6fb1 \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "cf19179e8e2fd54c601378cec9e0d21bb12b6fb1"

RUN python -m pip install --no-cache-dir --no-deps pytest==9.0.2 iniconfig==2.3.0 packaging==26.0 pluggy==1.6.0 pygments==2.20.0 flit-core==3.12.0 \
    && python -m pip install --no-cache-dir --no-deps --no-build-isolation -e .

CMD ["pytest", "-q"]
