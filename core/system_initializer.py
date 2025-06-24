from modules.self_diagnostics import SelfDiagnostics
from modules.resource_limiter import ResourceLimiter

diagnostics = SelfDiagnostics()
diagnostics.start()

limiter = ResourceLimiter()
limiter.start()
