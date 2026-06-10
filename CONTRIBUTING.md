# Contributing to REAI

First off, thank you for considering contributing to REAI! It's people like you that make open-source software such a great community to learn, inspire, and create.

## Getting Started

1. **Fork the Repository**
   Fork the REAI repository to your GitHub account and clone it to your local machine.
   ```bash
   git clone https://github.com/YOUR_USERNAME/reai.git
   ```

2. **Branch Naming Convention**
   Create a new branch for your feature, bug fix, or documentation update.
   - `feature/your-feature-name`
   - `fix/bug-you-are-fixing`
   - `docs/documentation-update`

3. **Setting Up the Environment**
   Please ensure you have Python 3.11+ and Node 20+ installed. 
   - **Backend:** Create a virtual environment, install `requirements.txt`, and run `alembic upgrade head`.
   - **Frontend:** Run `npm install` and ensure `npm run lint` passes without errors.

## Making Changes

- Write tests for any new backend functionality inside `backend/tests/`.
- Ensure your code follows the existing style (FastAPI conventions for Python, ESLint standard for React/TS).
- Update the documentation (README, etc.) if your change introduces new behavior or environment variables.

## Submitting a Pull Request

1. Push your branch to your fork.
2. Open a Pull Request against the `main` branch of the upstream repository.
3. Use the provided Pull Request Template to describe your changes.
4. Ensure all CI/CD checks pass.

Thank you for your contribution!
