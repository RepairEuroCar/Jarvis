import time
from typing import List, Optional

import aiohttp

from utils.logger import get_logger


class LoggedClientSession(aiohttp.ClientSession):
    """ClientSession with automatic request logging using TraceConfig."""

    def __init__(
        self, *args, trace_configs: Optional[List[aiohttp.TraceConfig]] = None, **kwargs
    ):
        logger = get_logger().getChild("http")
        trace_config = aiohttp.TraceConfig()

        async def on_request_start(session, context, params):
            context.start = time.monotonic()

        async def on_request_end(session, context, params):
            duration = time.monotonic() - getattr(context, "start", time.monotonic())
            logger.info(
                "%s %s -> %s (%.2fs)",
                params.method,
                params.url,
                params.response.status,
                duration,
            )

        trace_config.on_request_start.append(on_request_start)
        trace_config.on_request_end.append(on_request_end)

        if trace_configs:
            trace_configs.append(trace_config)
        else:
            trace_configs = [trace_config]

        kwargs["trace_configs"] = trace_configs
        super().__init__(*args, **kwargs)
