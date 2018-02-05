from flask import session as login_session
from database_setup import Base, Category, Item, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Get user info by user ID
def get_user_info(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Get user ID by email
def get_user_id(email):
    user = session.query(User).filter_by(email=email).one()
    return user.id


# Check user logged in
def logged_in_user():
    return 'username' in login_session


def user_allowed_to_edit(obj):
    return ('user_id' in login_session and
            obj.user_id == login_session['user_id'])


def add_ser(login_session):
    new_user = User(
        name=login_session['username'],
        email=login_session['email'])
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


# Check category by name
def category(category_name):
    return session.query(Category).filter_by(name=category_name).one()


# Check all categories
def categories():
    return session.query(Category).order_by('name')


# Check item by name and its category_name
def item(name, category_name):
    return session.query(Item).filter_by(
        name=name,
        category_id=category(category_name).id).one()


# Check item by params
def items(count='all', category_name=None):
    if count == 'latest':
        return session.query(Item).order_by('id DESC').limit(10)
    elif category_name:
        current_category = category(category_name)
        filtered_items = session.query(Item).filter_by(
            category_id=current_category.id)
        return filtered_items.order_by('name')
    else:
        return session.query(Item).order_by('name')
