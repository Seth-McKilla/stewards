import json
import math
import requests
import pandas as pd
from flask import Flask, request
from flask.templating import render_template
import time
from datetime import date, datetime
from dotenv import load_dotenv
import os
import multiprocessing.pool


load_dotenv()


def get_voters(tup_arg):
    pid, query, url = tup_arg
    p_query = query.replace("proposal_id", pid)
    r = requests.post(url, json={"query": p_query})
    votes = r.json()["data"]["votes"]
    return [v["voter"].lower() for v in votes]


def tally(address):
    while True:
        try:
            r = requests.get(f"https://gtcselenium.herokuapp.com/?a={address}")
            return float(r.json()["Total_participation_rate"].strip("%"))

        except Exception as e:
            print(e)
            continue

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
            voting_participation.append(0.00)

        elif list(r.json().keys())[0] == "message":
            voting_participation.append(0.00)

        else:
            url = "https://api.boardroom.info/v1/voters/" + str(result["address"][i])
            res = requests.get(url)
            userVotesCast = res.json()["data"]["protocols"][0]["totalVotesCast"]
            voting_participation.append(math.ceil((userVotesCast / totalVotes) * 100))

    df2 = pd.DataFrame(voting_participation, columns=["voteparticipation"])
    df3 = pd.concat([result, df2], axis=1)

    l1 = []
    for i in df3["workstream_short"]:
        if str(i) == "nan":
            a1 = "-"
            l1.append(a1)
            print('Replace this!')
        elif str(i) == "MMM":
            l1.append("Merch, Memes, Marketing")
        elif str(i) == "PGF":
            l1.append("Public Goods Funding")
        elif str(i) == "MC":
            l1.append("Moonshot Collective")
        elif str(i) == "DG":
            l1.append("Decentralize Gitcoin")
        else:
            l1.append("Fraud Detection & Defense")

    df_workstream = pd.DataFrame(l1, columns=["workstream"])
    print('The workstreams are: ',df_workstream['workstream'])
    df3 = df3.drop("workstream_short", 1)
    df4 = pd.concat([df3, df_workstream], axis=1)

    # f_values
    df = pd.read_csv("stewards.csv")
    f_value_list = []
    post_count_1 = requests.get(
        "https://gov.gitcoin.co/u/" + df["username"][0] + ".json",
        headers={
            "Api-key": os.environ.get("DISCOURSE_API_KEY"),
            "Api-Username": os.environ.get("DISCOURSE_API_USERNAME"),
        },
    )

    datetime_object = datetime.strptime(str(df["steward_since"][0]), "%Y-%m-%d")
    date1_1 = date(
        int(datetime_object.strftime("%Y")),
        int(datetime_object.strftime("%m")),
        int(datetime_object.strftime("%d")),
    )
    today = date.today()
    date2_1 = date(
        int(today.strftime("%Y")), int(today.strftime("%m")), int(today.strftime("%d"))
    )
    days_1 = abs(date1_1 - date2_1).days
    week_since_steward_1 = int(days_1 / 7)
    #print(post_count_1.json())
    post_count_value = 0
    try:
        post_count_value = int(post_count_1.json()["user"]["post_count"])
    except Exception as e:
        print(e)
    f_value_1 = post_count_value / week_since_steward_1
    if round(float(f_value_1), 2) == round(float(df["f_value"][0]), 2):
        f_value_list = list(df["f_value"])
    else:
        posts_count_value = 0
        for username in df["username"]:
            # print(username)
            s = requests.get(
                "https://gov.gitcoin.co/u/" + username + ".json",
                headers={
                    "Api-key": os.environ.get("DISCOURSE_API_KEY"),
                    "Api-Username": os.environ.get("DISCOURSE_API_USERNAME"),
                },
            )
            try:
                posts_count_value = int(s.json()["user"]["post_count"])
            except Exception as e:
                print(e)
            f_value_list.append(posts_count_value)

    weeks_since_steward_list = []
    df_date = df["steward_since"]
    for i in df_date:
        datetime_object = datetime.strptime(str(i), "%Y-%m-%d")
        date1 = date(
            int(datetime_object.strftime("%Y")),
            int(datetime_object.strftime("%m")),
            int(datetime_object.strftime("%d")),
        )
        today = date.today()
        date2 = date(
            int(today.strftime("%Y")),
            int(today.strftime("%m")),
            int(today.strftime("%d")),
        )
        days = abs(date1 - date2).days
        weeks_since_steward_list.append(int(days / 7))

    f_value = [i / j for i, j in zip(f_value_list, weeks_since_steward_list)]
    f_value_final = []
    for i in f_value:
        if float(i) < 1.5:
            f_value_final.append(i)
        else:
            f_value_final.append(1.5)
    print("f_values are:",f_value_final)

    # v_values

    # Snapshot API
    space_alias = "gitcoindao.eth"

    query_proposal_closed = """query Proposals {
    proposals (
        first: 10000,
        skip: 0,
        where: {
        space_in:"space_name",
        state: "closed"
        },
        orderBy: "created",
        orderDirection: desc
    ) {
        id
        title
        body
        choices
        start
        end
        snapshot
        state
        author
        space {
        id
        name
        }
    }
    } """.replace(
        "space_name", space_alias
    )

    url = "https://hub.snapshot.org/graphql?"
    r1 = requests.post(url, json={"query": query_proposal_closed})
    # print(r1.json()['data']['proposals'][0]['id'])
    print('proposals')
    print(len(r1.json()['data']['proposals']))

    # Proposal ID
    p_id_list = []

    for i in range(len(r1.json()["data"]["proposals"])):
        p_id_list.append(r1.json()["data"]["proposals"][i]["id"])

    query = """query Votes {
        votes (
        first: 1000
        skip: 0
        where: {
            proposal: "proposal_id"
        }
        orderBy: "created",
        orderDirection: desc
        ) {
        id
        voter
        created
        proposal {
            id
        }
        choice
        space {
            id
        }
        }
    } """

    url = "https://hub.snapshot.org/graphql?operationName=Votes"

    voter_presence = dict()

    arg_list = [(pid, query, url) for pid in p_id_list]
    multipool = multiprocessing.pool.ThreadPool(processes=50)
    list_of_voters = multipool.map(get_voters, arg_list, chunksize=1)

    for voters in list_of_voters:
        for voter in voters:
            if voter in voter_presence:
                voter_presence[voter] += 1
            else:
                voter_presence[voter] = 1

    print(voter_presence)

    csv_voter_presence = dict()

    csv_voters = [v.lower() for v in df["address"].values]
    for voter in csv_voters:
        if voter in voter_presence:
            # print(voter,':',voter_presence[voter])
            csv_voter_presence[voter] = voter_presence[voter]
        else:
            # print(voter,': 0')
            csv_voter_presence[voter] = 0

    snapshot_api_percentage_list = []

    for i in range(len(csv_voters)):
        # print(str(i+1)+') '+csv_voters[i]+' : '+str(csv_voter_presence[csv_voters[i]]/len(p_id_list)))
        snapshot_api_percentage_list.append(
            round(float(csv_voter_presence[csv_voters[i]] / len(p_id_list)), 2)
        )

    # Tally API

    # tally_api_percentage_list = []

    #address_1 = tally(df['address'][0])
    #print('This is address 1:', address_1)

    r_1 = requests.get("https://gtcselenium.herokuapp.com/?a=" + df["address"][0])

    some_lovely_value = 0
    try:
        some_lovely_value = r_1.json()["Total_participation_rate"].strip("%")
    except:
        some_lovely_value = 0

    if type(some_lovely_value) != float:
        # print("This works")
        tally_paricipation_rate = df["Tally_participation_rate"]
        # print(tally_paricipation_rate)

    elif tally(df["address"][0]) == float(df["Tally_participation_rate"][0]):
        # print("This works")
        tally_paricipation_rate = df["Tally_participation_rate"]
        # print(tally_paricipation_rate)

    else:
        df["Tally_participation_rate"] = zip(*df.address.map(tally))
        df.to_csv("stewards.csv", index=False)
        # print(tally(address_1))

    v_value = [
        round((2.2 * i + 1.5 * j) / 2, 2)
        for i, j in zip(snapshot_api_percentage_list, tally_paricipation_rate)
    ]
    # print("v value is:", v_value)

    # w_values
    w_values = df["w_value"]

    # print("w value is:", w_values)

    health_score = [
        (round(i * j, 1) * 10 + k) for i, j, k in zip(f_value, v_value, w_values)
    ]
    health_score_final = []
    for i in health_score:
        if i <= 10.0:
            health_score_final.append(int(i))
        else:
            health_score_final.append(10)

    df5 = pd.DataFrame(health_score_final, columns=["Health Score"])
    print("Health Score is:",df5["Health Score"])
    df6 = pd.concat([df4, df5], axis=1)
    # print('This is df6:',df6)
    # Forum Post Count
    s_1 = requests.get(
        "https://gov.gitcoin.co/u/" + df["username"][0] + ".json",
        headers={
            "Api-key": os.environ.get("DISCOURSE_API_KEY"),
            "Api-Username": os.environ.get("DISCOURSE_API_USERNAME"),
        },
    )
    #print(s_1.json())
    #print(50*'-')
    left_compare = 0
    try:
        left_compare = s_1.json()["user"]["post_count"]
    except Exception as e:
        print(e)
    if left_compare == df["forum_post_count_base"][0]:
        forum_post_count_list = list(df["forum_post_count_base"])
        # print(forum_post_count_list)
    else:
        forum_post_count_list = []
        for username in df["username"]:
            # print(username)
            s = requests.get(
                "https://gov.gitcoin.co/u/" + username + ".json",
                headers={
                    "Api-key": os.environ.get("DISCOURSE_API_KEY"),
                    "Api-Username": os.environ.get("DISCOURSE_API_USERNAME"),
                },
            )
            try:
                forum_post_count_list.append(s.json()["user"]["post_count"])
            except Exception as e:
                print(e)
                forum_post_count_list.append(0)
            print(f'forum posts : {forum_post_count_list}')
            time.sleep(1)
        df["forum_post_count"] = pd.DataFrame(forum_post_count_list)
        df.to_csv("stewards.csv", index=False)
    df7 = pd.DataFrame(forum_post_count_list, columns=["forum_post_count"])
    print("forum_post_count is:",df7["forum_post_count"])
    df8 = pd.concat([df6, df7], axis=1)

    df8["json"] = df8.to_json(orient="records", lines=True).splitlines()
    for i in range(len(stewards_data["address"])):
        res = json.loads(df8["json"][i])
        json_list.append(res)
    # print(json_list[0])
    print('preprocess done')
    return json_list


