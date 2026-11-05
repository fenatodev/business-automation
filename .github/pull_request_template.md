## Capability

<!-- What complete functional slice does this PR deliver? -->

## Included

- [ ] Backend/API
- [ ] UX/operator flow
- [ ] Tests
- [ ] Documentation

## Safety

- [ ] Tenant isolation and authorization preserved
- [ ] No secrets, real customer data or production actions
- [ ] Migration/security review completed if applicable

## Validation

```text
uv run pytest
.venv/bin/python -m compileall app tests
git diff --check
```
