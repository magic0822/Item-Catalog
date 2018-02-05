from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import User, Category, Item, Base

engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

user1 = User(name='alexbrown', email='alexbrown@gg.com')
user2 = User(name='bobnaz', email='bobnaz@gg.com')
user3 = User(name='charliedavid', email='charliedav@gg.com')
session.add(user1)
session.add(user2)
session.add(user3)
session.commit()
# new catalog
category1 = Category(name="Camera", user=user1)
session.add(category1)
session.commit()
# new item
item1 = Item(name="Camera Drones",
             description="A quadcopter, also called a quadrotor helicopter or quadrotor, is a multirotor helicopter that is lifted and propelled by four rotors.",
             category=category1, user=user3)
session.add(item1)
session.commit()
# new item
item2 = Item(name="DSLR Cameras",
             description="A digital single-lens reflex camera is a digital camera that combines the optics and the mechanisms of a single-lens reflex camera with a digital imaging sensor.",
             category=category1, user=user3)
session.add(item2)
session.commit()

# new catalog
category2 = Category(name="Cell Phones", user=user2)
session.add(category2)
session.commit()
# new item
item3 = Item(name="Smart Phone", description="Smart like human but price.", category=category2, user=user1)
session.add(item3)
session.commit()
# new item
item4 = Item(name="Flip Phone", description="Not smart but classic and fast.", category=category2, user=user2)
session.add(item4)
session.commit()
