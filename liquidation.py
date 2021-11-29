import json
import time
import requests
from pytezos import pytezos

pytezos = pytezos.using(key = 'PRIVATE_KEY', shell='https://mainnet.api.tez.ie')
address = 'TZ_ADDRESS'

ctez_contract = pytezos.contract('KT1GWnsoFZVHGh7roXEER3qeCcgJgrXT3de2')

amount_max = 490 #ctez in account

def formate_decimal(n):
    n = str(n)
    return float(n[:n.find('.')+7])

def check_decimal(n):
    n=str(n)
    if n[::-1].find('.') < 6:
        n = n+'0'
        return str(n).replace('.','')
    else:
        return str(n).replace('.','')

transactions = []

print("[*] Launched")
while True:
    try:
        ovens = requests.get('https://api.tzkt.io/v1/bigmaps/20919/keys?limit=10000').json()
        oven = requests.get('https://api.tzkt.io/v1/contracts/KT1GWnsoFZVHGh7roXEER3qeCcgJgrXT3de2/storage').json()
    except Exception as e:
        print(e)
    
    if oven and ovens:
    
        target = int(oven['target'])/2**48
        
        for e in ovens:
            try: 
                tez = int(e['value']['tez_balance'])/1000000
                tez = formate_decimal(tez)
                
                ctez = int(e['value']['ctez_outstanding'])/1000000
                liquidation = formate_decimal(ctez*1.0667*target)
                
                if liquidation > tez and liquidation <= amount_max:

                    
                    transaction_fee = check_decimal(formate_decimal(ctez*0.01)) 
                    
                    if tez not in transactions:
                        pytezos.bulk(
                        	ctez_contract.liquidate(to=address, handle={"id": int(e["key"]["id"]), "owner": e["key"]["owner"]}, quantity = int(e['value']['ctez_outstanding']))
                        ).autofill(fee = transaction_fee).sign().inject()
                        transactions.append(tez)
                    print("Liquidation profit on", e["value"]["address"], "of", ctez, "at", time.asctime())
                    
                elif liquidation > tez and liquidation > amount_max:
                    print("Liquidation out of profit on", e["value"]["address"], "of", ctez, "at", time.asctime())
                    
            except Exception as e:
                print(e)
                continue
    time.sleep(5)
