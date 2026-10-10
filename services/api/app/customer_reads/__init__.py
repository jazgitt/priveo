from fastapi import FastAPI


def register(app: FastAPI) -> None:
    from app.customer_reads.router import router

    app.include_router(router)
