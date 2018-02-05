from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    name = Column(
        String(250), nullable=False, unique=True
    )
    id = Column(
        Integer, primary_key=True
    )
    email = Column(
        String(250), nullable=False

    )


class Category(Base):
    # table information
    __tablename__ = 'category'
    # mapper
    name = Column(
        String(150), nullable=False
    )
    id = Column(
        Integer, primary_key=True
    )
    user_id = Column(
        Integer, ForeignKey('user.id')
    )
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name, }


class Item(Base):
    # table information
    __tablename__ = 'item'
    # mapper
    name = Column(
        String(50), nullable=False
    )
    id = Column(
        Integer, primary_key=True
    )
    description = Column(String(250))
    category_id = Column(
        Integer, ForeignKey('category.id')
    )
    user_id = Column(
        Integer, ForeignKey('user.id')
    )
    category = relationship(Category)
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description, }


engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)
