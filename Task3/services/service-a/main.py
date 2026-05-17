import os
import logging

import httpx
from fastapi import FastAPI

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "service-a")
SERVICE_B_URL = os.getenv("SERVICE_B_URL", "http://service-b:8080/")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://simplest-collector:4317")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(SERVICE_NAME)

resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(SERVICE_NAME)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()


@app.get("/")
def root():
    with tracer.start_as_current_span("service-a.handle_root") as span:
        span.set_attribute("order.id", "demo-order-42")
        log.info("service-a received request, calling service-b at %s", SERVICE_B_URL)
        with httpx.Client(timeout=5.0) as client:
            r = client.get(SERVICE_B_URL)
            payload = r.json()
        span.set_attribute("service-b.status_code", r.status_code)
        return {"service": SERVICE_NAME, "downstream": payload}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
