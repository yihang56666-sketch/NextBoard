"""Backend integrations for the hardware butler.

This package intentionally contains no executable logic at import time.

Real hardware flash/debug/observe is safety-gated and must go through
``tools.hardware_action_executor`` (which keeps real backends blocked until
backend-specific bench validation). Do not add a flash helper here that calls
a backend's ``flash()`` directly — that bypasses the confirmation-token gate
and the project's planned-gated guarantee.
"""
