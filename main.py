from fastapi import FastAPI
from routers import todos
import models
from database import engine
app = FastAPI()


models.Base.metadata.create_all(bind=engine)



# @app.get("/")
# def home_page():
#     return {'message':'all ok'}

app.include_router(todos.router)