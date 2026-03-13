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

# DATI STORICI (più leghe possibili)
DATI_STORICI_URLS = {
    'Serie A': 'https://www.football-data.co.uk/mmz4281/2324/I1.csv',
    'Premier': 'https://www.football-data.co.uk/mmz4281/2324/E0.csv',
    'La Liga': 'https://www.football-data.co.uk/mmz4281/2324/ES1.csv',
    'Bundesliga': 'https://www.football-data.co.uk/mmz4281/2324/L1.csv',
    'Ligue 1': 'https://www.football-data.co.uk/mmz4281/2324/F1.csv',
    'Eredivisie': 'https://www.football-data.co.uk/mmz4281/2324/N1.csv',
    'Primeira Liga': 'https://www.football-data.co.uk/mmz4281/2324/P1.csv',
    'Serie B': 'https://www.football-data.co.uk/mmz4281/2324/I2.csv',
    'Championship': 'https://www.football-data.co.uk/mmz4281/2324/E2.csv'
}

# TUTTE LE COMPETIZIONI DA ANALIZZARE (API football-data.org)
COMPETIZIONI = [
    # Leghe Nazionali
    ('SA', 'Serie A', '🇮🇹'),
    ('PL', 'Premier League', '🇬🇧'),
    ('PD', 'La Liga', '🇪🇸'),
    ('BL1', 'Bundesliga', '🇩🇪'),
    ('FL1', 'Ligue 1', '🇫🇷'),
    ('ERE', 'Eredivisie', '🇳🇱'),
    ('PPL', 'Primeira Liga', '🇵🇹'),
    ('BSA', 'Serie A Brasile', '🇧🇷'),
    ('CLI', 'Serie A Argentina', '🇦🇷'),
    
    # Competizioni Europee
    ('CL', 'UEFA Champions League', '🏆'),
    ('EL', 'UEFA Europa League', '🥈'),
    ('EC', 'UEFA Conference League', '🥉'),
    
    # Coppe Nazionali
    ('CLI', 'Coppa Italia', '🇮🇹🏆'),
    ('FAC', 'FA Cup', '🇬🇧🏆'),
    ('CDR', 'Copa del Rey', '🇪🇸🏆'),
    ('DFB', 'DFB Pokal', '🇩🇪🏆'),
    ('CDF', 'Coupe de France', '🇫🇷🏆'),
    
    # Nazionali (quando attive)
    ('WC', 'FIFA World Cup', '🌍'),
    ('EC', 'UEFA Euro', '🇪🇺'),
    ('NL', 'UEFA Nations League', '🏆'),
]

