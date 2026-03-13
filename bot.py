import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
from telegram import Bot
import asyncio
from datetime import datetime, timedelta
import requests

# CONFIGURAZIONE
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY = os.getenv('FOOTBALL_DATA_API_KEY')

# DATI STORICI (per statistiche squadre)
DATI_STORICI_URLS = {
    'Serie A': 'https://www.football-data.co.uk/mmz4281/2324/I1.csv',
    'Premier': 'https://www.football-data.co.uk/mmz4281/2324/E0.csv',
    'La Liga': 'https://www.football-data.co.uk/mmz4281/2324/ES1.csv',
    'Bundesliga': 'https://www.football-data.co.uk/mmz4281/2324/L1.csv'
}

# MAPPATURA NOMI SQUADRE (per compatibilità)
MAPPA_SQUADRE = {
    'AC Milan': 'Milan',
    'Inter Milan': 'Inter',
    'Juventus FC': 'Juventus',
    'SSC Napoli': 'Napoli',
    'AS Roma': 'Roma',
    'SS Lazio': 'Lazio',
    'Atalanta BC': 'Atalanta',
    'ACF Fiorentina': 'Fiorentina',
    'Torino FC': 'Torino',
    'Bologna FC': 'Bologna',
    'Genoa CFC': 'Genoa',
    'UC Sampdoria': 'Sampdoria',
    'Hellas Verona FC': 'Verona',
    'Udinese Calcio': 'Udinese',
    'US Sassuolo': 'Sassuolo',
    'Empoli FC': 'Empoli',
    'US Lecce': 'Lecce',
    'Cagliari Calcio': 'Cagliari',
    'Frosinone Calcio': 'Frosinone',
    'AC Monza': 'Monza',
    'US Salernitana': 'Salernitana'
}

def scarica_dati_storici():
    """Scarica CSV storici per statistiche"""
    all_df = []
    for lega, url in DATI_STORICI_URLS.items():
        try:
            df = pd.read_csv(url)
            df['Lega'] = lega
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df['Partita'] = df['HomeTeam'] + " vs " + df['AwayTeam']
            all_df.append(df)
            print(f"✅ Scaricati dati per {lega}")
        except Exception as e:
            print(f"❌ Errore {lega}: {e}")
    
    if all_df:
        return pd.concat(all_df, ignore_index=True)
    return None

def scarica_calendario_futuro():
    """Scarica partite future da football-data.org API"""
    partite = []
    oggi = datetime.now()
    futuro = oggi + timedelta(days=7)  # Prossimi 7 giorni
    
    try:
        headers = {'X-Auth-Token': API_KEY}
        
        # Serie A
        url = 'https://api.football-data.org/v4/competitions/SA/matches'
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for match in data.get('matches', []):
                match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                
                # Filtra solo partite dei prossimi 7 giorni
                if oggi <= match_date <= futuro:
                    home = mappa_nome(match['homeTeam']['name'])
                    away = mappa_nome(match['awayTeam']['name'])
                    
                    partite.append({
                        'home': home,
                        'away': away,
                        'data': match_date.strftime('%Y-%m-%d %H:%M'),
                        'lega': 'Serie A'
                    })
                    print(f"✅ Trovata: {home} vs {away}")
        
        # Premier League
        url = 'https://api.football-data.org/v4/competitions/PL/matches'
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for match in data.get('matches', []):
                match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                
                if oggi <= match_date <= futuro:
                    home = mappa_nome(match['homeTeam']['name'])
                    away = mappa_nome(match['awayTeam']['name'])
                    
                    partite.append({
                        'home': home,
                        'away': away,
                        'data': match_date.strftime('%Y-%m-%d %H:%M'),
                        'lega': 'Premier League'
                    })
                    print(f"✅ Trovata: {home} vs {away}")
        
        # La Liga
        url = 'https://api.football-data.org/v4/competitions/PD/matches'
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for match in data.get('matches', []):
                match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                
                if oggi <= match_date <= futuro:
                    home = mappa_nome(match['homeTeam']['name'])
                    away = mappa_nome(match['awayTeam']['name'])
                    
                    partite.append({
                        'home': home,
                        'away': away,
                        'data': match_date.strftime('%Y-%m-%d %H:%M'),
                        'lega': 'La Liga'
                    })
                    print(f"✅ Trovata: {home} vs {away}")
        
        # Bundesliga
        url = 'https://api.football-data.org/v4/competitions/BL1/matches'
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for match in data.get('matches', []):
                match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                
                if oggi <= match_date <= futuro:
                    home = mappa_nome(match['homeTeam']['name'])
                    away = mappa_nome(match['awayTeam']['name'])
                    
                    partite.append({
                        'home': home,
                        'away': away,
                        'data': match_date.strftime('%Y-%m-%d %H:%M'),
                        'lega': 'Bundesliga'
                    })
                    print(f"✅ Trovata: {home} vs {away}")
                    
    except Exception as e:
        print(f"❌ Errore calendario: {e}")
    
    return partite

