import time
import calendar
import multiprocessing
from sympy import *
from pytezos import pytezos
from decimal import Decimal
from datetime import datetime

#Portefeuille
pytezos = pytezos.using(key = 'PRIVATE_KEY', shell='https://rpc.tzbeta.net')
address = 'TZ_ADDRESS'

#Contract communs
core_spicy = pytezos.contract('KT1PwoZxyv4XkPEGnTqWYvjA1UYiPTgAGyqL')
wtz_contract = pytezos.contract('KT1PnUZCp3u2KzWr93pn4DD7HAJnm3rWVrgn')
wtz_address = 'KT1PnUZCp3u2KzWr93pn4DD7HAJnm3rWVrgn'

#Pairs sur lesquelles il y a arbitrage
pairs = { 
    0:{
        'name': 'SPI',
        'pool_spicy': pytezos.contract('KT1UUjqN2tVHb2xEXS6XHs1GbuV1F6cDTAiT'),
        'spicy_address': 'KT1UUjqN2tVHb2xEXS6XHs1GbuV1F6cDTAiT',
        'pool_quipu': pytezos.contract('KT1Eg2QesN1tCzScTrvoeKm5W67GgjV32McR'),
        'pool_address': 'KT1Eg2QesN1tCzScTrvoeKm5W67GgjV32McR',
        'token_contract': pytezos.contract('KT1CS2xKGHNPTauSh5Re4qE3N9PCfG5u4dPx'),
        'token_address': 'KT1CS2xKGHNPTauSh5Re4qE3N9PCfG5u4dPx',
        'decimal': 6
    },
    1:{
        'name': 'hDAO',
        'pool_spicy': pytezos.contract('KT1EAuMMJgtZ4uR9HpjkhcyAQQtDZSsadUR4'),
        'spicy_address':    'KT1EAuMMJgtZ4uR9HpjkhcyAQQtDZSsadUR4',
        'pool_quipu': pytezos.contract('KT1QxLqukyfohPV5kPkw97Rs6cw1DDDvYgbB'),
        'pool_address': 'KT1QxLqukyfohPV5kPkw97Rs6cw1DDDvYgbB',
        'token_contract': pytezos.contract('KT1AFA2mwNUMNd4SsujE1YYp29vd8BZejyKW'),
        'token_address': 'KT1AFA2mwNUMNd4SsujE1YYp29vd8BZejyKW',
        'decimal': 6
    },
    2:{
        'name': 'FLAME',
        'pool_spicy': pytezos.contract('KT1PBJcT5ayGf4tjHRyvh2tTx7DpBUudoGyA'),
        'spicy_address': 'KT1PBJcT5ayGf4tjHRyvh2tTx7DpBUudoGyA',
        'pool_quipu': pytezos.contract('KT1Q93ftAUzvfMGPwC78nX8eouL1VzmHPd4d'),
        'pool_address': 'KT1Q93ftAUzvfMGPwC78nX8eouL1VzmHPd4d',
        'token_contract': pytezos.contract('KT1Wa8yqRBpFCusJWgcQyjhRz7hUQAmFxW7j'),
        'token_address': 'KT1Wa8yqRBpFCusJWgcQyjhRz7hUQAmFxW7j',
        'decimal': 6
    }
}

t = {
        "SPI": 0,
        "hDAO": 0,
        "FLAME": 0
}

def return_on_swap(target, source, amount):
    #Calcul le nombre de token en retour sur un swap
    price = (target*amount/(source+amount))*0.997
    return price

def local_maxima(sr0, sr1, tr1, tr0):
    #Calcule le meilleur profit réalisable sur un double swap
    x = Symbol('x')
    f = (tr0*((sr1*x/(sr0+x))*0.997)/(tr1+((sr1*x/(sr0+x))*0.997)))*0.997-x
    fprime = diff(f, x)
    solution = [[xx, f.subs(x, xx)] for xx in solve(fprime, x) if(xx>0 and f.subs(x, xx)> 0.05)]
    return solution

def formate_decimal(n, decimal):
    #Limite le nombre de decimal
    n = str(n)
    return float(n[:n.find('.')+decimal+1])

def to_int(n):
    #De decimal a int
    n=str(n)
    if n[::-1].find('.') < 6:
        n = n+'0'
        return int(str(n).replace('.',''))
    else:
        return int(str(n).replace('.',''))

