FROM public.ecr.aws/lambda/python:3.12 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /build
COPY pyproject.toml uv.lock ./

RUN uv export --frozen --no-emit-workspace --no-dev --no-editable -o requirements.txt && \
    uv pip install \
    --no-cache \
    --system \
    --target "${LAMBDA_TASK_ROOT}" \
    -r requirements.txt

FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

COPY app/ app/

CMD [ "app.lambda_function.handler" ]
