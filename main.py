from fastapi import FastAPI
from routers import todos,users
import models
from database import engine
app = FastAPI()


models.Base.metadata.create_all(bind=engine)



# @app.get("/")
# def home_page():
#     return {'message':'all ok'}
app.include_router(users.router)
app.include_router(todos.router)