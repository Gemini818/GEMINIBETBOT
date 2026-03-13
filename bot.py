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

# DATI STORICI
DATI_STORICI_URLS = {
    'Serie A': 'https://www.football-data.co.uk/mmz4281/2324/I1.csv',
    'Premier': 'https://www.football-data.co.uk/mmz4281/2324/E0.csv',
    'La Liga': 'https://www.football-data.co.uk/mmz4281/2324/ES1.csv',
    'Bundesliga': 'https://www.football-data.co.uk/mmz4281/2324/L1.csv'
}

# MAPPATURA NOMI SQUADRE
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
    'Hellas Verona FC': 'Verona',
    'Udinese Calcio': 'Udinese',
    'US Sassuolo': 'Sassuolo',
    'Empoli FC': 'Empoli',
    'US Lecce': 'Lecce',
    'Cagliari Calcio': 'Cagliari',
    'AC Monza': 'Monza',
    'US Salernitana': 'Salernitana',
    'Parma Calcio': 'Parma',
    'Como 1907': 'Como'
}

# PARTITE DI BACKUP (se API fallisce) - AGGIORNA QUI MANUALMENTE
PARTITE_BACKUP = [
    ('Inter', 'Napoli', 'Serie A'),
    ('Juventus', 'Milan', 'Serie A'),
    ('Roma', 'Atalanta', 'Serie A'),
    ('Lazio', 'Fiorentina', 'Serie A'),
    ('Bologna', 'Torino', 'Serie A'),
]

def scarica_dati_storici():
    all_df = []
    for lega, url in DATI_STORICI_URLS.items():
        try:
            df = pd.read_csv(url)
            df['Lega'] = lega
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df['Partita'] = df['HomeTeam'] + " vs " + df['AwayTeam']
            all_df.append(df)
        except Exception as e:
            print(f"Errore {lega}: {e}")
    
    if all_df:
        return pd.concat(all_df, ignore_index=True)
    return None

def scarica_calendario_futuro():
    """Scarica partite future con DEBUG"""
    partite = []
    oggi = datetime.now()
    futuro = oggi + timedelta(days=7)
    
    messaggi_errore = []
    
    # Controlla se API Key esiste
    if not API_KEY:
        messaggi_errore.append("⚠️ API Key NON trovata nei Secrets!")
        return partite, messaggi_errore
    
    if API_KEY == 'YOUR_API_KEY_HERE' or len(API_KEY) < 10:
        messaggi_errore.append("⚠️ API Key sembra non valida!")
        return partite, messaggi_errore
    
    competizioni = [
        ('SA', 'Serie A'),
        ('PL', 'Premier League'),
        ('PD', 'La Liga'),
        ('BL1', 'Bundesliga')
    ]
    
    for comp_id, comp_nome in competizioni:
        try:
            url = f'https://api.football-data.org/v4/competitions/{comp_id}/matches'
            headers = {'X-Auth-Token': API_KEY}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                matches_found = 0
                
                for match in data.get('matches', []):
                    match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                    
                    if oggi <= match_date <= futuro:
                        home = mappa_nome(match['homeTeam']['name'])
                        away = mappa_nome(match['awayTeam']['name'])
                        
                        partite.append({
                            'home': home,
                            'away': away,
                            'data': match_date.strftime('%Y-%m-%d %H:%M'),
                            'lega': comp_nome
                        })
                        matches_found += 1
                
                print(f"✅ {comp_nome}: {matches_found} partite trovate")
                
            elif response.status_code == 403:
                messaggi_errore.append(f"❌ {comp_nome}: API Key non valida (403)")
            elif response.status_code == 429:
                messaggi_errore.append(f"⚠️ {comp_nome}: Limite richieste raggiunto (429)")
            else:
                messaggi_errore.append(f"⚠️ {comp_nome}: Errore {response.status_code}")
                
        except Exception as e:
            messaggi_errore.append(f"❌ {comp_nome}: {str(e)}")
    
    return partite, messaggi_errore

def mappa_nome(nome_squadra):
    return MAPPA_SQUADRE.get(nome_squadra, nome_squadra)

def calcola_stats(df, squadra, n=10):
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
    
    await bot.send_message(CHAT_ID, f"📊 Caricate {len(df_storico)} partite storiche")
    
    # 2. Scarica calendario futuro
    partite_future, errori = scarica_calendario_futuro()
    
    # Invia eventuali errori per debug
    if errori:
        msg_errori = "⚠️ **Report Errori API:**\n\n" + "\n".join(errori)
        await bot.send_message(CHAT_ID, msg_errori)
    
    # Se nessuna partita, usa backup
    if not partite_future:
        await bot.send_message(CHAT_ID, "⚠️ Nessuna partita da API. Uso partite di backup...")
        partite_future = [
            {'home': h, 'away': a, 'lega': l, 'data': datetime.now().strftime('%Y-%m-%d')}
            for h, a, l in PARTITE_BACKUP
        ]
    
    await bot.send_message(CHAT_ID, f"📅 **{len(partite_future)} partite da analizzare**")
    
    # 3. Analizza ogni partita
    segnali = []
    for p in partite_future:
        risultato = analizza_partita(df_storico, p['home'], p['away'], p['lega'])
        if risultato:
            risultato['data'] = p['data']
            segnali.append(risultato)
    
    # 4. Invia segnali
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
        
        msg += "\n⚠️ *Gioca responsabilmente*"
        await bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    else:
        await bot.send_message(CHAT_ID, "ℹ️ Nessun segnale >80% per le partite di oggi.")
    
    await bot.send_message(CHAT_ID, "✅ **Analisi completata!**")

if __name__ == "__main__":
    asyncio.run(main())
