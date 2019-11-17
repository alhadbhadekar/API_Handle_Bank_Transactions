from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app=Flask(__name__)
api = Api(app) #Initializa this app to be an API

client = MongoClient("mongodb://db:27017")
db = client.BankAPI #Create a DB by name bank API
users = db["Users"] #Create a collection by name Users

def UserExists(username):
    if users.find({"Username":username}).count() == 0:
        return False
    else:
        return True

class Register(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        if UserExists(username):
            retJson = {
                "status": "301",
                "msg": "Invalid Username/ User exixts"
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Own": 0,
            "Debt": 0
        })

        retJson = {
            "status": 200,
            "msg" : "You successfully signed up for the API"
        }
        return jsonify(retJson)

#Helper functions
def verifyPw(username, password):
    if not UserExists(username):
        return False

    hashed_pw = users.find({
        "Username":username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def cashWithUser(username):
    cash = users.find({
        "Username": username
    })[0]["Own"]
    return cash

def debtWithUser(username):
    debt= users.find({
        "Username": username
    })[0]["Debt"]
    return debt

def generateReturnDictionary(status, msg):
    retJson = {
        "status": status,
        "msg" : msg
    }
    return retJson

# ErrorDictonary (status 303, message), True/False
def verifyCredentials(username, password):
    if not UserExists(username):
        return generateReturnDictionary(301, "Invailid Username"), True

    correct_pw = verifyPw(username, password)

    if not correct_pw:
        return generateReturnDictionary(302, "Incorrect Password"), True

    return None, False

def updateAccount(username, balance):
    users.update({
        "Username" : username
    },{
        "$set":{
            "Own": balance
        }
    })

def updateDebt(username, balance):
    users.update({
        "Username": username
    },{
        "$set":{
            "Debt": balance
        }
    })

class Add(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        if money <= 0:
            return jsonify(generateReturnDictionary(304, "The amount entered must be greater than 0"))

        cash = cashWithUser(username)
        money-=1 #Charge 1$ for each transaction
        bank_cash = cashWithUser("BANK")
        updateAccount("BANK", bank_cash + 1)
        updateAccount("username", cash + money)

        return jsonify(generateReturnDictionary(200, "Amount added successfully to the Account"))

class Transfer(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        to = postedData["to"]
        money = postedData["amount"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        cash = cashWithUser(username)

        if cash <=0:
            return jsonify(generateReturnDictionary(304, "You're are out of money"))

        if not UserExists(to):
            return jsonify(generateReturnDictionary(301, "Receiver username is invalid"))

        cash_from = cashWithUser(username)
        cash_to   = cashWithUser(to)
        bank_cash = cashWithUser("BANK")

        updateAccount("BANK", bank_cash + 1) #1$ as transaction fee
        updateAccount(to, cash_to + money - 1)
        updateAccount(username, cash_from-money)

        return jsonify(generateReturnDictionary(200, "Amount Transferred successfully"))


class Balance(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        retJson = users.find({
            "Username": username
        },{
            "Password":0, #Using MongoDB projetions to hide password and id
            "_id":0       #So this will putput json with only username ,Own and debt
        })[0]

        return(retJson)

class TakeLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        cash = cashWithUser(username)
        debt = debtWithUser(username)

        updateAccount(username, cash + money) #Updating user account with previou cash in account + debt money

        updateAccount(username, debt + money) #Updating debt account
        return jsonify(generateReturnDictionary(200, "Loan added to your account"))

class PayLoan(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]
        money    = postedData["amount"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return jsonify(retJson)

        cash = cashWithUser(username)

        if cash < money:
            return jsonify(generateReturnDictionary(303, "Not Enough Cash in your account"))

        debt = debtWithUser(username)
        updateAccount(username, cash-money)
        updateDebt(username, debt - money)

        return jsonify(generateReturnDictionary(200, "Loan Paid"))

api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/takeloan')
api.add_resource(PayLoan, '/payloan')


if __name__=="__main__":
    app.run(host='0.0.0.0')
