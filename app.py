import json
import math
import requests
import pandas as pd
from flask import Flask, request
from flask.templating import render_template

app = Flask(__name__, static_folder="assets")

def preprocess():
    stewards_data = pd.read_csv("stewards.csv")
    voting_power = []
    json_list = []

    for i in stewards_data["address"]:
        url = "https://api.boardroom.info/v1/voters/" + i
        r = requests.get(url)
        if list(r.json().keys())[0] == "message":
            url1 = "https://api.thegraph.com/subgraphs/name/withtally/protocol-gitcoin-bravo-v2"

            add = i

            CRLF = "\\r\\n"
            payload = (
                '{"query":"query ($voterAddress: String!) {'
                + CRLF
                + "  histories {"
                + CRLF
                + "    totalSupply"
                + CRLF
                + "  },"
                + CRLF
                + "  account(id: $voterAddress) {"
                + CRLF
                + "    id"
                + CRLF
                + "    votes"
                + CRLF
                + "    tokenBalance"
                + CRLF
                + "    ballotsCastCount"
                + CRLF
                + "    proposalsProposedCount"
                + CRLF
                + "    percentageOfTotalVotingPower"
                + CRLF
                + "    frequencyOfParticipationTotal"
                + CRLF
                + "    delegationsCurrentlyReceivedCount"
                + CRLF
                + "    frequencyOfParticipationAsActiveVoter"
                + CRLF
                + "  }"
                + CRLF
                + "  delegators: accounts(orderBy: tokenBalance, orderDirection: desc, where: {delegatingTo: $voterAddress}){"
                + CRLF
                + "    id"
                + CRLF
                + "    votes"
                + CRLF
                + "    tokenBalance"
                + CRLF
                + "    ballotsCastCount"
                + CRLF
                + "    proposalsProposedCount"
                + CRLF
                + "    percentageOfTotalVotingPower"
                + CRLF
                + "    frequencyOfParticipationTotal"
                + CRLF
                + "    delegationsCurrentlyReceivedCount"
                + CRLF
                + "    frequencyOfParticipationAsActiveVoter"
                + CRLF
                + "  }"
                + CRLF
                + '}","variables":{"voterAddress":"'
                + add
                + '"}}'
            )
            headers = {"Content-Type": "application/json"}

            response = requests.request("POST", url1, headers=headers, data=payload)
            res = json.loads(response.text)
            if res["data"]["account"] == None:
                voting_power.append(0)
            else:
                power = "{:.2f}".format(
                    float(res["data"]["account"]["percentageOfTotalVotingPower"])
                )
                voting_power.append(power)

        else:
            power = "{:.2f}".format(
                (float(r.json()["data"]["protocols"][0]["lastCastPower"]) / 100000000)
                * 100
            )
            voting_power.append(power)

        df_voting_power = pd.DataFrame(voting_power, columns=["votingweight"])
        result = pd.concat([stewards_data, df_voting_power], axis=1)

    w = requests.get("https://api.boardroom.info/v1/protocols/gitcoin")

    totalVotes = w.json()["data"]["totalProposals"]

    voting_participation = []

    for i in range(len(result["address"])):
        url = "https://api.boardroom.info/v1/voters/" + result["address"][i]
        r = requests.get(url)

        if str(result["votingweight"][i]) == "nan":
            voting_participation.append(0)

        elif list(r.json().keys())[0] == "message":
            voting_participation.append(0)

        else:
            url = "https://api.boardroom.info/v1/voters/" + str(result["address"][i])
            res = requests.get(url)
            userVotesCast = res.json()["data"]["protocols"][0]["totalVotesCast"]
            voting_participation.append(math.ceil((userVotesCast / totalVotes) * 100))

    df2 = pd.DataFrame(voting_participation, columns=["voteparticipation"])
    df3 = pd.concat([result, df2], axis=1)

    df3["json"] = df3.to_json(orient="records", lines=True).splitlines()
    for i in range(len(stewards_data["address"])):
        res = json.loads(df3["json"][i])
        json_list.append(res)

    return json_list

initial_list = preprocess()


def sort_by_key(list):
    return list['name']

def sort_by_date(list):
    return list['steward_since']

def sort_by_part(list):
    return list['voteparticipation']

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        data = [x for x in request.form.values()]

        if data[0] == 'name':
            if data[1] == 'True':
                return render_template("index.html", stewards=sorted(initial_list, key=sort_by_key, reverse=False))
            else: 
                return render_template("index.html", stewards=sorted(initial_list, key=sort_by_key, reverse=True))

        if data[0] == 'date':
            if data[1] == 'True':
                return render_template("index.html", stewards=sorted(initial_list, key=sort_by_date, reverse=False))
            else: 
                return render_template("index.html", stewards=sorted(initial_list, key=sort_by_date, reverse=True))
        
        if data[0] == 'voteparticipation':
            if data[1] == 'True':
                return render_template("index.html", stewards=sorted(initial_list, key=sort_by_part, reverse=False))
            else: 
                return render_template("index.html", stewards=sorted(initial_list, key=sort_by_part, reverse=True))

        if data[0] == 'votingweight':
            if data[1] == 'True':
                return render_template("index.html", stewards=sorted(initial_list, key=lambda k: float(k['votingweight']), reverse=False))
            else: 
                return render_template("index.html", stewards=sorted(initial_list, key=lambda k: float(k['votingweight']), reverse=True))
        
    else:
        return render_template("index.html", stewards=initial_list)
