from datetime import datetime, timedelta, timezone
from fastapi import FastAPI,APIRouter,Depends,status,Path,HTTPException
from jose import jwt,JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer
from typing import Annotated
from passlib.context import CryptContext
from models import Users

router = APIRouter(
    prefix='/user',
    tags=['user']
)

SECRET_KEY = 'f78bb45cd23de31c25b06ecfec22b7f3e3050bd78fc8d0ea2fc4bd0b6a66ce04'
ALGORITHM = 'HS256'

bcryt_context = CryptContext(schemes=['bcrypt'],deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='user/token')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
async def get_current_user(token:Annotated[str,Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username = payload.get('sub')
        user_id = payload.get('id')
        user_role = payload.get('role')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Could not validate user')
        return {'username':username,'id':user_id,'role':user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Could not validate user')
    

db_dependency = Annotated[Session,Depends(get_db)]
user_dependency = Annotated[dict,Depends(get_current_user)]

class CreateUserRequest(BaseModel):
    username : str
    email : str
    first_name : str
    last_name : str
    password : str
    role : str
    phone_number : str 
    
class Token(BaseModel):
    access_token : str
    token_type : str

class UserVerification(BaseModel):
    password : str
    new_password : str

def authenticate_user(username:str,password:str,db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcryt_context.verify(password,user.hashed_password):
        return False
    return user


def create_access_token(username:str,user_id:int,role:str,expires_delta:timedelta):
    encode = {'sub':username,'id':user_id,'role':role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp':expires})
    return jwt.encode(encode,SECRET_KEY,algorithm=ALGORITHM)
    

    


@router.get("/single-user",status_code=status.HTTP_200_OK)
async def get_single_user(user:user_dependency,db:db_dependency):
    if user is None:
        raise HTTPException(status_code=404,detail='Authentication failed')
    return db.query(Users).filter(Users.id == user.get('id')).first()

@router.post("/",status_code=status.HTTP_201_CREATED)
async def create_user(db:db_dependency,user_model:CreateUserRequest):
    create_user_model = Users(
        email = user_model.email,
        username = user_model.username,
        first_name = user_model.first_name,
        last_name = user_model.last_name,
        role = user_model.role,
        hashed_password = bcryt_context.hash(user_model.password),
        is_active = True,
        phone_number = user_model.phone_number
    )
    db.add(create_user_model)
    db.commit()


@router.put("/password",status_code=status.HTTP_204_NO_CONTENT)
async def change_password(user:user_dependency,db:db_dependency,user_verification:UserVerification):
    if user is None:
        raise HTTPException(status_code=401,detail="Authentication Failed")
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    if not bcryt_context.verify(user_verification.password,user_model.hashed_password):
        raise HTTPException(status_code=401,detail="Error on password changed")
    user_model.hashed_password = bcryt_context.hash(user_verification.new_password)
    db.add(user_model)
    db.commit()

@router.put("/phonenumber/{phone_number}",status_code=status.HTTP_204_NO_CONTENT)
async def change_phone_number(user:user_dependency,db:db_dependency,phone_number:str):
    if user is None:
        raise HTTPException(status_code=401,detail="Authentication Failed")
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    user_model.phone_number = phone_number
    db.add(user_model)
    db.commit()


@router.post("/token",response_model=Token)
async def login_for_access_token(form_data:Annotated[OAuth2PasswordRequestForm,Depends()],db:db_dependency):
    user = authenticate_user(form_data.username,form_data.password,db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail='Could not validate User')
    token = create_access_token(user.username,user.id,user.role,timedelta(minutes=20))
    return{
        'access_token':token,
        'token_type':'bearer'
    }
    
    
