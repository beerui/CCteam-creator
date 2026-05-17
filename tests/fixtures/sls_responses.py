"""Sample SLS GetLogs responses (already deserialized to list[dict])."""

SAMPLE_LOGS = [
    {
        "__time__": "1716000123",
        "app.id": "c67xxx",
        "app.name": "大集客服",
        "app.env": "daily",
        "view.name": "/agent",
        "exception.message": "conv list failed: 33001",
        "exception.message.convergence": "conv list failed: 33001",
        "exception.stack": (
            "TypeError: ...\n"
            "    at onResponse (https://example.com/static/js/agent.abc.js:631:67170)"
        ),
        "view.name.convergence": "/agent",
        "event_id": "evt-001",
        "session.id": "sess-001",
    },
    {
        "__time__": "1716000200",
        "app.id": "c67xxx",
        "app.name": "大集客服",
        "app.env": "daily",
        "view.name": "/agent?foo=1",
        "exception.message": "conv list failed: 33001",
        "exception.message.convergence": "conv list failed: 33001",
        "exception.stack": (
            "TypeError: ...\n"
            "    at onResponse (https://example.com/static/js/agent.abc.js:631:67170)"
        ),
        "view.name.convergence": "/agent",
        "event_id": "evt-002",
        "session.id": "sess-002",
    },
    {
        "__time__": "1716000300",
        "app.id": "c67xxx",
        "app.name": "大集客服",
        "app.env": "daily",
        "view.name": "/login",
        "exception.message": "token 无效",
        "exception.message.convergence": "token 无效",
        "exception.stack": (
            "Error: ...\n"
            "    at verify (https://example.com/static/js/auth.def.js:42:1)"
        ),
        "view.name.convergence": "/login",
        "event_id": "evt-003",
        "session.id": "sess-003",
    },
]
