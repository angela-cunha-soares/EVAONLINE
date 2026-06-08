# How to Contribute to EVAonline

Thank you for your interest in contributing! EVAonline is an open-source project for calculating reference evapotranspiration (ET₀) using the FAO-56 Penman-Monteith method with data fusion via Kalman filters. The backend is Python (FastAPI + Celery), the frontend is Dash, and the database is PostgreSQL with migrations managed by Alembic.

Contributions of any kind are welcome: bug fixes, new features, documentation improvements, tests, translations, etc.

## Before You Start

1. **Read the [README.md](README.md)** – it contains installation instructions, how to run the project locally, and an overview of the project.

2. **Search the [open issues](https://github.com/angela-cunha-soares/EVAONLINE/issues)** – check if what you want to do is already being discussed. If not, **open a new issue** describing the problem or idea (use the available templates, if any).

3. **Discuss before starting** – comment on the issue to align expectations. This avoids duplicate work and increases the chances of your pull request being accepted.

4. **Follow the [Code of Conduct](CODE_OF_CONDUCT.md)** – respect other contributors and maintain a welcoming environment.

## Recommended Contribution Workflow

1. **Fork** the repository to your GitHub account.

2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/EVAONLINE.git
   cd EVAONLINE
   ```

3. **Create a branch** for your contribution:
   ```bash
   git checkout -b my-contribution
   ```

4. **Make your changes and test locally:**
   - Run the existing tests and, if possible, add new tests for your changes.
   - Command to run all tests:
     ```bash
     pytest backend/tests/ frontend/tests/ -v
     ```
   - If you changed the database models, create a new Alembic migration:
     ```bash
     alembic revision --autogenerate -m "Migration description"
     ```

5. **Format the code following the project's style:**
   - We use `black` for formatting, `flake8` for linting, and `mypy` for type checking.

   - If you have set up pre-commit (recommended), simply run:
     ```bash
     pre-commit run --all-files
     ```

6. **Commit** with clear and descriptive messages (in Portuguese or English, but consistently):
   - Good example: `feat: add support for multiple languages in the frontend`
   - Bad example: `updated stuff`
   - We suggest the Conventional Commits standard:
     - `feat`: for new features
     - `fix`: for bug fixes
     - `docs`: for documentation
     - `chore`: for maintenance tasks
     - `test`: for adding/adjusting tests

7. **Push the changes to your fork:**
   ```bash
   git push origin feat/your-change-name
   ```

8. **Open a Pull Request (PR)** to the `main` branch of the original repository:
   - Clearly describe what was changed, why, and link the related issue (e.g.: `Closes #123`).
   - If the change affects the user interface, add screenshots or GIFs.

9. **Wait for review** – maintainers may request adjustments. Respond to comments and update the PR if necessary.

10. **After approval**, the PR will be merged (we usually use squash or rebase to keep the history clean).

## Tips for a Quality Contribution
- Clean and readable code – follow PEP 8.
- New or updated tests – ensure the software continues to work.
- Updated documentation – include docstrings and update the README if necessary.
- Respect the existing style – consistency makes maintenance easier.

## Questions?
- Open an issue with the "question" tag.
- Contact us by email: angelasilviane@alumni.usp.br

**We greatly appreciate any contribution!**