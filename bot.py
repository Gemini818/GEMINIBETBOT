import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
from telegram import Bot
import asyncio
from datetime import datetime, timedelta
import requests

# ═══════════════════════════════════════════════════
# CONFIGURAZIONE BOT - SOGLIE REALISTICHE
# ═══════════════════════════════════════════════════
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY = os.getenv('FOOTBALL_DATA_API_KEY')

# SOGLIE AGGIORNATE (Per ricevere segnali reali)
MIN_QUOTA = 1.60           # Quota minima bookmaker
PROB_15_MIN = 70           # Probabilità minima Over 1.5 (%)
PROB_25_MIN = 65           # Probabilità minima Over 2.5 (%)
GIORNI_ANALISI = 3         # Analizza partite dei prossimi 3 giorni

# DATI STORICI (per statistiche squadre)
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

# COMPETIZIONI DA ANALIZZARE
COMPETIZIONI = [
    ('SA', 'Serie A', '🇮🇹'),
    ('PL', 'Premier League', '🇬🇧'),
    ('PD', 'La Liga', '🇪🇸'),
    ('BL1', 'Bundesliga', '🇩🇪'),
    ('FL1', 'Ligue 1', '🇫🇷'),
    ('ERE', 'Eredivisie', '🇳🇱'),
    ('PPL', 'Primeira Liga', '🇵🇹'),
    ('CL', 'UEFA Champions League', '🏆'),
    ('EL', 'UEFA Europa League', '🥈'),
    ('EC', 'UEFA Conference League', '🥉'),
    ('CLI', 'Coppa Italia', '🇮🇹🏆'),
    ('FAC', 'FA Cup', '🇬🇧🏆'),
    ('CDR', 'Copa del Rey', '🇪🇸🏆'),
    ('DFB', 'DFB Pokal', '🇩🇪🏆')
]

# MAPPATURA NOMI SQUADRE
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
    'AFC Bournemouth': 'Bournemouth', 'Leicester City FC': 'Leicester',
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
    # Germania
    'FC Bayern München': 'Bayern Munich', 'Borussia Dortmund': 'Dortmund',
    'RB Leipzig': 'RB Leipzig', 'Bayer 04 Leverkusen': 'Leverkusen',
    'Eintracht Frankfurt': 'Frankfurt', 'VfL Wolfsburg': 'Wolfsburg',
    'Borussia Mönchengladbach': 'Gladbach', '1. FC Union Berlin': 'Union Berlin',
    'SC Freiburg': 'Freiburg', '1. FC Köln': 'Koln', 'TSG 1899 Hoffenheim': 'Hoffenheim',
    'VfB Stuttgart': 'Stuttgart', 'FC Augsburg': 'Augsburg', '1. FSV Mainz 05': 'Mainz',
    'Werder Bremen': 'Werder Bremen', 'VfL Bochum 1848': 'Bochum',
    # Francia
    'Paris Saint-Germain FC': 'PSG', 'Olympique de Marseille': 'Marseille',
    'Olympique Lyonnais': 'Lyon', 'AS Monaco FC': 'Monaco',
    'LOSC Lille': 'Lille', 'OGC Nice': 'Nice', 'Stade Rennais FC 1901': 'Rennes',
    'RC Lens': 'Lens', 'Stade de Reims': 'Reims', 'Montpellier HSC': 'Montpellier',
    'FC Nantes': 'Nantes', 'RC Strasbourg Alsace': 'Strasbourg',
    'Toulouse FC': 'Toulouse', 'Le Havre AC': 'Le Havre',
    # Paesi Bassi
    'AFC Ajax': 'Ajax', 'PSV': 'PSV', 'Feyenoord Rotterdam': 'Feyenoord',
    'AZ Alkmaar': 'AZ', 'FC Twente': 'Twente', 'FC Utrecht': 'Utrecht',
    # Portogallo
    'SL Benfica': 'Benfica', 'FC Porto': 'Porto', 'Sporting CP': 'Sporting',
    'SC Braga': 'Braga', 'Vitória SC': 'Vitoria Guimaraes',
}

# ═══════════════════════════════════════════════════
# FUNZIONI PRINCIPALI
# ═══════════════════════════════════════════════════

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
    """Scarica partite future da tutte le competizioni"""
    partite = []
    oggi = datetime.now()
    futuro = oggi + timedelta(days=GIORNI_ANALISI)
    
    messaggi_errore = []
    
    if not API_KEY:
        messaggi_errore.append("⚠️ API Key NON trovata nei Secrets!")
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
                        home = MAPPA_SQUADRE.get(match['homeTeam']['name'], match['homeTeam']['name'])
                        away = MAPPA_SQUADRE.get(match['awayTeam']['name'], match['awayTeam']['name'])
                        
                        # Recupero Quote (Odds) se disponibili
                        quota_over_25 = None
                        quota_over_15 = None
                        
                        if 'odds' in match and match['odds']:
                            for odd_obj in match['odds']:
                                market = odd_obj.get('market', '')
                                if 'Over/Under' in market:
                                    for selection in odd_obj.get('selections', []):
                                        if selection.get('name') == 'Over 2.5':
                                            quota_over_25 = selection.get('odd')
                                        elif selection.get('name') == 'Over 1.5':
                                            quota_over_15 = selection.get('odd')
                        
                        partite.append({
                            'home': home,
                            'away': away,
                            'data': match_date.strftime('%Y-%m-%d %H:%M'),
                            'lega': f"{bandiera} {comp_nome}",
                            'quota_reale_25': float(quota_over_25) if quota_over_25 else None,
                            'quota_reale_15': float(quota_over_15) if quota_over_15 else None
                        })
                        matches_found += 1
                
                if matches_found > 0:
                    print(f"✅ {comp_nome}: {matches_found} partite")
                    
            elif response.status_code == 403:
                messaggi_errore.append(f"❌ {comp_nome}: API Key non valida")
            elif response.status_code == 429:
                messaggi_errore.append(f"⚠️ {comp_nome}: Limite richieste raggiunto")
                
        except Exception as e:
            print(f"⚠️ Errore {comp_nome}: {e}")
    
    return partite, messaggi_errore

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