# MAPPATURA NOMI SQUADRE (ESTESA PER TUTTE LE LEGHE)
MAPPA_SQUADRE = {
    # Italia
    'AC Milan': 'Milan', 'Inter Milan': 'Inter', 'Juventus FC': 'Juventus',
    'SSC Napoli': 'Napoli', 'AS Roma': 'Roma', 'SS Lazio': 'Lazio',
    'Atalanta BC': 'Atalanta', 'ACF Fiorentina': 'Fiorentina', 'Torino FC': 'Torino',
    'Bologna FC': 'Bologna', 'Genoa CFC': 'Genoa', 'UC Sampdoria': 'Sampdoria',
    'Hellas Verona FC': 'Verona', 'Udinese Calcio': 'Udinese', 'US Sassuolo': 'Sassuolo',
    'Empoli FC': 'Empoli', 'US Lecce': 'Lecce', 'Cagliari Calcio': 'Cagliari',
    'AC Monza': 'Monza', 'US Salernitana': 'Salernitana', 'Parma Calcio': 'Parma',
    'Como 1907': 'Como', 'Venezia FC': 'Venezia',
    
    # Inghilterra
    'Manchester United FC': 'Man United', 'Manchester City FC': 'Man City',
    'Liverpool FC': 'Liverpool', 'Chelsea FC': 'Chelsea', 'Arsenal FC': 'Arsenal',
    'Tottenham Hotspur FC': 'Tottenham', 'Newcastle United FC': 'Newcastle',
    'Aston Villa FC': 'Aston Villa', 'West Ham United FC': 'West Ham',
    'Brighton & Hove Albion FC': 'Brighton', 'Wolverhampton Wanderers FC': 'Wolves',
    'Everton FC': 'Everton', 'Fulham FC': 'Fulham', 'Brentford FC': 'Brentford',
    'Crystal Palace FC': 'Crystal Palace', 'Nottingham Forest FC': 'Nottm Forest',
    'AFC Bournemouth': 'Bournemouth', 'Luton Town FC': 'Luton', 'Burnley FC': 'Burnley',
    'Sheffield United FC': 'Sheffield Utd', 'Leicester City FC': 'Leicester',
    'Leeds United FC': 'Leeds', 'Southampton FC': 'Southampton',
    
    # Spagna
    'Real Madrid CF': 'Real Madrid', 'FC Barcelona': 'Barcelona',
    'Atlético de Madrid': 'Atletico Madrid', 'Sevilla FC': 'Sevilla',
    'Real Sociedad de Fútbol': 'Real Sociedad', 'Real Betis Balompié': 'Betis',
    'Villarreal CF': 'Villarreal', 'Valencia CF': 'Valencia',
    'Athletic Club': 'Athletic Bilbao', 'Getafe CF': 'Getafe',
    'Girona FC': 'Girona', 'CA Osasuna': 'Osasuna', 'Rayo Vallecano': 'Rayo Vallecano',
    'RC Celta de Vigo': 'Celta Vigo', 'RCD Mallorca': 'Mallorca',
    'Deportivo Alavés': 'Alaves', 'Cádiz CF': 'Cadiz', 'Granada CF': 'Granada',
    'UD Almería': 'Almeria', 'Elche CF': 'Elche',
    
    # Germania
    'FC Bayern München': 'Bayern Munich', 'Borussia Dortmund': 'Dortmund',
    'RB Leipzig': 'RB Leipzig', 'Bayer 04 Leverkusen': 'Leverkusen',
    'Eintracht Frankfurt': 'Frankfurt', 'VfL Wolfsburg': 'Wolfsburg',
    'Borussia Mönchengladbach': 'Gladbach', '1. FC Union Berlin': 'Union Berlin',
    'SC Freiburg': 'Freiburg', '1. FC Köln': 'Koln', 'TSG 1899 Hoffenheim': 'Hoffenheim',
    'VfB Stuttgart': 'Stuttgart', 'FC Augsburg': 'Augsburg', '1. FSV Mainz 05': 'Mainz',
    'Werder Bremen': 'Werder Bremen', 'VfL Bochum 1848': 'Bochum',
    'FC Heidenheim 1846': 'Heidenheim', 'SV Darmstadt 98': 'Darmstadt',
    
    # Francia
    'Paris Saint-Germain FC': 'PSG', 'Olympique de Marseille': 'Marseille',
    'Olympique Lyonnais': 'Lyon', 'AS Monaco FC': 'Monaco',
    'LOSC Lille': 'Lille', 'OGC Nice': 'Nice', 'Stade Rennais FC 1901': 'Rennes',
    'RC Lens': 'Lens', 'Stade de Reims': 'Reims', 'Montpellier HSC': 'Montpellier',
    'FC Nantes': 'Nantes', 'RC Strasbourg Alsace': 'Strasbourg',
    'Toulouse FC': 'Toulouse', 'Le Havre AC': 'Le Havre',
    'Clermont Foot 63': 'Clermont', 'FC Lorient': 'Lorient', 'FC Metz': 'Metz',
    
    # Paesi Bassi
    'AFC Ajax': 'Ajax', 'PSV': 'PSV', 'Feyenoord Rotterdam': 'Feyenoord',
    'AZ Alkmaar': 'AZ', 'FC Twente': 'Twente', 'FC Utrecht': 'Utrecht',
    
    # Portogallo
    'SL Benfica': 'Benfica', 'FC Porto': 'Porto', 'Sporting CP': 'Sporting',
    'SC Braga': 'Braga', 'Vitória SC': 'Vitoria Guimaraes',
}

