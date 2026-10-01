FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY chatgraph ./chatgraph
RUN pip install .
RUN useradd --create-home bot
WORKDIR /app
COPY examples/stream/bot.py ./bot.py
RUN chown bot /app
USER bot
CMD ["python", "bot.py"]
