from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Connect to localhost (We will forward the port next)
tempo_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)

# Service Name (This appears in Grafana)
resource = Resource(attributes={"service.name": "my-first-trace"})

provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(tempo_exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

print("Sending trace...")
with tracer.start_as_current_span("main-request") as parent:
    parent.set_attribute("user.role", "admin")
    
    # Create a child span
    with tracer.start_as_current_span("database-query") as child:
        child.set_attribute("sql.query", "SELECT * FROM users")
        print("Processing DB query...")

print("Done! Check Grafana.")
