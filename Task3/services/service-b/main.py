import os
import logging
import random

from fastapi import FastAPI

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "service-b")
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


@app.get("/")
def root():
    with tracer.start_as_current_span("service-b.calculate") as span:
        polygons = random.randint(1000, 100000)
        price = polygons * 0.0123
        span.set_attribute("pricing.polygon_count", polygons)
        span.set_attribute("pricing.price", price)
        log.info("service-b calculated price=%.2f for polygons=%d", price, polygons)
        return {"service": SERVICE_NAME, "polygons": polygons, "price": round(price, 2)}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
