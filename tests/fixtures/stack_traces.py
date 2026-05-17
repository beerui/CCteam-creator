"""Sample stack traces covering Chrome V8 / Firefox / plain path / edge cases."""

CHROME_V8 = """TypeError: Cannot read property 'x' of undefined
    at onResponse (https://example.com/static/js/agent.abc123.js:631:67170)
    at handleResponse (https://example.com/static/js/main.js:42:15)
    at <anonymous>"""

FIREFOX = """TypeError: Cannot read property 'x' of undefined
onResponse@https://example.com/static/js/agent.abc123.js:631:67170
handleResponse@https://example.com/static/js/main.js:42:15"""

PLAIN_PATH = "src/pages/agent/api/conv.js:42:15"

VENDOR_FIRST = """TypeError: ...
    at someFunc (https://example.com/static/js/chunk-vendors.abc.js:1:200)
    at onResponse (https://example.com/static/js/agent.abc.js:631:67170)"""

MIN_JS_FIRST = """TypeError: ...
    at fn (https://example.com/static/js/main.min.js:1:200)
    at onResponse (https://example.com/static/js/agent.js:631:67170)"""

EMPTY = ""

GARBLED = "some random error message without proper format"

WINDOWS_PATH = """TypeError: ...
    at onResponse (C:\\Users\\jane\\app\\src\\main.js:42:15)"""

URL_QUERY = """TypeError: ...
    at onResponse (https://example.com/static/js/agent.js?v=1.2.3:631:67170)"""

URL_QUERY_FIREFOX = """TypeError: ...
onResponse@https://example.com/static/js/agent.js?t=12345:631:67170"""

URL_QUERY_PLAIN = "src/pages/agent/api/conv.js?v=2:42:15"