def analizza_partita(df_storico, home, away, lega, quota_reale_25, quota_reale_15):
    """Analizza una partita e restituisce pronostico con filtro quota"""
    stat_h = calcola_stats(df_storico, home)
    stat_a = calcola_stats(df_storico, away)
    
    if not stat_h or not stat_a:
        return None
    
    gol_attesi = (stat_h['mf'] + stat_a['ms'] + stat_a['mf'] + stat_h['ms']) / 2
    
    p15 = (1 - sum(poisson.pmf(k, gol_attesi) for k in range(2))) * 100
    p25 = (1 - sum(poisson.pmf(k, gol_attesi) for k in range(3))) * 100
    
    segnali_possibili = []
    
    # Controllo Over 2.5
    if p25 > PROB_25_MIN:
        quota_usata = quota_reale_25 if quota_reale_25 else (100 / p25)
        
        if quota_usata >= MIN_QUOTA:
            segnali_possibili.append({
                'mercato': "Over 2.5",
                'probabilita': p25,
                'quota': quota_usata,
                'gol_attesi': gol_attesi
            })
    
    # Controllo Over 1.5
    if p15 > PROB_15_MIN:
        quota_usata = quota_reale_15 if quota_reale_15 else (100 / p15)
        
        if quota_usata >= MIN_QUOTA:
            segnali_possibili.append({
                'mercato': "Over 1.5",
                'probabilita': p15,
                'quota': quota_usata,
                'gol_attesi': gol_attesi
            })
    
    # Ritorna il segnale migliore
    if segnali_possibili:
        best = max(segnali_possibili, key=lambda x: x['probabilita'])
        return {
            'partita': f"{home} vs {away}",
            'lega': lega,
            'mercato': best['mercato'],
            'probabilita': f"{best['probabilita']:.1f}%",
            'quota': f"{best['quota']:.2f}",
            'gol_attesi': f"{best['gol_attesi']:.2f}"
        }
    
    return None

# ═══════════════════════════════════════════════════
# FUNZIONE PRINCIPALE
# ═══════════════════════════════════════════════════

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    
    await bot.send_message(CHAT_ID, f"🤖 **Bot avviato!**\n📊 Soglie: Over 1.5 >{PROB_15_MIN}% | Over 2.5 >{PROB_25_MIN}% | Quota ≥{MIN_QUOTA}")
    
    # 1. Scarica dati storici
    df_storico = scarica_dati_storici()
    if df_storico is None:
        await bot.send_message(CHAT_ID, "❌ Errore download dati storici.")
        return
    
    await bot.send_message(CHAT_ID, f"📊 Caricate {len(df_storico)} partite storiche")
    
    # 2. Scarica calendario futuro
    partite_future, errori = scarica_calendario_futuro()
    
    # Invia eventuali errori
    if errori:
        msg_errori = "⚠️ **Report Errori:**\n\n" + "\n".join(errori[:5])
        await bot.send_message(CHAT_ID, msg_errori)
    
    if not partite_future:
        await bot.send_message(CHAT_ID, "⚠️ Nessuna partita trovata nei prossimi {} giorni.".format(GIORNI_ANALISI))
        return
    
    await bot.send_message(CHAT_ID, f"📅 **{len(partite_future)} partite da analizzare**")
    
    # 3. Analizza ogni partita
    segnali = []
    scartati_quota = 0
    scartati_prob = 0
    
    for p in partite_future:
        risultato = analizza_partita(
            df_storico, p['home'], p['away'], p['lega'],
            p.get('quota_reale_25'), p.get('quota_reale_15')
        )
        if risultato:
            risultato['data'] = p['data']
            segnali.append(risultato)
    
    # 4. Invia segnali su Telegram
    if segnali:
        segnali.sort(key=lambda x: float(x['probabilita'].replace('%', '')), reverse=True)
        
        msg = f"🔥 **{len(segnali)} SEGNALI TROVATI** 🔥\n\n"
        for i, s in enumerate(segnali[:10], 1):
            msg += f"""{i}⃣ ⚽ {s['partita']}
📅 {s.get('data', 'Oggi')}
🏆 {s['lega']}
🎯 **{s['mercato']}**
📈 Prob: {s['probabilita']}
💰 **Quota: {s['quota']}**
⚡ Gol Att: {s['gol_attesi']}
──────────────────\n"""
        
        if len(segnali) > 10:
            msg += f"\n...e altri {len(segnali) - 10} segnali\n"
        
        msg += f"\n⚠️ *Gioca responsabilmente. Statistiche su ultimi 10 match.*"
        await bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    else:
        msg_no_signal = f"ℹ️ Nessun segnale valido oggi.\n\n"
        msg_no_signal += f"Motivi possibili:\n"
        msg_no_signal += f"- Nessuna partita con probabilità > soglia\n"
        msg_no_signal += f"- Tutte le partite buone avevano quota < {MIN_QUOTA}\n\n"
        msg_no_signal += f"📊 Partite analizzate: {len(partite_future)}"
        await bot.send_message(CHAT_ID, msg_no_signal)
    
    await bot.send_message(CHAT_ID, "✅ **Analisi completata!**")

if __name__ == "__main__":
    asyncio.run(main())
