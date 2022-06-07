from .database import Base
from sqlalchemy import Column, ForeignKey,Integer,String,DateTime
from sqlalchemy.orm import relationship


class DbUser(Base):
    __tablename__ = "users"

    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True)
    email = Column(String,unique=True)
    password = Column(String)
    items = relationship('DbPost',back_populates='user')


class DbPost(Base):
    __tablename__ = "posts"

    id = Column(Integer,primary_key=True,index=True)
    image_url = Column(String)
    image_url_type = Column(String)
    caption = Column(String)
    timestamp = Column(DateTime)
    user_id = Column(Integer,ForeignKey("users.id"))
    user = relationship('DbUser',back_populates='items')
    


    