def scarica_dati_storici():
    """Scarica CSV storici per tutte le leghe"""
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
            print(f"⚠️ Errore {lega}: {e}")
    
    if all_df:
        return pd.concat(all_df, ignore_index=True)
    return None

def scarica_calendario_futuro():
    """Scarica partite future da TUTTE le competizioni"""
    partite = []
    oggi = datetime.now()
    futuro = oggi + timedelta(days=7)  # Prossimi 7 giorni
    
    messaggi_errore = []
    competizioni_processate = 0
    
    if not API_KEY:
        messaggi_errore.append("⚠️ API Key NON trovata!")
        return partite, messaggi_errore
    
    for comp_id, comp_nome, bandiera in COMPETIZIONI:
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
                            'lega': f"{bandiera} {comp_nome}",
                            'competizione': comp_id
                        })
                        matches_found += 1
                
                if matches_found > 0:
                    competizioni_processate += 1
                    print(f"✅ {comp_nome}: {matches_found} partite")
                
            elif response.status_code == 403:
                messaggi_errore.append(f"❌ {comp_nome}: API Key non valida")
            elif response.status_code == 429:
                messaggi_errore.append(f"⚠️ {comp_nome}: Limite richieste")
            # Altre competizioni potrebbero non essere disponibili con API free
            
        except Exception as e:
            # Silenziosamente salta competizioni non disponibili
            pass
    
    print(f"📊 Competizioni processate: {competizioni_processate}")
    return partite, messaggi_errore

def mappa_nome(nome_squadra):
    """Converte nomi API in nomi compatibili"""
    return MAPPA_SQUADRE.get(nome_squadra, nome_squadra)

def calcola_stats(df, squadra, n=10):
    """Calcola statistiche ultime N partite"""
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
    
    await bot.send_message(CHAT_ID, f"📊 Caricate {len(df_storico)} partite storiche")
    
    # 2. Scarica calendario futuro (TUTTE le competizioni)
    partite_future, errori = scarica_calendario_futuro()
    
    # Invia eventuali errori
    if errori:
        msg_errori = "⚠️ **Report Errori:**\n\n" + "\n".join(errori[:5])  # Max 5 errori
        await bot.send_message(CHAT_ID, msg_errori)
    
    if not partite_future:
        await bot.send_message(CHAT_ID, "⚠️ Nessuna partita trovata nei prossimi 7 giorni.")
        return
    
    await bot.send_message(CHAT_ID, f"📅 **{len(partite_future)} partite da analizzare**")
    
    # 3. Analizza ogni partita
    segnali = []
    for p in partite_future:
        risultato = analizza_partita(df_storico, p['home'], p['away'], p['lega'])
        if risultato:
            risultato['data'] = p['data']
            segnali.append(risultato)
    
    # 4. Invia segnali su Telegram
    if segnali:
        # Ordina per probabilità decrescente
        segnali.sort(key=lambda x: float(x['probabilita'].replace('%', '')), reverse=True)
        
        msg = f"🔥 **{len(segnali)} SEGNALI TROVATI** 🔥\n\n"
        for i, s in enumerate(segnali[:10], 1):  # Max 10 segnali per messaggio
            msg += f"""{i}⃣ ⚽ {s['partita']}
📅 {s.get('data', 'Oggi')}
🏆 {s['lega']}
🎯 **{s['mercato']}**
📈 Prob: {s['probabilita']}
⚡ Gol Att: {s['gol_attesi']}
──────────────────\n"""
        
        if len(segnali) > 10:
            msg += f"\n...e altri {len(segnali) - 10} segnali\n"
        
        msg += "\n⚠️ *Gioca responsabilmente. Statistiche su ultimi 10 match.*"
        await bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    else:
        await bot.send_message(CHAT_ID, "ℹ️ Nessun segnale >80% per le partite di oggi.")
    
    await bot.send_message(CHAT_ID, "✅ **Analisi completata!**")

if __name__ == "__main__":
    asyncio.run(main())
