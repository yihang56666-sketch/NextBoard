## Summary

-

## Verification

- [ ] `python tools\release_verify.py --profile quick`
- [ ] `ruff check tools/ tests/`
- [ ] `mypy tools/ --config-file mypy.ini`
- [ ] `pytest tests/ -v --basetemp=.tmp-pytest-current`
- [ ] `python tests\validate_hardware_butler.py`
- [ ] `python tools\release_verify.py` before release or broad launch changes
- [ ] Plugin runtime synced with `python tools\package_hardware_butler_plugin.py` when packaged files changed

## Safety

- [ ] No real hardware action bypasses were added
- [ ] New hardware-affecting paths remain planned, dry-run, simulated, or confirmation-gated
