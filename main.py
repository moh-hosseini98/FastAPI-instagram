from ast import mod
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException,status
from requests import request
from db.database import get_db
from db import models
from db.database import engine
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError

SECRET_KEY = "1F4D80A352ADBE20E70F71A45709718035784D587F63F43CD0C7765F0F4D90D7"
ALGORITHM = "HS256"

bcrypt_context = CryptContext(schemes=["bcrypt"],deprecated ="auto")

oath2_bearer = OAuth2PasswordBearer(tokenUrl="token",auto_error=False)

def hash_password(password):
    return bcrypt_context.hash(password)

def verify_password(plain_password,hashed_password):
    return bcrypt_context.verify(plain_password,hashed_password)


def create_access_token(username: str,user_id: int,expire_delta: Optional[timedelta] = None):
    to_encode = {"sub":username,"id":user_id}
    if expire_delta:
        expire = datetime.utcnow() + expire_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)   

    to_encode.update({"exp":expire}) 

    return jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)




def get_current_user(token: str = Depends(oath2_bearer)):
    credentials_exception = HTTPException (
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credentials not valid",
        headers={"www-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        if username is None or user_id is None:
            raise credentials_exception

        return {"username":username,"id":user_id}    
    except JWTError:
        raise  credentials_exception  

        


app = FastAPI(debug=True)


class UserIn(BaseModel):
    username: str
    email: str
    password: str

class UserOut(BaseModel):
    username: str
    email: str
    class Config():
        orm_mode = True

# for postdisplay

class User(BaseModel):
    username: str
    class Config():
        orm_mode = True

class PostBase(BaseModel):
    image_url: str
    image_url_type: str
    caption: str
    

class PostDisplay(BaseModel):
    id: int
    image_url: str
    image_url_type: str
    caption: str
    timestamp: datetime
    user: User
    class Config():
        orm_mode = True

class UserAuth(BaseModel):
    id: int
    username: str
    email: str

class CommentIn(BaseModel):
    text: str
    



@app.get("/")
async def root():
    return {"msg":"hello"}

models.Base.metadata.create_all(engine)


@app.post("/users/register",response_model=UserOut)
async def register_user(request: UserIn,db: Session = Depends(get_db)):
    user = models.DbUser(
        username = request.username,
        email = request.email,
        password = hash_password(request.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@app.post("/token")
async def login_for_access_token(login_form: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):
    user = db.query(models.DbUser).filter(models.DbUser.username == login_form.username).first()
    if user is None:
        raise HTTPException(status_code=404,detail="user not found")

    password = verify_password(login_form.password,user.password)

    if not password:
        raise HTTPException(status_code=404,detail="invalid password")

    access_token = create_access_token(user.username,user.id)  

    return {
        "access_token":access_token,
        "token_type": "Bearer"
    }



    



@app.get("/posts",response_model=List[PostDisplay])
def get_all_posts(db: Session = Depends(get_db)):
    return db.query(models.DbPost).all()


@app.post("/create",response_model=PostDisplay)
async def create_post(request: PostBase,db: Session = Depends(get_db),user: dict = Depends(get_current_user)):
    post = models.DbPost(
        caption = request.caption,
        image_url = request.image_url,
        image_url_type = request.image_url_type,
        timestamp = datetime.utcnow(),
        user_id = user.get('id')
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return post

@app.put("/{post_id}")
async def update_post(post_id: int,request: PostBase,user: dict = Depends(get_current_user),db: Session = Depends(get_db)):
    post = db.query(models.DbPost).filter(models.DbPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail = f'post with id {post_id} not found')
    if post.user_id != user.get("id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="just post creator can change")

    post.caption = request.caption
    post.image_url = request.image_url
    post.image_url_type = request.image_url_type

    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "msg":"updated"
    }   

@app.delete("/{post_id}")
async def delete_post(post_id: int,user: dict = Depends(get_current_user),db: Session = Depends(get_db)):
    post = db.query(models.DbPost).filter(models.DbPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail = f'post with id {post_id} not found')
    if post.user_id != user.get("id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail = 'only creator can delete post')

    db.delete(post)
    db.commit()

    return {
        "msg":"POST DELETED!"
    }    


@app.get("/me")
async def user_posts(user: dict = Depends(get_current_user),db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_FORBIDDEN,detail="Credentials not valid",
        headers={"www-Authenticate": "Bearer"})
    posts = db.query(models.DbPost).filter(models.DbPost.user_id == user.get("id")).all()
    return posts

@app.post("/posts/{post_id}/comments")
async def get_comments(post_id:int,request: CommentIn,user: dict = Depends(get_current_user),db: Session = Depends(get_db)):
    post = db.query(models.DbPost).filter(models.DbPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='not found')

    new_comment = models.DbComment(
        text = request.text,
        post_id = post.id,
        username = user.get("username")
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return new_comment




