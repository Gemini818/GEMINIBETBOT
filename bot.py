import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
from telegram import Bot
import asyncio
from datetime import datetime, timedelta
import requests
import math

# ═══════════════════════════════════════════════════
# CONFIGURAZIONE BOT
# ═══════════════════════════════════════════════════
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY = os.getenv('FOOTBALL_DATA_API_KEY')

# SOGLIE MULTIPLE (sistema a cascata)
SOGLIE = [
    {'nome': '⭐ PREMIUM', 'prob_15': 75, 'prob_25': 70, 'quota': 1.70},
    {'nome': '🟢 ALTA', 'prob_15': 70, 'prob_25': 65, 'quota': 1.65},
    {'nome': '📊 STANDARD', 'prob_15': 65, 'prob_25': 60, 'quota': 1.60},
    {'nome': '⚠️ BASE', 'prob_15': 60, 'prob_25': 55, 'quota': 1.55},
]

MIN_SEGNALI_GIORNALIERI = 2
GIORNI_ANALISI = 3

# DATI STORICI (URL PULITI SENZA SPAZI)
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

# COMPETIZIONI
COMPETIZIONI = [
    ('SA', 'Serie A', '🇮🇹'), ('PL', 'Premier League', '🇬🇧'),
    ('PD', 'La Liga', '🇪🇸'), ('BL1', 'Bundesliga', '🇩🇪'),
    ('FL1', 'Ligue 1', '🇫🇷'), ('ERE', 'Eredivisie', '🇳🇱'),
    ('PPL', 'Primeira Liga', '🇵🇹'), ('CL', 'UEFA Champions League', '🏆'),
    ('EL', 'UEFA Europa League', '🥈'), ('EC', 'UEFA Conference League', '🥉'),
    ('CLI', 'Coppa Italia', '🇮🇹🏆'), ('FAC', 'FA Cup', '🇬🇧🏆'),
    ('CDR', 'Copa del Rey', '🇪🇸🏆'), ('DFB', 'DFB Pokal', '🇩🇪🏆')
]

