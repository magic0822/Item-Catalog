#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify, \
    session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from database_setup import Base, Category, Item, User
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
import functions as fun

app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Google+ client id and application name
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Item catalog"


# Create anti-forgery state token
@app.route('/login')
def show_login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = fun.get_user_id(login_session['email'])
    if not user_id:
        user_id = fun.add_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    flash("Welcome, you are now logged in as %s." % login_session['username'])
    flash("success")
    print("done!")
    return output


@app.route('/gdisconnect')
def gdisconnect():
    """Log out from google+."""
    access_token = login_session['access_token']
    print('In gdisconnect access token is %s', access_token)
    print('User name is: ')
    print(login_session['username'])
    if access_token is None:
        print('Access Token is None')
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = ('https://accounts.google.com/o/oauth2/revoke?token=%s'
           % login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is ')
    print(result)
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


# Check logged in users
@app.context_processor
def logged_in_users():
    return dict(user_logged_in=fun.logged_in_user())


@app.route('/')
@app.route('/catalogs/')
def public():
    return render_template(
        'public.html',
        categories=fun.categories(),
        latest_items=fun.items(count='latest'),
        show_categories=True)


@app.route('/catalogs/<category_name>/')
@app.route('/catalogs/<category_name>/items/')
def show_category(category_name):
    return render_template(
        'show_category.html',
        category_name=category_name,
        categories=fun.categories(),
        filtered_items=fun.items(category_name=category_name),
        show_categories=True)


@app.route('/catalogs/<category_name>/items/<item_name>/')
def show_item(category_name, item_name):
    return render_template('show_item.html', item=fun.item(item_name, category_name))


@app.route('/catalogs/<category_name>/items/new/', methods=['GET', 'POST'])
def add_item(category_name):
    if not fun.logged_in_user():
        flash("Please login.")
        return redirect('login')

    if request.method == 'POST':
        add_item_name = request.form['name'].strip().lower()
        add_item_description = request.form['description'].strip()
        if add_item_name and add_item_description:
            try:
                fun.item(name=add_item_name, category_name=category_name)
                errors = {
                    'name': 'Duplicate item name!'}
                params = {
                    'name': add_item_name,
                    'description': add_item_description}
                return render_template(
                    'add_item.html',
                    category_name=category_name,
                    errors=errors,
                    params=params)
            except:
                add_item = Item(
                    name=add_item_name,
                    description=add_item_description,
                    category=fun.category(category_name),
                    user=fun.get_user_info(login_session['user_id']))
                session.add(add_item)
                session.commit()
                flash("Item is added.")
                return redirect(
                    url_for(
                        'show_item',
                        category_name=category_name,
                        item_name=add_item_name))
        else:
            errors = {}
            params = {'name': '', 'description': ''}
            if add_item_name:
                params['name'] = add_item_name
            else:
                errors['name'] = "Blank is not allowed!"

            if add_item_description:
                params['description'] = add_item_description
            else:
                errors['description'] = "Blank is not allowed!"

            return render_template(
                'add_item.html',
                category_name=category_name,
                errors=errors,
                params=params)
    else:
        return render_template(
            'add_item.html',
            category_name=category_name,
            params={'name': '', 'description': ''})


@app.route(
    '/catalogs/<category_name>/items/<item_name>/edit/',
    methods=['GET', 'POST'])
def edit_item(category_name, item_name):
    if not fun.logged_in_user():
        flash("Please login!")
        return redirect('login')
    item_to_edit = fun.item(item_name, category_name)
    if request.method == 'POST':
        edited_item_name = request.form['name'].strip().lower()
        edited_item_description = request.form['description'].strip()
        if edited_item_name and edited_item_description:
            item_to_edit.name = edited_item_name
            item_to_edit.description = edited_item_description
            session.add(item_to_edit)
            try:
                session.commit()
                flash("Item is updated.")
                return redirect(
                    url_for(
                        'show_item',
                        category_name=category_name,
                        item_name=edited_item_name))
            except IntegrityError:
                session.rollback()
                errors = {'name': 'Duplicate item name.'}
                params = {'name': edited_item_name,
                          'description': edited_item_description}
                return render_template(
                    'edit_item.html',
                    category_name=category_name,
                    item_name=item_name,
                    errors=errors,
                    params=params)
        else:
            errors = {}
            params = {'name': '', 'description': ''}
            if edited_item_name:
                params['name'] = edited_item_name
            else:
                errors['name'] = "Blank is not allowed."

            if edited_item_description:
                params['description'] = edited_item_description
            else:
                errors['description'] = "Blank is not allowed."

            return render_template('edit_item.html',
                                   category_name=category_name,
                                   item_name=item_name,
                                   errors=errors,
                                   params=params)
    else:
        return render_template(
            'edit_item.html',
            category_name=category_name,
            item_name=item_name,
            params={'name': item_to_edit.name,
                    'description': item_to_edit.description})


@app.route(
    '/catalogs/<category_name>/items/<item_name>/delete/',
    methods=['GET', 'POST'])
def delete_item(category_name, item_name):
    if not fun.logged_in_user():
        flash("Please login.")
        return redirect('login')
    item_to_delete = fun.item(item_name, category_name)
    if request.method == 'POST':
        session.delete(item_to_delete)
        try:
            session.commit()
            flash("Item is deleted.")
            return redirect(
                url_for('show_category', category_name=category_name))
        except:
            session.rollback()
            return "Please try again later."
    else:
        return render_template(
            'delete_item.html',
            category_name=category_name,
            item_name=item_name)


# API for JSON of categories
# @app.route('/catalogs/JSON')
# def categories2JSON():
#     return jsonify(AllCategories=[cat.serialize for cat in fun.categories()])


# API for JSON of items of category
@app.route('/catalogs/<category_name>/items/JSON')
def items2JSON(category_name):
    json_items = fun.items(category_name=category_name)
    return jsonify(CategoryItems=[i.serialize for i in json_items])


# API for JSON of all items
@app.route('/catalogs/<category_name>/items/<item_name>/JSON')
def item2JSON(category_name, item_name):
    json_item = fun.item(item_name, category_name)
    return jsonify(CategoryItem=json_item.serialize)


if __name__ == '__main__':
    app.secret_key = 'secret'
    app.debug = True
    app.run(host='localhost', port=8000)
