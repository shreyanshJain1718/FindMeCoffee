from flask import Flask, render_template, request, url_for,jsonify, redirect
import pymongo
import random
import hashlib
from bson.objectid import ObjectId
import pytz
from datetime import datetime
import operator

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = myclient["coffeeHouse"]

app = Flask(__name__)

def getAverageRating(shopId):
    allRatings = db["ratings"]
    shopRatings = allRatings.find({'shop_username': shopId})
    print("shopRatings")
    print(shopRatings)
    totalRating = 0
    ratingCount = 0
    for i in shopRatings:
        rating = int(i['rating'])
        if(rating != -1):
            totalRating += rating
            ratingCount += 1
    if(ratingCount == 0):
        return -1
    else:
        return (round(totalRating/ratingCount, 2), ratingCount)

def hasher(password):
    password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
    return password_hash

@app.route("/", methods=["GET", "POST"])
@app.route("/index.html", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route('/userlogin.html', methods=["GET"])
def userLogin():
    return render_template("userlogin.html")


@app.route("/shoplogin.html", methods=["GET", "POST"])
def shopLogin():
    return render_template("shoplogin.html")


@app.route("/usersignup.html", methods=["GET", "POST"])
def userSignUp():
    return render_template("usersignup.html")


@app.route("/shop_register.html", methods=["GET", "POST"])
def shopRegister():
    return render_template("shop_register.html")


@app.route("/user_log", methods=["GET", "POST"])
def user_log():
    data = dict(request.form)
    print(data)
    username = data["cust_username"][0]
    myquery = {"cust_username": username}
    users = db["userschemas"]
    x = users.find_one(myquery)
    custPasswordHash = hasher(data["cust_password"][0])
    if x is not None:
        if x["cust_password"] == custPasswordHash:
            return render_template("main.html", name=x["cust_name"], id=x["cust_username"])
        elif x["cust_password"] != custPasswordHash:
#            return "<HTML><head><title>Error</title></head><body> <h1>Oops! Wrong password! </h1></body></HTML>"           
            return "<script> alert('Wrong password'); </script>"
    else:
        return "<HTML><head><title>Error</title></head><body> <h1>Account not found! </h1></body></HTML>"

@app.route('/setRating')
def setRating():
    data = dict(request.args)
    print("*** set Rating")
    print(data)
    shopId = data["shop_username"][0]
    custId = data["cust_username"][0]
    rating = data[shopId+"shopRating"][0]
    db["ratings"].update_one({'shop_username':shopId, 'cust_username' : custId}, {'$set': {'rating' : rating }}, upsert=True)
    print("updated")
    return('',204)

@app.route("/shop_log", methods=["GET", "POST"])
def shop_log():
    data = dict(request.form)
    username = data["shop_username"][0]
    myquery = {"shop_username": username}
    shops = db["shopschemas"]
    x = shops.find_one(myquery)
    shopPasswordHash = hasher(data["shop_password"][0])
    if x is not None:
        if x["shop_password"] == shopPasswordHash:
            # find orders
            # find reviews
            ratings = db["ratings"]
            ratings = ratings.find({"shop_username": x["shop_username"]})
            rating = []
            orders = {}

            orders1 = db["orderschemas"]
            orders1 = orders1.find({"shop_username": x["shop_username"],"order_delivered":"false"})
            orders2 = db["orderschemas"]
            orders2 = orders2.find({"shop_username": x["shop_username"],"order_delivered":"false"})
            users = db["userschemas"]
            menus = db["menuschemas"]

            # get reviews from user
            totalRating=0
            count=0
            for i in ratings:
                user = users.find_one({"cust_username": i["cust_username"]})["cust_username"]
                if int(i['rating']) != -1:
                    mydict = {
                        "cust_username": user,
                        "rating": i["rating"]
                    }
                    count+=1
                    totalRating += int(i['rating'])
                    rating.append(mydict)
            if(count != 0):
                avg_reviews = totalRating/count
            else:
                avg_reviews = -1

            # get ratings
            for i in orders1:
                orders[i['cust_username']] = []

            total_cost = {}
            food_prices = db["menudistschemas"]
            for i in orders2:
                myquery = {"food_name": i["food_name"], "shop_username": x['shop_username']}
                food_price = int(food_prices.find_one(myquery)['costPerUnit'])
                orders[i['cust_username']].append(tuple((i['food_name'], i['amount'], food_price)))

            for user in orders:
                total = 0
                for i in orders[user]:
                    myquery = {"food_name": i[0], "shop_username": x['shop_username']}
                    food_price = int(food_prices.find_one(myquery)['costPerUnit'])
                    total += food_price*int(i[1])
                total_cost[user] = total

            return render_template("shop_main.html", name=x['shop_name'], shop_username=x['shop_username'], reviews=ratings, orders=orders, expense=total_cost, avg_review=round(avg_reviews,2) if avg_reviews!= -1 else avg_reviews)

        elif x["shop_password"] != shopPasswordHash:
            return "<HTML><head><title>Error</title></head><body> <h1>Oops! Wrong password! </h1></body></HTML>"
    else:
        return "<HTML><head><title>Error</title></head><body> <h1>Account not found! </h1></body></HTML>"


@app.route("/user_register", methods=["GET", "POST"])
def register():
    data = dict(request.form)
    mydict = {
        "cust_username": data['cust_username'][0],
        "cust_name": data['cust_name'][0],
        "cust_email": data['cust_email'][0],
        "cust_password": hasher(data['cust_password'][0])
    }
    jerry = {"cust_username": data['cust_username'][0]}
    col = db["userschemas"]
    x = col.find_one(jerry)
    if x is None:
        col.insert_one(mydict)
        print("User successfully created!")
        return redirect("userlogin.html")
    else:
        return "<HTML><head><title>Error</title></head><body> <h1>Username already exists! </h1></body></HTML>"


@app.route("/shop_signup", methods=["GET", "POST"])
def shop_register():
    data = dict(request.form)
    print("*** shop signup")
    print(data)
    mydict = {
    "shop_username": data['shop_username'][0],
    "shop_name": data['shop_name'][0],
    "shop_password": hasher(data['shop_password'][0]),
    "shop_mail": data['shop_email'][0],
    "shop_openTime": data['shop_opentime'][0],
    "shop_closeTime": data['shop_closetime'][0],
    "shop_location":  {
                       "shop_loc_longitude": int(data['shop_loc_longitude'][0]),
                       "shop_loc_latitude": int(data['shop_loc_lattitude'][0])
               },
    "shop_address": data['shop_address'][0]
}
    jerry = {"shop_username": data['shop_username'][0]}
    col = db["shopschemas"]
    x = col.find_one(jerry)
    if x is None:
        col.insert_one(mydict)
        print("Shop successfully created!")
        return redirect("/shoplogin.html")
    else:
        return "<HTML><head><title>Error</title></head><body> <h1>Shop-ID already exists! </h1></body></HTML>"


@app.route("/nearest", methods=["GET", "POST"])
def get_nearest():
    currentLoc_lat = random.randint(1, 15)
    currentLoc_long = random.randint(1, 15)
    data = dict(request.form)
    print(data)
    username = data['cust_username'][0]
    print(username)
    col = db["shopschemas"]
    x = col.find()
    metaDataArray = []
    distanceArray = []

    for i in x:
        dist = abs(i["shop_location"]["shop_loc_latitude"]-currentLoc_lat) + abs(i["shop_location"]["shop_loc_longitude"]-currentLoc_long)
        distanceArray.append(dist)
        rating = db["ratings"]
        rating = rating.find_one({"shop_username": i["shop_username"], "cust_username": username})
        if(rating is None):
            rating = -1
        else:
            rating = rating['rating']
        i["userRating"] = rating
        avgRatingData = getAverageRating(i["shop_username"])
        i["avgRating"] = avgRatingData[0]
        i["ratingCount"] = avgRatingData[1]
        metaDataArray.append(i)
        print("*** nearest")
        print(i)
    for i in range(len(distanceArray)):
        for j in range(len(distanceArray)):
         if distanceArray[i] > distanceArray[j]:
            temp = distanceArray[i]
            distanceArray[i] = distanceArray[j]
            distanceArray[j] = temp
            temp = metaDataArray[i]
            metaDataArray[i] = metaDataArray[j]
            metaDataArray[j] = temp 

    return render_template("shop_list.html", shops=metaDataArray, by=username)


@app.route("/best", methods=["GET", "POST"])
def get_best():
    data = dict(request.form)
    print(data)
    username = data['cust_username'][0]
    col = db['ratings']
    print(list(col.find()))
    best = list(col.group(["shop_username"], {}, {"count": 0}, "function(o, p){p.count++}" ))
    shop_rates = {}
    for i in best:
        print(i)
        shop_rates[i['shop_username']] = i['count']

    sorted_by_value = sorted(shop_rates.items(), key=lambda kv: kv[1])[::-1]
    shops = []
    tel = db['shopschemas']
    for i in sorted_by_value:
        shop = tel.find_one({"shop_username": i[0]})
        rating = db["ratings"]
        rating = rating.find_one({"shop_username": i[0], "cust_username": username})
        if(rating is None):
            rating = -1
        else:
            rating = rating['rating']
        shop["userRating"] = rating
        shop["avgRating"] = getAverageRating(i[0])[0]
        shop["ratingCount"] = getAverageRating(i[0])[1]
        shops.append(shop)

    return render_template("shop_list.html", shops=shops, by=username)


@app.route("/diversity", methods=["GET", "POST"])
def get_diversity():
    data = dict(request.form)
    print(data)
    col = db["menudistschemas"]
    username = data['cust_username'][0]
    diversity = list(col.group(["shop_username"], {}, {"count":0},"function(o, p){p.count++}" ))
    print(diversity)
    food_length = {}
    shops = []

    for i in diversity:
        print(i)
        food_length[i['shop_username'][0]] = i['count']

    sorted_by_value = list(food_length.items())
    sorted_by_value.sort(key=operator.itemgetter(1))
    sorted_by_value = sorted_by_value[::-1]
    print("***sorted by value")
    print(sorted_by_value)
    print("*** index 1")
    print(list(food_length.items()))
    tel = db['shopschemas']
    for i in sorted_by_value:
        shop = tel.find_one({"shop_username": i[0]})
        rating = db["ratings"]
        rating = rating.find_one({"shop_username": i[0], "cust_username": username})
        if(rating is None):
            rating = -1
        else:
            rating = rating['rating']
        shop["userRating"] = rating
        shop["avgRating"] = getAverageRating(i[0])[0]
        shop["ratingCount"] = getAverageRating(i[0])[1]
        shops.append(shop)

    return render_template("shop_list.html", shops=shops, by=username)


@app.route("/shopmenu.html", methods=["GET", "POST"])
def regA():
    data = dict(request.form)
    shop_id = data['shop_username'][0]
    col = db["menuschemas"]
    foods = col.find()
    food_list = []
    for i in foods:
        food_list.append(i['food_name'])
    return render_template("shop_menu.html", food_items=food_list, by=shop_id)


@app.route("/logout", methods=["GET", "POST"])
def rift():
    return redirect("/index.html")


@app.route("/add_food", methods=["GET", "POST"])
def add_food():
    data = dict(request.form)
    print(data)
    col0 = db["menudistschemas"]
    col2 = db["menuschemas"]

    if "special" in data.keys():
        food = data['special'][0]
        by = data['shop_username']
        at = data['price'][0]
        mydict = {
            "shop_username": by,
            "food_name": food,
            "costPerUnit": at
        }
        adder = {"food_name": food}
        col0.insert_one(mydict)
        col2.insert_one(adder)
    else:
        foods = data['fooz']
        by = data['shop_username']
        at = data['price']
        z = []
        for i in foods:
            mydict = {
                "shop_username": by,
                "food_name": i,
                "costPerUnit": at[foods.index(i)]
            }
            z.append(mydict)
        col0.insert_many(z)
    return ('', 204)



@app.route("/return_main_user", methods=["GET", "POST"])
def getBack():
    data = dict(request.form)
    print(data)
    username = data['cust_username'][0]
    myquery = {"cust_username": username}
    col = db["userschemas"]
    x = col.find_one(myquery)
    return render_template("main.html", name=x["cust_name"], id=x["cust_username"])


@app.route("/order_food", methods=["GET", "POST"])
def order_food():
    data = dict(request.form)
    print(data)
    username = data['cust_username'][0]
    shop_id = data['shop_username'][0]
    col = db["menudistschemas"]
    my_query = {"shop_username": shop_id}
    x = col.find(my_query)
    food_prep = []
    for i in x:
        food_prep.append(tuple((i["food_name"], i['costPerUnit'])))
    return render_template("order.html", by=username, at=shop_id, foods=food_prep)


@app.route("/place_order", methods=["GET", "POST"])
def place_order():
    data = dict(request.form)
    print(data)
    username = data['cust_username'][0]
    shop_id = data['shop_username'][0]
    foods = data['items']
    amount = data['quantity']
    col = db['orderschemas']
    add = []
    for i in range(len(foods)):
        if int(amount[i])>0:
            mydict = {
                "cust_username":username,
                "shop_username":shop_id,
                "food_name": foods[i],
                "amount": amount[i],
                "transaction_date": datetime.now(pytz.utc),
                "order_delivered": "false"
            }
            print(mydict)
            add.append(mydict)
    print(add)
    col.insert_many(add)
    print("orders created successfully.")
    z = db['userschemas']
    iser = z.find_one({"cust_username": username})
    return render_template("main.html",name=iser['cust_name'],id=username)


if __name__ == '__main__':
    app.run(debug=True)