# MAPPATURA NOMI SQUADRE (ESTESA)
MAPPA_SQUADRE = {
    'AC Milan': 'Milan', 'Inter Milan': 'Inter', 'Juventus FC': 'Juventus',
    'SSC Napoli': 'Napoli', 'AS Roma': 'Roma', 'SS Lazio': 'Lazio',
    'Atalanta BC': 'Atalanta', 'ACF Fiorentina': 'Fiorentina', 'Torino FC': 'Torino',
    'Bologna FC': 'Bologna', 'Genoa CFC': 'Genoa', 'UC Sampdoria': 'Sampdoria',
    'Hellas Verona FC': 'Verona', 'Udinese Calcio': 'Udinese', 'US Sassuolo': 'Sassuolo',
    'Empoli FC': 'Empoli', 'US Lecce': 'Lecce', 'Cagliari Calcio': 'Cagliari',
    'AC Monza': 'Monza', 'US Salernitana': 'Salernitana', 'Parma Calcio': 'Parma',
    'Como 1907': 'Como', 'Venezia FC': 'Venezia',
    'Manchester United FC': 'Man United', 'Manchester City FC': 'Man City',
    'Liverpool FC': 'Liverpool', 'Chelsea FC': 'Chelsea', 'Arsenal FC': 'Arsenal',
    'Tottenham Hotspur FC': 'Tottenham', 'Newcastle United FC': 'Newcastle',
    'Aston Villa FC': 'Aston Villa', 'West Ham United FC': 'West Ham',
    'Brighton & Hove Albion FC': 'Brighton', 'Wolverhampton Wanderers FC': 'Wolves',
    'Everton FC': 'Everton', 'Fulham FC': 'Fulham', 'Brentford FC': 'Brentford',
    'Crystal Palace FC': 'Crystal Palace', 'Nottingham Forest FC': 'Nottm Forest',
    'AFC Bournemouth': 'Bournemouth', 'Leicester City FC': 'Leicester',
    'Leeds United FC': 'Leeds', 'Southampton FC': 'Southampton',
    'Real Madrid CF': 'Real Madrid', 'FC Barcelona': 'Barcelona',
    'Atlético de Madrid': 'Atletico Madrid', 'Sevilla FC': 'Sevilla',
    'Real Sociedad de Fútbol': 'Real Sociedad', 'Real Betis Balompié': 'Betis',
    'Villarreal CF': 'Villarreal', 'Valencia CF': 'Valencia',
    'Athletic Club': 'Athletic Bilbao', 'Getafe CF': 'Getafe',
    'Girona FC': 'Girona', 'CA Osasuna': 'Osasuna', 'Rayo Vallecano': 'Rayo Vallecano',
    'RC Celta de Vigo': 'Celta Vigo', 'RCD Mallorca': 'Mallorca',
    'Deportivo Alavés': 'Alaves', 'Cádiz CF': 'Cadiz', 'Granada CF': 'Granada',
    'FC Bayern München': 'Bayern Munich', 'Borussia Dortmund': 'Dortmund',
    'RB Leipzig': 'RB Leipzig', 'Bayer 04 Leverkusen': 'Leverkusen',
    'Eintracht Frankfurt': 'Frankfurt', 'VfL Wolfsburg': 'Wolfsburg',
    'Borussia Mönchengladbach': 'Gladbach', '1. FC Union Berlin': 'Union Berlin',
    'SC Freiburg': 'Freiburg', '1. FC Köln': 'Koln', 'TSG 1899 Hoffenheim': 'Hoffenheim',
    'VfB Stuttgart': 'Stuttgart', 'FC Augsburg': 'Augsburg', '1. FSV Mainz 05': 'Mainz',
    'Werder Bremen': 'Werder Bremen', 'VfL Bochum 1848': 'Bochum',
    'Paris Saint-Germain FC': 'PSG', 'Olympique de Marseille': 'Marseille',
    'Olympique Lyonnais': 'Lyon', 'AS Monaco FC': 'Monaco',
    'LOSC Lille': 'Lille', 'OGC Nice': 'Nice', 'Stade Rennais FC 1901': 'Rennes',
    'RC Lens': 'Lens', 'Stade de Reims': 'Reims', 'Montpellier HSC': 'Montpellier',
    'FC Nantes': 'Nantes', 'RC Strasbourg Alsace': 'Strasbourg',
    'Toulouse FC': 'Toulouse', 'Le Havre AC': 'Le Havre',
    'AFC Ajax': 'Ajax', 'PSV': 'PSV', 'Feyenoord Rotterdam': 'Feyenoord',
    'AZ Alkmaar': 'AZ', 'FC Twente': 'Twente', 'FC Utrecht': 'Utrecht',
    'SL Benfica': 'Benfica', 'FC Porto': 'Porto', 'Sporting CP': 'Sporting',
    'SC Braga': 'Braga', 'Vitória SC': 'Vitoria Guimaraes',
}

# ═══════════════════════════════════════════════════
# FUNZIONI UTILI
# ═══════════════════════════════════════════════════

def rimuovi_fuso_orario(dt):
    """Converte datetime aware in naive per confronti uniformi"""
    if dt is None:
        return None
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

def calcola_probabilita_multipla(segnali):
    """Calcola la probabilità combinata di una multipla"""
    if not segnali:
        return 0.0
    prob_totale = 1.0
    for s in segnali:
        # Estrai percentuale (es. "85.2%" -> 0.852)
        p = float(s['probabilita'].replace('%', '')) / 100.0
        prob_totale *= p
    return prob_totale * 100

def calcola_quota_multipla(segnali):
    """Calcola la quota totale moltiplicando le singole"""
    if not segnali:
        return 0.0
    quota_totale = 1.0
    for s in segnali:
        q = float(s['quota'])
        quota_totale *= q
    return quota_totale

# ═══════════════════════════════════════════════════
# FUNZIONI PRINCIPALI
# ═══════════════════════════════════════════════════

def scarica_dati_storici():
    """Scarica CSV storici per tutte le leghe"""
    all_df = []
    for lega, url in DATI_STORICI_URLS.items():
        try:
            # URL pulito tramite .strip()
            df = pd.read_csv(url.strip())
            df['Lega'] = lega
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df['Date'] = df['Date'].apply(rimuovi_fuso_orario)
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
            # URL corretto senza spazi
            url = f'https://api.football-data.org/v4/competitions/{comp_id}/matches'
            headers = {'X-Auth-Token': API_KEY}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                matches_found = 0
                
                for match in data.get('matches', []):
                    match_date = datetime.fromisoformat(match['utcDate'].replace('Z', '+00:00'))
                    match_date = rimuovi_fuso_orario(match_date)
                    
                    if oggi <= match_date <= futuro:
                        home = MAPPA_SQUADRE.get(match['homeTeam']['name'], match['homeTeam']['name'])
                        away = MAPPA_SQUADRE.get(match['awayTeam']['name'], match['awayTeam']['name'])
                        
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

