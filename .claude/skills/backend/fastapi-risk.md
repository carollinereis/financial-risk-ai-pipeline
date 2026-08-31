# Skill: FastAPI Risk Engine

- Enforce strict typing via Pydantic v2 schemas for all input payloads and response models.
- Separate financial risk calculation logic from FastAPI route handlers (place business logic inside `src/`).
- Use asynchronous route handlers (`async def`) for I/O bound database and model calls.