def to_decimal(n, decimal):
    #De int a decimal
    n = list(str(n))
    n.insert(decimal*-1, '.')
    n = float(''.join(n))
    return n

def swap_quipu_to_spicy(pool_quipu, spicy_address, pool,spicy, pool_address, token_contract, token_address, token, wtz, amount):
    #Swap de quipuswap a spicyswap sans passer par le routeur
    dead = calendar.timegm(time.gmtime())+1800
    pytezos.bulk(
        pool_quipu.tezToTokenPayment(min_out=token, receiver=address).with_amount(Decimal(amount)),

        token_contract.transfer([{"txs":[{"to_": spicy_address, "amount": token, "token_id": 0}], "from_": address}]),
        contract_pool.start_swap(_to=address, flash=None, amount0Out=0, amount1Out=round(token*0.98))
    ).send()

def swap_spicy_to_quipu(pool_quipu, spicy_address, pool_spicy, pool_address, token_contract, token_address, token, xtz, amount):
    #Swap de spicyswap a quipuswap sans passer par le routeur	
    dead = calendar.timegm(time.gmtime())+1800
    pytezos.bulk(
        wtz_contract.transfer([{"txs":[{"to_": spicy_address, "amount": amount, "token_id": 0}], "from_": address}]),
        pool_spicy.start_swap(_to=address, flash=None, amount0Out=0, amount1Out=round(token*0.98)),

        token_contract.update_operators([{"add_operator": {"owner": address, "operator": pool_address, "token_id": 0}}]),
        pool_quipu.tokenToTezPayment(amount = token, min_out = round(xtz*0.995), receiver = address)
    ).send()

def loop(pair):
    #Récupère le storage des smart-contracts
    spicy_storage = pair['pool_spicy'].storage()
    quipu_storage = pair['pool_quipu'].storage()

    #Récupère les tokens en pool
    sr0 = to_decimal(spicy_storage['reserve0'],pair['decimal'])
    sr1 = to_decimal(spicy_storage['reserve1'], pair['decimal'])
    qr0 = to_decimal(quipu_storage['storage']['tez_pool'], pair['decimal'])
    qr1 = to_decimal(quipu_storage['storage']['token_pool'], pair['decimal'])
    
    #Une solution est un bénéfice supérieur a 0.05 xtz 
    solution = local_maxima(sr0, sr1, qr1, qr0)
    if solution:
    	#Si la transaction n'a pas  déjà été faite alors elle sera éxécuté
        if solution[0][0] != t[pair['name']]:
            #Calcul des nombres de tokens a swap pour la transaction
            amount = formate_decimal(solution[0][0], 6)
            
            token = return_on_swap(sr1 ,sr0, amount) 
            token = formate_decimal(token, pair['decimal'])
            
            xtz = return_on_swap(qr0, qr1, token)
            xtz = formate_decimal(xtz, 6)
            
            token = to_int(token)
            xtz = to_int(xtz)
            amount = to_int(amount)
 
            swap_spicy_to_quipu(pair['pool_quipu'], pair['spicy_address'], pair['pool_spicy'], pair['pool_address'], pair['token_contract'], pair['token_address'], token, xtz, amount)
            
            t[pair['name']] = solution[0][0]
            print(f"Spicy to Quipu on {pair['name']}: {solution[0][1]}")

    else:
        solution = local_maxima(qr0, qr1, sr1, sr0)
        if solution:
            if solution[0][0] != t[pair['name']]:
                amount = formate_decimal(solution[0][0], 6)
                
                token = return_on_swap(qr1 ,qr0, amount) 
                token = formate_decimal(token, pair['decimal'])
                
                wtz = return_on_swap(sr0, sr1, token)
                wtz = formate_decimal(wtz, 6)
                
                amount = str(amount)
                token = to_int(token)
                wtz = to_int(wtz)
                
                swap_quipu_to_spicy(pair['pool_quipu'], pair['spicy_address'], pair['pool_spicy'], pair['pool_address'], pair['token_contract'], pair['token_address'], token, wtz, amount)
                
                t[pair['name']] = solution[0][0]
                print(f"Quipu to spicy on {pair['name']}: {solution[0][1]}")

 
print("Launched")
while True:
    try:
        for k, v in pairs.items():
            loop(pairs[k])
    except Exception as error:
        print(error)
