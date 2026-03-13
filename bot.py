import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
from telegram import Bot
import asyncio
from datetime import datetime, timedelta
import json
import aiohttp

# CONFIGURAZIONE
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# URL per scaricare il calendario (TheSportsDB - Serie A)
# Nota: TheSportsDB ha dati limitati gratis, usiamo football-data per lo storico
CALENDARIO_URL = 'https://www.football-data.org/v4/competitions/SA/matches'
DATI_STORICI_URLS = {
    'Serie A': 'https://www.football-data.co.uk/mmz4281/2324/I1.csv',
    'Premier': 'https://www.football-data.co.uk/mmz4281/2324/E0.csv',
    'La Liga': 'https://www.football-data.co.uk/mmz4281/2324/ES1.csv',
    'Bundesliga': 'https://www.football-data.co.uk/mmz4281/2324/L1.csv'
}

def scarica_dati_storici():
    """Scarica i CSV storici per le statistiche delle squadre"""
    all_df = []
    for lega, url in DATI_STORICI_URLS.items():
        try:
            df = pd.read_csv(url)
            df['Lega'] = lega
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            df['Partita'] = df['HomeTeam'] + " vs " + df['AwayTeam']
            all_df.append(df)
        except Exception as e:
            print(f"Errore download {lega}: {e}")
    
    if all_df:
        return pd.concat(all_df, ignore_index=True)
    return None

async def scarica_calendario_futuro():
    """Scarica le partite future da giocare (prossimi 7 giorni)"""
    partite_future = []
    
    # Usiamo un endpoint gratuito per il calendario
    # Nota: Questo è un esempio - in produzione servirebbe API key
    try:
        # Per ora usiamo un metodo semplificato: leggiamo da un file locale
        # In futuro si può collegare a API vere
        async with aiohttp.ClientSession() as session:
            # Esempio: API gratuita per calcio italiano
            url = "https://api.football-data.org/v4/competitions/SA/matches"
            headers = {'X-Auth-Token': 'YOUR_API_KEY_HERE'}  # Opzionale
            
            # Per ora torniamo partite simulate basate sui dati storici
            # Questo è un placeholder per quando avrai una API key
            pass
    except Exception as e:
        print(f"Errore calendario: {e}")
    
    return partite_future

def calcola_stats(df, squadra, n=10):
    """Calcola media gol fatti e subiti nelle ultime N partite"""
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
    """Analizza una singola partita e restituisce il pronostico"""
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
    
    # 1. Scarica dati storici per le statistiche
    df_storico = scarica_dati_storici()
    if df_storico is None:
        await bot.send_message(CHAT_ID, "❌ Errore download dati storici.")
        return
    
    # 2. Definisci qui le partite di OGGI/DOMANI (da aggiornare manualmente o via API)
    # Formato: (Casa, Ospite, Lega)
    partite_da_analizzare = [
        # Esempio - MODIFICA QUESTE CON LE PARTITE VERE DI OGGI
        # ("Atalanta", "Fiorentina", "Serie A"),
        # ("Milan", "Inter", "Serie A"),
    ]
    
    # 3. Analizza ogni partita
    segnali = []
    for home, away, lega in partite_da_analizzare:
        risultato = analizza_partita(df_storico, home, away, lega)
        if risultato:
            segnali.append(risultato)
    
    # 4. Invia i segnali su Telegram
    if segnali:
        for s in segnali:
            msg = f"""🔥 **SEGNALE TROVATO** 🔥

⚽ {s['partita']}
🏆 {s['lega']}
🎯 **{s['mercato']}**
📈 Probabilità: {s['probabilita']}
⚡ Gol Attesi: {s['gol_attesi']}

⚠️ *Gioca responsabilmente*
            """
            await bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    else:
        await bot.send_message(CHAT_ID, "ℹ️ Nessun segnale >80% per le partite di oggi.")

if __name__ == "__main__":
    asyncio.run(main())
