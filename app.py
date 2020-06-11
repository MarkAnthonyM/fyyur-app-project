#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
import datetime
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import os
import sys
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db, compare_type=True)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

# TODO: Understand how to use associated table as compared to Modeled table
# shows = db.Table('shows',
#   db.Column('venue_id', db.Integer, db.ForeignKey('venue.id'), primary_key=True),
#   db.Column('artist_id', db.Integer, db.ForeignKey('artist.id'), primary_key=True),
#   db.Column('date', db.String(120))
# )

class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    past_show_count = db.Column(db.Integer, nullable=False)
    upcoming_show_count = db.Column(db.Integer, nullable=False)
    shows = db.relationship('Show', backref=db.backref('venues', lazy=True))

    def __repr__(self):
      return '<Venue Id: %s, Venue Name: %s>' % (self.id, self.name)

class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(120))
    past_show_count = db.Column(db.Integer, nullable=False)
    upcoming_show_count = db.Column(db.Integer, nullable=False)
    shows = db.relationship('Show', backref=db.backref('artists'), lazy=True)

    def __repr__(self):
      return '<Artist Id: %s, Artist Name: %s>' % (self.id, self.name)

# Association model. Bridges relationship between Venue and Artist 
class Show(db.Model):
  __tablename__ = 'shows'

  id = db.Column(db.Integer, autoincrement=True, primary_key=True)
  venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), primary_key=True)
  artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'), primary_key=True)
  date = db.Column(db.String(120))

  def __repr__(self):
    return '<Show Id: %s, Show date: %s>' % (self.id, self.date)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

# Check against show date and return true/false based on whether show is upcoming 
def upcomingcheck(value):
  now = datetime.utcnow()
  show_date = dateutil.parser.parse(value)
  return now < show_date

app.jinja_env.filters['datetime'] = format_datetime
app.jinja_env.filters['upcomingcheck'] = upcomingcheck

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # Query database and store Venue information to be displayed
  locations = []
  area_data = Venue.query.distinct(Venue.city, Venue.state).all()
  for venue in area_data:
    area = {
      'city': venue.city,
      'state': venue.state,
      'venues': [Venue.query.filter_by(city=venue.city).all()] 
    }
    locations.append(area)

  return render_template('pages/venues.html', areas=locations);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # Store search string
  search_term=request.form.get('search_term', '')

  venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()
  
  response={
    "count": len(venues),
    "data": []
  }

  for venue in venues:
    venue_dictionary = {
      'id': venue.id,
      'name': venue.name,
    }

    response['data'].append(venue_dictionary)

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  data = Venue.query.get(venue_id)

  # Check for valid url/database record. Redirects to 404 error page on invalid url.  
  if data == None:
    return abort(404)

  # check show dates against current date and store aggrate values
  current_time = datetime.utcnow()
  upcoming_show = Show.query.filter_by(venue_id=venue_id).filter(Show.date > str(current_time)).count()
  past_show = Show.query.filter_by(venue_id=venue_id).filter(Show.date < str(current_time)).count()
  data.upcoming_show_count = upcoming_show
  data.past_show_count = past_show

  data.genres = data.genres.split(",")

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # Attempt to request form data and use to contruct venue db record
  try:
    form_data = request.form
    if form_data['seeking_talent'] == 'True':
      validate_bool = True
    else:
      validate_bool = False
    
    genres_string = ",".join(form_data.getlist('genres'))
    
    venue = Venue(
      name=form_data['name'],
      city=form_data['city'].capitalize(),
      state=form_data['state'],
      address=form_data['address'],
      phone=form_data['phone'],
      image_link=form_data['image_link'],
      facebook_link=form_data['facebook_link'],
      website_link=form_data['website_link'],
      seeking_talent=validate_bool,
      seeking_description=form_data['seeking_description'],
      genres=genres_string,
      past_show_count=0,
      upcoming_show_count=0
    )
    
    db.session.add(venue)
    db.session.commit()
    
    # on successful db insert, flash success
    flash('Venue ' + request.form['name'] + ' was successfully listed!')

  except:
    db.session.rollback()
    print(sys.exe_info())
    abort(500)
    flash('Venue ' + request.form['name'] + ' encountered error during submission!')
  finally:
    db.session.close()
    
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # Display all artist in database
  data = Artist.query.all()
  
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # Store search string and use to search for specific artists
  search_term=request.form.get('search_term', '')

  artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()
  
  response={
    "count": len(artists),
    "data": []
  }

  for artist in artists:
    artist_dictionary = {
      'id': artist.id,
      'name': artist.name,
    }

    response['data'].append(artist_dictionary)
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  data = Artist.query.get(artist_id)

  # Check for valid url/database record. Redirects to 404 error page on invalid url.  
  if data == None:
    return abort(404)

  # check show dates against current date and store aggrate values
  current_time = datetime.utcnow()
  upcoming_show = Show.query.filter_by(artist_id=artist_id).filter(Show.date > str(current_time)).count()
  past_show = Show.query.filter_by(artist_id=artist_id).filter(Show.date < str(current_time)).count()
  data.upcoming_show_count = upcoming_show
  data.past_show_count = past_show
  
  data.genres = data.genres.split(",")
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist={
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
  }
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
  }
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # attempt to request form data and use to create artist object record
  try:
    form_data = request.form

    if form_data['seeking_venue'] == 'True':
      validate_bool = True
    else:
      validate_bool = False
    
    genres_string = ",".join(form_data.getlist('genres'))
    
    artist = Artist(
      name = form_data['name'],
      city = form_data['city'].capitalize(),
      state = form_data['state'],
      phone = form_data['phone'],
      genres = genres_string,
      image_link = form_data['image_link'],
      facebook_link = form_data['facebook_link'],
      website_link = form_data['website_link'],
      seeking_venue = validate_bool,
      seeking_description = form_data['seeking_description'],
      past_show_count = 0,
      upcoming_show_count = 0,
    )

    db.session.add(artist)
    db.session.commit()

    # on successful db insert, flash success
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    print(sys.exe_info())
    abort(500)
    flash('Artist ' + request.form['name'] + ' encountered error during submission!')

  finally:
    db.session.close() 

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  data=[]
  shows = Show.query.all()
  current_date = datetime.utcnow()

  for show in shows:
    data.append({
      'venue_id': show.venue_id,
      'venue_name': show.venues.name,
      'artist_id': show.artist_id,
      'artist_name': show.artists.name,
      'artist_image_link': show.artists.image_link,
      'start_time': show.date,
      'past_show': show.date < str(current_date)
    })
  
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # attempt to use form data to create new show listing
  try:
    form_data = request.form

    venue = Venue.query.get(form_data['venue_id'])
    artist = Artist.query.get(form_data['artist_id'])
    date = request.form['start_time']

    shows = Show(venue_id=venue.id, artist_id=artist.id, date=date)

    db.session.add(shows)
    db.session.commit()

    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    print(sys.exe_info())
    abort(500)
    flash('Show failed to list!')
  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
# if __name__ == '__main__':
#     app.run()

# Or specify port manually:

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)

