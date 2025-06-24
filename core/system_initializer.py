from core.metrics import run_server
from modules.resource_limiter import ResourceLimiter
from modules.self_diagnostics import SelfDiagnostics

diagnostics = SelfDiagnostics()
diagnostics.start()

limiter = ResourceLimiter()
limiter.start()

# start live metrics server
run_server()