initial_list = preprocess()


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        data = [x for x in request.form.values()]

        if data[0] == "name":
            if data[1] == "True":
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list, key=lambda k: k["name"], reverse=False
                    ),
                )
            else:
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list, key=lambda k: k["name"], reverse=True
                    ),
                )

        if data[0] == "date":
            if data[1] == "True":
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list, key=lambda k: k["steward_since"], reverse=False
                    ),
                )
            else:
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list, key=lambda k: k["steward_since"], reverse=True
                    ),
                )

        if data[0] == "voteparticipation":
            if data[1] == "True":
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list,
                        key=lambda k: k["voteparticipation"],
                        reverse=False,
                    ),
                )
            else:
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list, key=lambda k: k["voteparticipation"], reverse=True
                    ),
                )

        if data[0] == "votingweight":
            if data[1] == "True":
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list,
                        key=lambda k: float(k["votingweight"]),
                        reverse=False,
                    ),
                )
            else:
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list,
                        key=lambda k: float(k["votingweight"]),
                        reverse=True,
                    ),
                )

        if data[0] == "statement_post_id":
            if data[1] == "True":
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list,
                        key=lambda k: k["statement_post_id"],
                        reverse=False,
                    ),
                )
            else:
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list, key=lambda k: k["statement_post_id"], reverse=True
                    ),
                )

        if data[0] == "health":
            if data[1] == "True":
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list,
                        key=lambda k: k["Health Score"],
                        reverse=False,
                    ),
                )
            else:
                return render_template(
                    "index.html",
                    stewards=sorted(
                        initial_list, key=lambda k: k["Health Score"], reverse=True
                    ),
                )

    else:
        return render_template("index.html", stewards=initial_list)