def analizza_partita_cascata(df_storico, home, away, lega, quota_reale_25, quota_reale_15):
    """Analizza partita con sistema a cascata"""
    stat_h = calcola_stats(df_storico, home)
    stat_a = calcola_stats(df_storico, away)
    
    if not stat_h or not stat_a:
        return None
    
    gol_attesi = (stat_h['mf'] + stat_a['ms'] + stat_a['mf'] + stat_h['ms']) / 2
    
    p15 = (1 - sum(poisson.pmf(k, gol_attesi) for k in range(2))) * 100
    p25 = (1 - sum(poisson.pmf(k, gol_attesi) for k in range(3))) * 100
    
    migliori_segnali = []
    
    for soglia in SOGLIE:
        segnali_possibili = []
        
        if p25 > soglia['prob_25']:
            quota_usata = quota_reale_25 if quota_reale_25 else (100 / p25)
            if quota_usata >= soglia['quota']:
                segnali_possibili.append({
                    'mercato': "Over 2.5",
                    'probabilita': p25,
                    'quota': quota_usata,
                    'gol_attesi': gol_attesi,
                    'livello': soglia['nome']
                })
        
        if p15 > soglia['prob_15']:
            quota_usata = quota_reale_15 if quota_reale_15 else (100 / p15)
            if quota_usata >= soglia['quota']:
                segnali_possibili.append({
                    'mercato': "Over 1.5",
                    'probabilita': p15,
                    'quota': quota_usata,
                    'gol_attesi': gol_attesi,
                    'livello': soglia['nome']
                })
        
        if segnali_possibili:
            best = max(segnali_possibili, key=lambda x: x['probabilita'])
            migliori_segnali.append(best)
            break
    
    if migliori_segnali:
        best = migliori_segnali[0]
        return {
            'partita': f"{home} vs {away}",
            'lega': lega,
            'mercato': best['mercato'],
            'probabilita': f"{best['probabilita']:.1f}%",
            'quota': f"{best['quota']:.2f}",
            'gol_attesi': f"{best['gol_attesi']:.2f}",
            'livello': best['livello']
        }
    
    return None

