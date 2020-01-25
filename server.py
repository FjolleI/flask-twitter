from flask import Flask, render_template, request, redirect, session, flash
from flask_bcrypt import Bcrypt

from mysqlconnection import connectToMySQL
import re

app = Flask(__name__)
app.secret_key = "hidden"
bcrypt = Bcrypt(app)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

@app.route("/")
def landing_page():
    return render_template("index.html")

@app.route("/register_user", methods=['POST'])
def on_register():
    is_valid = True

    if not EMAIL_REGEX.match(request.form['em']):
        is_valid = False
        flash("Invalid email address")

    if request.form['pw'] != request.form['cpw']:
        is_valid = False
        flash("Passwords don't match") 
    
    if not is_valid:
        return redirect("/")
    else:
        #save to db - reg user
        mysql = connectToMySQL('wall_db')
        query = "INSERT INTO user (first_name, last_name, email, password, created_at, updated_at) VALUES (%(fn)s,%(ln)s,%(em)s,%(pw)s,NOW(),NOW())"
        hashed_pw = bcrypt.generate_password_hash(request.form['pw'])
        data = {
            'fn': request.form['fn'],
            'ln': request.form['ln'],
            'em': request.form['em'],
            'pw': hashed_pw,
        }
        results = mysql.query_db(query, data)
        if results:
            session['user_id'] = results

        return redirect("/success")

@app.route("/login_user", methods=['POST'])
def on_login():
    is_valid = True
    if len(request.form['em']) < 1:
        is_valid = False
        flash("Email cannot be blank.")

    mysql = connectToMySQL("wall_db")
    query = "SELECT * FROM user WHERE email=%(em)s"
    data = {'em': request.form['em']}
    result = mysql.query_db(query, data)

    if result:
        user_data = result[0]
        if bcrypt.check_password_hash(user_data['password'],request.form['pw']):
            session['user_id'] = user_data['id_user']
            return redirect("/success")
        else:
            is_valid = False
            flash("Invalid email or password used.")
    else:
        is_valid = False
        flash("Invalid email or password used.")
    
    if not is_valid:
        return redirect("/")  

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/success")
def tweet_landing():

    if 'user_id' not in session:
        return redirect("/")

    # GETTING INFO FOR GREETING
    mysql = connectToMySQL('wall_db')
    query = "SELECT first_name FROM user WHERE id_user = %(id)s"
    data = {'id': session['user_id']}
    result = mysql.query_db(query, data)
    if result:
        user_data = result[0]

    # GET TWEET LIKE COUNT
    mysql = connectToMySQL('wall_db')
    query = "SELECT tweet_id_tweet, COUNT(tweet_id_tweet) AS like_count FROM tweets_users_have_liked GROUP BY tweet_id_tweet"
    like_count = mysql.query_db(query, data)

    # TO GET ALL TWEET DATA
    mysql = connectToMySQL('wall_db')
    query = "SELECT user.first_name, user.last_name, tweet.content, tweet.author, tweet.id_tweet FROM tweet LEFT JOIN user on tweet.author = user.id_user LEFT JOIN tweets_users_have_liked on tweets_users_have_liked.tweet_id_tweet = tweet.id_tweet GROUP BY id_tweet ORDER BY COUNT(tweet_id_tweet) DESC"
    
    all_tweets = mysql.query_db(query) 

    for tweet in all_tweets:
        for count in like_count:
            if count['tweet_id_tweet'] == tweet['id_tweet']:
                tweet['like_count'] = count['like_count']
        if 'like_count' not in tweet:
            tweet['like_count'] = 0
   

    return render_template("tweet_landing.html", user_data=user_data, all_tweets=all_tweets)

@app.route("/write_tweet", methods=["POST"])
def on_tweet_creation():
    is_valid = True

    if len(request.form['tweet_content']) < 5:
        is_valid = False
        flash("Tweet content must be at least 5 chars. long.")

    if is_valid:
        mysql = connectToMySQL('wall_db')
        query = "INSERT INTO tweet (content, author, created_at, updated_at) VALUES (%(cont)s, %(author_id)s, NOW(), NOW())"
        data = {
            'cont': request.form['tweet_content'],
            'author_id': session['user_id']
        }
        mysql.query_db(query, data)

    return redirect("/success")

