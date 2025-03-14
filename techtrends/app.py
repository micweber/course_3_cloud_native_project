import sqlite3
import logging
import sys

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort
from datetime import datetime

# Global connection counter
connection_count = 0

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    global connection_count
    connection = sqlite3.connect('database.db')
    connection_count = connection_count + 1
    connection.row_factory = sqlite3.Row
    return connection

# Function to get a post using its ID
def get_post(post_id):
    global connection_count
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    connection_count = connection_count - 1

    return post

# Function to get a post using its ID
def get_post_count():
    global connection_count
    connection = get_db_connection()
    count = connection.execute('SELECT count(*) FROM posts').fetchone()[0]
    connection.close()
    connection_count = connection_count - 1

    return count

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define Healthcheck endpoint
@app.route('/healthz')
def healthcheck():
    db_exist = True
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts")
    except sqlite3.OperationalError as e:
        db_exist = False
    finally:
        if 'conn' in locals():
            conn.close()

    if db_exist:
        response = app.response_class( 
                response=json.dumps({"result":"OK - healthy"}),
                status=200,
                mimetype='application/json'
        )
    else:
        response = app.response_class( 
                response=json.dumps({"result":"ERROR - database error"}),
                status=500,
                mimetype='application/json'
    )
    return response

# Define Metrics endpoint
@app.route('/metrics')
def metrics():
    response = app.response_class(
            response=json.dumps({"db_connection_count": connection_count, "post_count": get_post_count()}),
            status=200,
            mimetype='application/json'
    )
    return response

# Define the main route of the web application 
@app.route('/')
def index():
    global connection_count
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    connection_count = connection_count - 1
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
      app.logger.info('Non-existing article (' + str(post_id) + ') is accessed and a 404 page is returned.')
      return render_template('404.html')
    else:
      app.logger.info('Article "' + str(post['title']) + '" retrieved!')
      return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info('"About Us" page is retrieved.')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    global connection_count
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()
            app.logger.info('Article "' + str(title) + '" created.')

            connection_count = connection_count - 1

            return redirect(url_for('index'))

    return render_template('create.html')

# start the application on port 3111
if __name__ == "__main__":
    ## stream logs to a file
    logging.basicConfig(level=logging.DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)

    # Handler for STDERR (WARNING and higher)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)

    # Format for Logs: "14/03/2025, 14:44:15, Message-Text"
    formatter = logging.Formatter('%d/%m/%Y, %H:%M:%S, %(message)s')

    # add Formatter to handler
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)

    # add Handler to Logger
    app.logger.addHandler(stdout_handler)
    app.logger.addHandler(stderr_handler)

    app.run(host='0.0.0.0', port='3111')
