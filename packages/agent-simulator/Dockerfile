FROM python:3.12-slim

WORKDIR /app/packages/agent-simulator

COPY packages/agent-simulator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/agent-simulator/ .

ENV PYTHONPATH=/app/packages/agent-simulator

CMD ["uvicorn", "simulator.main:app", "--host", "0.0.0.0", "--port", "8100"]