def mappa_nome(nome_squadra):
    """Converte nomi API in nomi compatibili con dati storici"""
    return MAPPA_SQUADRE.get(nome_squadra, nome_squadra)

def calcola_stats(df, squadra, n=10):
    """Calcola media gol fatti/subiti ultime N partite"""
    matches = df[(df['HomeTeam'] == squadra) | (df['AwayTeam'] == squadra)]
    matches = matches.sort_values('Date', ascending=False).head(n)
    
    if len(matches) < 5:
        return None
    
    gf, gs = 0, 0
    for _, row in matches.iterrows():
        if row['HomeTeam'] == squadra:
            gf += row['FTHG']
            gs += row['FTAG']
        else:
            gf += row['FTAG']
            gs += row['FTHG']
    
    return {'mf': gf/len(matches), 'ms': gs/len(matches)}

def analizza_partita(df_storico, home, away, lega):
    """Analizza una partita e restituisce pronostico"""
    stat_h = calcola_stats(df_storico, home)
    stat_a = calcola_stats(df_storico, away)
    
    if not stat_h or not stat_a:
        return None
    
    gol_attesi = (stat_h['mf'] + stat_a['ms'] + stat_a['mf'] + stat_h['ms']) / 2
    
    p15 = (1 - sum(poisson.pmf(k, gol_attesi) for k in range(2))) * 100
    p25 = (1 - sum(poisson.pmf(k, gol_attesi) for k in range(3))) * 100
    
    merc, prob = None, 0
    
    if p25 > 75:
        merc, prob = "Over 2.5", p25
    elif p15 > 82:
        merc, prob = "Over 1.5", p15
    
    if merc:
        return {
            'partita': f"{home} vs {away}",
            'lega': lega,
            'mercato': merc,
            'probabilita': f"{prob:.1f}%",
            'gol_attesi': f"{gol_attesi:.2f}"
        }
    return None

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    
    await bot.send_message(CHAT_ID, "🤖 **Bot avviato!** Analisi in corso...")
    
    # 1. Scarica dati storici
    df_storico = scarica_dati_storici()
    if df_storico is None:
        await bot.send_message(CHAT_ID, "❌ Errore download dati storici.")
        return
    
    # 2. Scarica calendario futuro (AUTOMATICO!)
    partite_future = scarica_calendario_futuro()
    
    if not partite_future:
        await bot.send_message(CHAT_ID, "⚠️ Nessuna partita trovata per i prossimi 7 giorni.")
        return
    
    await bot.send_message(CHAT_ID, f"📅 **Trovate {len(partite_future)} partite da analizzare**")
    
    # 3. Analizza ogni partita
    segnali = []
    for p in partite_future:
        risultato = analizza_partita(df_storico, p['home'], p['away'], p['lega'])
        if risultato:
            risultato['data'] = p['data']
            segnali.append(risultato)
    
    # 4. Invia segnali su Telegram
    if segnali:
        msg = f"🔥 **{len(segnali)} SEGNALI TROVATI** 🔥\n\n"
        for s in segnali:
            msg += f"""⚽ {s['partita']}
📅 {s.get('data', 'Oggi')}
🏆 {s['lega']}
🎯 **{s['mercato']}**
📈 Prob: {s['probabilita']}
⚡ Gol Att: {s['gol_attesi']}
──────────────────\n"""
        
        msg += "\n⚠️ *Gioca responsabilmente. Statistiche basate su ultimi 10 match.*"
        await bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    else:
        await bot.send_message(CHAT_ID, "ℹ️ Nessun segnale >80% per le partite di oggi.")
    
    await bot.send_message(CHAT_ID, "✅ **Analisi completata!**")

if __name__ == "__main__":
    asyncio.run(main())
