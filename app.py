import json
import requests
import pandas as pd
from flask import Flask
from flask.templating import render_template
app = Flask(__name__, static_folder="assets")

@app.route("/", methods=["GET", "POST"])

def main():

    stewards_data = pd.read_csv('stewards.csv')
    voting_power = []

    for i in stewards_data['address']:
        url = 'https://api.boardroom.info/v1/voters/' + i
        r = requests.get(url)
        if list(r.json().keys())[0] == 'message':
            url1 = 'https://api.thegraph.com/subgraphs/name/withtally/protocol-gitcoin-bravo-v2'

            add = i

            CRLF = '\\r\\n'
            payload='{"query":"query ($voterAddress: String!) {'+CRLF\
            +'  histories {'+CRLF\
            +'    totalSupply'+CRLF\
            +'  },'+CRLF\
            +'  account(id: $voterAddress) {'+CRLF\
            +'    id'+CRLF\
            +'    votes'+CRLF\
            +'    tokenBalance'+CRLF\
            +'    ballotsCastCount'+CRLF\
            +'    proposalsProposedCount'+CRLF\
            +'    percentageOfTotalVotingPower'+CRLF\
            +'    frequencyOfParticipationTotal'+CRLF\
            +'    delegationsCurrentlyReceivedCount'+CRLF\
            +'    frequencyOfParticipationAsActiveVoter'+CRLF\
            +'  }'+CRLF\
            +'  delegators: accounts(orderBy: tokenBalance, orderDirection: desc, where: {delegatingTo: $voterAddress}){'+CRLF\
            +'    id'+CRLF\
            +'    votes'+CRLF\
            +'    tokenBalance'+CRLF\
            +'    ballotsCastCount'+CRLF\
            +'    proposalsProposedCount'+CRLF\
            +'    percentageOfTotalVotingPower'+CRLF\
            +'    frequencyOfParticipationTotal'+CRLF\
            +'    delegationsCurrentlyReceivedCount'+CRLF\
            +'    frequencyOfParticipationAsActiveVoter'+CRLF\
            +'  }'+CRLF\
            +'}","variables":{"voterAddress":"'+add+'"}}'
            headers = {
            'Content-Type': 'application/json'
            }

            response = requests.request('POST', url1, headers=headers, data=payload)
            res = json.loads(response.text)
            if res['data']['account'] == None:
                voting_power.append('NA')
            else:
                voting_power.append(res['data']['account']['percentageOfTotalVotingPower'])
            
        else:
            voting_power.append((float(r.json()['data']['protocols'][0]['lastCastPower'])/100000000)*100)

        df_voting_power = pd.DataFrame(voting_power, columns = ['votingweight'])
        result = pd.concat([stewards_data, df_voting_power], axis=1)

    w = requests.get("https://api.boardroom.info/v1/protocols/gitcoin")

    totalVotes = w.json()['data']['totalProposals']

    voting_participation = []

    #df1 = pd.read_csv('stewards.csv')

    for i in range(len(result['address'])):
        #print(df1['Voting Power'][i])
        #print(result['address'][i])
        url = 'https://api.boardroom.info/v1/voters/' + result['address'][i]
        r = requests.get(url)

        if str(result['votingweight'][i]) == 'nan':
            voting_participation.append('NA')
            
        elif list(r.json().keys())[0] == 'message':
                voting_participation.append('NA')    
        
        else:
            url = 'https://api.boardroom.info/v1/voters/' + str(result['address'][i])
            res = requests.get(url)
            #print(res.json())
            #print(res.json()['data']['totalVotesCast'])
            userVotesCast = res.json()['data']['protocols'][0]['totalVotesCast']
            voting_participation.append((userVotesCast/totalVotes)*100)

    df2 = pd.DataFrame(voting_participation,columns=['voteparticipation'])
    df3 = pd.concat([result,df2],axis=1)

    df3['json'] = df3.to_json(orient='records', lines=True).splitlines()
    res = [json.loads(df['json'][i])]
    json_list.append(res)

    return render_template("index.html", stewards=json_list)