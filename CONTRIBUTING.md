# Contributing to Cicada AML

Thank you for considering a contribution. This document covers what you need to get started.

---

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in Supabase credentials
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env       # set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
```

---

## Code Style

### Python

- **Linter/Formatter**: [Ruff](https://docs.astral.sh/ruff/)
- Run before committing:

```bash
cd backend
ruff check .
ruff format .
```

- Type hints are expected on all public functions.
- Docstrings follow Google style.

### TypeScript / React

- **Linter**: ESLint (config in `frontend/eslint.config.js`)
- **Type checking**: `npx tsc --noEmit`
- Run before committing:

```bash
cd frontend
npm run lint
npx tsc --noEmit
```

- Prefer named exports for components. Default exports for page-level components only.
- Use Tailwind utility classes; avoid inline `style={}` unless dynamic values require it.

---

## Testing

### Backend

```bash
cd backend
pytest                          # full suite
pytest tests/test_heuristics.py # specific module
pytest -x --tb=short           # stop on first failure, short traceback
```

All new heuristics, services, or API routes should have corresponding tests.

### Frontend

```bash
cd frontend
npx tsc --noEmit   # type checking (no dedicated test runner yet)
```

---

## Adding a Heuristic

1. Choose the correct module based on the ID range:
   - `traditional.py` (1-90), `blockchain.py` (91-142), `hybrid.py` (143-155, 176-185), `ai_enabled.py` (156-175).
2. Subclass `BaseHeuristic`. Set `id`, `name`, `environment`, `lens_tags`, `description`, `data_requirements`.
3. Implement `evaluate()`. Return a `HeuristicResult` with `triggered`, `confidence`, `explanation`, and `evidence`.
4. Register with `register(_instance)` at module bottom.
5. Run `pytest tests/test_heuristics.py` to verify registration and basic contract.

---

## Adding an API Route

1. Create or extend a router in `backend/app/api/`.
2. Use `CurrentUserId` dependency for auth-scoped endpoints.
3. Add the router in `backend/app/main.py` with the appropriate prefix and tags.
4. Add a test in `backend/tests/test_api.py` or a dedicated test file.

---

## Database Migrations

- Place new migrations in `supabase/migrations/` with the next sequential prefix (e.g. `024_*.sql`).
- Each migration must be idempotent (`IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`).
- Document the migration in the table in `README.md`.

---

## Commit Messages

- Use present tense ("Add feature" not "Added feature").
- Keep the subject line under 72 characters.
- Reference issue numbers when applicable.

---

## Pull Requests

1. Branch from `main`.
2. Keep PRs focused -- one feature or fix per PR.
3. Ensure `pytest` and `npx tsc --noEmit` pass.
4. Update `README.md` if the change affects documented behavior (API routes, env vars, migrations).
5. Request review from at least one maintainer.

---

## Reporting Issues

- Use GitHub Issues.
- Include reproduction steps, expected behavior, and actual behavior.
- For security vulnerabilities, email the maintainer directly instead of filing a public issue.

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