# ═══════════════════════════════════════════════════
# FUNZIONE PRINCIPALE
# ═══════════════════════════════════════════════════

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    
    await bot.send_message(CHAT_ID, f"🤖 **Bot avviato!**\n🎯 Obiettivo: {MIN_SEGNALI_GIORNALIERI}+ segnali al giorno")
    
    # 1. Scarica dati storici
    df_storico = scarica_dati_storici()
    if df_storico is None:
        await bot.send_message(CHAT_ID, "❌ Errore download dati storici.")
        return
    
    await bot.send_message(CHAT_ID, f"📊 Caricate {len(df_storico)} partite storiche")
    
    # 2. Scarica calendario futuro
    partite_future, errori = scarica_calendario_futuro()
    
    if errori:
        msg_errori = "⚠️ **Report Errori:**\n\n" + "\n".join(errori[:5])
        await bot.send_message(CHAT_ID, msg_errori)
    
    if not partite_future:
        await bot.send_message(CHAT_ID, f"⚠️ Nessuna partita trovata nei prossimi {GIORNI_ANALISI} giorni.")
        return
    
    await bot.send_message(CHAT_ID, f"📅 **{len(partite_future)} partite da analizzare**")
    
    # 3. Analizza ogni partita
    tutti_segnali = []
    
    for p in partite_future:
        risultato = analizza_partita_cascata(
            df_storico, p['home'], p['away'], p['lega'],
            p.get('quota_reale_25'), p.get('quota_reale_15')
        )
        if risultato:
            risultato['data'] = p['data']
            tutti_segnali.append(risultato)
    
    # 4. Ordina per livello e probabilità
    ordine_livelli = {'⭐ PREMIUM': 0, '🟢 ALTA': 1, '📊 STANDARD': 2, '⚠️ BASE': 3}
    tutti_segnali.sort(key=lambda x: (ordine_livelli.get(x['livello'], 99), -float(x['probabilita'].replace('%', ''))))
    
    # 5. Seleziona i migliori segnali singoli
    segnali_finali = tutti_segnali[:max(MIN_SEGNALI_GIORNALIERI, len(tutti_segnali))]
    
    # 6. CALCOLO MULTIPLA SICURA (>80%)
    multipla_sicura = None
    if len(tutti_segnali) >= 2:
        # Prova a creare una multipla da 2 eventi con i segnali più sicuri
        candidati = tutti_segnali[:5] # Prendi i top 5
        for i in range(len(candidati)):
            for j in range(i + 1, len(candidati)):
                combo = [candidati[i], candidati[j]]
                prob_combo = calcola_probabilita_multipla(combo)
                
                # Se la probabilità combinata è > 80%, è una multipla sicura
                if prob_combo > 80.0:
                    multipla_sicura = {
                        'eventi': combo,
                        'probabilita': prob_combo,
                        'quota_totale': calcola_quota_multipla(combo)
                    }
                    break
            if multipla_sicura:
                break
        
        # Se nessuna da 2 supera l'80%, prova con singole molto alte se esistono
        if not multipla_sicura and len(candidati) > 0:
             # Fallback: se il singolo migliore è > 85% lo proponiamo come "Super Singola"
             if float(candidati[0]['probabilita'].replace('%','')) > 85:
                 multipla_sicura = {
                    'eventi': [candidati[0]],
                    'probabilita': float(candidati[0]['probabilita'].replace('%','')),
                    'quota_totale': float(candidati[0]['quota'])
                 }

    # 7. Invia segnali su Telegram
    messaggio_inviato = False
    
    # Invio Multipla Sicura (Priorità Massima)
    if multipla_sicura:
        eventi = multipla_sicura['eventi']
        msg = f"🔒 **MULTIPLA SICURA (>80%)** 🔒\n\n"
        msg += f"📈 **Probabilità Uscita: {multipla_sicura['probabilita']:.1f}%**\n"
        msg += f"💰 **Quota Totale: {multipla_sicura['quota_totale']:.2f}**\n\n"
        
        for idx, ev in enumerate(eventi, 1):
            msg += f"{idx}️⃣⃣ ⚽ {ev['partita']}\n"
            msg += f"   🎯 {ev['mercato']} ({ev['probabilita']})\n"
            msg += f"   💵 Quota: {ev['quota']}\n"
            msg += f"   🏆 {ev['lega']}\n\n"
        
        msg += f"⚠️ *Gioca responsabilmente. Anche l'80% può perdere.*"
        await bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
        messaggio_inviato = True

    # Invio Segnali Singoli
    if segnali_finali:
        if messaggio_inviato:
            await asyncio.sleep(2) # Pausa tra i messaggi
            
        msg = f"🔥 **{len(segnali_finali)} SEGNALI SINGOLI** 🔥\n\n"
        
        segnali_per_livello = {}
        for s in segnali_finali:
            livello = s['livello']
            if livello not in segnali_per_livello:
                segnali_per_livello[livello] = []
            segnali_per_livello[livello].append(s)
        
        for livello, segnali in segnali_per_livello.items():
            msg += f"\n{livello} ({len(segnali)} segnali)\n"
            msg += "──────────────────\n"
            
            for i, s in enumerate(segnali, 1):
                msg += f"""⚽ {s['partita']}
📅 {s.get('data', 'Oggi')}
🏆 {s['lega']}
🎯 **{s['mercato']}**
📈 Prob: {s['probabilita']}
💰 Quota: {s['quota']}
⚡ Gol Att: {s['gol_attesi']}
──────────────────\n"""
        
        msg += f"\n⚠️ *Gioca responsabilmente.*"
        await bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    elif not messaggio_inviato:
        await bot.send_message(CHAT_ID, f"ℹ️ Nessun segnale valido trovato tra {len(partite_future)} partite analizzate.")
    
    await bot.send_message(CHAT_ID, "✅ **Analisi completata!**")

if __name__ == "__main__":
    asyncio.run(main())