@app.route("/details/<tweet_id_route>")
def on_details(tweet_id_route):
    mysql = connectToMySQL('wall_db')
    query = "SELECT tweet.id_tweet, tweet.content, tweet.created_at, tweet.updated_at, user.first_name, user.last_name FROM tweet JOIN user ON tweet.author = user.id_user WHERE tweet.id_tweet = %(tweet_id)s"
    data = { 'tweet_id': tweet_id_route }

    results = mysql.query_db(query, data) #False, [], [{}..n]

    if results:
        tweet_data = results[0]

        mysql = connectToMySQL('wall_db')
        query = "SELECT user.id_user, user.first_name, user.last_name, tweets_users_have_liked.user_id_user FROM tweets_users_have_liked JOIN user ON tweets_users_have_liked.user_id_user = user.id_user WHERE tweets_users_have_liked.tweet_id_tweet = %(tweet_id)s"
        data = {
            'tweet_id': tweet_id_route
        }
        user_likes_data = mysql.query_db(query, data)

         # LIKED TWEET IDS FOR LOGGED IN USER
        mysql = connectToMySQL('wall_db')
        query = "SELECT tweet_id_tweet FROM tweets_users_have_liked WHERE user_id_user = %(user_id)s"
        data = { 'user_id': session['user_id' ]}

        # results = mysql.query_db(query, data)
        # liked_tweet_ids = []
        # for data in results:
        #     liked_tweet_ids.append(data['tweet_id_tweet'])

        liked_tweet_ids = [data['tweet_id_tweet'] for data in mysql.query_db(query, data)]

        # TO GET ALL TWEET DATA
        mysql = connectToMySQL('wall_db')
        query = "SELECT user.first_name, user.last_name, tweet.content, tweet.author, tweet.id_tweet FROM tweet JOIN user on tweet.author = user.id_user"
        all_tweets = mysql.query_db(query) 

        mysql = connectToMySQL('wall_db')
        query = "SELECT user.id_user, user.first_name, user.last_name, tweet.content, tweet.author, tweet.id_tweet FROM tweet JOIN user on tweet.author = user.id_user JOIN tweets_users_have_liked on tweets_users_have_liked.tweet_id_tweet = tweet.id_tweet where tweets_users_have_liked.user_id_user=tweet.author and id_tweet=%(tweet_id)s"
        data = {
            'tweet_id': tweet_id_route
        }
        selfliked = mysql.query_db(query, data) 
        
        selflike = []

        for user in user_likes_data:
           
            try:
                if selfliked:
                    if user['id_user'] == selfliked[0]['id_user']:
                        
                        selflike.insert(-1, user)
                    else:
                        selflike.append(user)
            except:
                selflike.append(user)

        return render_template("tweet_detail.html", selflike=selflike, tweet_data=tweet_data, all_tweets=all_tweets, user_likes_data=user_likes_data, liked_tweet_ids=liked_tweet_ids)



        

    else:
        return redirect("/success")

@app.route("/like/<tweet_id_route>")
def on_like(tweet_id_route):
    mysql = connectToMySQL('wall_db')
    query = "INSERT INTO tweets_users_have_liked (user_id_user, tweet_id_tweet) VALUES ( %(user_id)s, %(tweet_id)s)"
    data = {
        'user_id': session['user_id'],
        'tweet_id': tweet_id_route
    } 
    mysql.query_db(query, data)



    return redirect("/success")

@app.route("/unlike/<tweet_id_route>")
def on_unlike(tweet_id_route):
    mysql = connectToMySQL("wall_db")
    query = "DELETE FROM tweets_users_have_liked WHERE user_id_user = %(user_id)s AND tweet_id_tweet = %(tweet_id)s"
    data = {
        'user_id': session['user_id'],
        'tweet_id': tweet_id_route
    }
    mysql.query_db(query, data)
    return redirect("/success")

@app.route("/delete_tweet/<tweet_id_route>")
def on_delete_tweet(tweet_id_route):

    mysql = connectToMySQL('wall_db')
    query = "DELETE FROM tweet WHERE id_tweet = %(tweet_id_query)s"
    data = {'tweet_id_query': tweet_id_route}
    mysql.query_db(query, data)

    return redirect("/success")

@app.route('/process', methods=['post'])
def process():
    if request.form['action'] == "Show":
        return redirect('/details/' + request.form['tweet-id'])

    if request.form['action'] == "Delete":
        return redirect('/delete_tweet/' + request.form['tweet-id'])
    return redirect('/success')


if "__main__" == __name__:
    app.run(debug=True)