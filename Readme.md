# Developer Quickstart

1. Clone the repository
2. Launch the Python app:
   - `poetry run python domovoy/manage.py migrate`
   - `poetry run python domovoy/manage.py runserver`
3. Open a new terminal and `cd domovoy_app`
4. Activate node 22 (e.g. `nvm use 22`)
5. `npm i`
6. Sync types from backend: `npm run domovoy-types` (you will need to do this every time the backend schema changes)
7. `npm run dev`