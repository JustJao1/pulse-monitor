FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api api
COPY lib lib
COPY public public
COPY run.py .
USER 65534:65534
EXPOSE 8765
CMD ["python","-c","from run import LocalHandler, ThreadingHTTPServer; ThreadingHTTPServer(('0.0.0.0',8765),LocalHandler).serve_forever()"]
