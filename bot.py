import os
import pandas as pd
import numpy as np
from scipy.stats import poisson
from telegram import Bot
import asyncio
from datetime import datetime
import json

# CONFIGURAZIONE (Prende le password dai Secret di GitHub)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
FILE_RISULTATI = 'risultati.json'

# URL DATI (Football-Data.co.uk - Stagione attuale)
DATA_URLS = {
    'Serie A': 'https://www.football-data.co.uk/mmz4281/2324/I1.csv',
    'Premier': 'https://www.football-data.co.uk/mmz4281/2324/E0.csv',
    'La Liga': 'https://www.football-data.co.uk/mmz4281/2324/ES1.csv',
    'Bundesliga': 'https://www.football-data.co.uk/mmz4281/2324/L1.csv'
}

def carica_risultati():
    """Carica lo storico delle scommesse dal file JSON"""
    if os.path.exists(FILE_RISULTATI):
        with open(FILE_RISULTATI, 'r') as f:
            return json.load(f)
    return []

def salva_risultati(dati):
    """Salva lo storico aggiornato nel file JSON"""
    with open(FILE_RISULTATI, 'w') as f:
        json.dump(dati, f, indent=2)

def scarica_dati():
    """Scarica i CSV aggiornati da football-data.co.uk"""
    all_df = []
    for lega, url in DATA_URLS.items():
        try:
            df = pd.read_csv(url)
            df['Lega'] = lega
            # Converte la data in formato leggibile
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            # Crea un nome unico per la partita (es: Milan vs Inter)
            df['Partita'] = df['HomeTeam'] + " vs " + df['AwayTeam']
            all_df.append(df)
        except Exception as e:
            print(f"Errore download {lega}: {e}")
    
    if all_df:
        return pd.concat(all_df, ignore_index=True)
    return None

def calcola_stats(df, squadra, n=10):
    """Calcola media gol fatti e subiti nelle ultime N partite"""
    matches = df[(df['HomeTeam'] == squadra) | (df['AwayTeam'] == squadra)]
    matches = matches.sort_values('Date', ascending=False).head(n)
    
    if len(matches) < 5:
        return None
    
    gf, gs = 0, 0
    for _, row in matches.iterrows():
        if row['HomeTeam'] == squadra:
            gf += row['FTHG'] # Gol Fatti Home
            gs += row['FTAG'] # Gol Subiti Home
        else:
            gf += row['FTAG'] # Gol Fatti Away
            gs += row['FTHG'] # Gol Subiti Away
    
    return {'mf': gf/len(matches), 'ms': gs/len(matches)}

def analizza_partite(df):
    """Trova le partite con probabilità > soglia"""
    segnali = []
    # Prende l'ultima data disponibile nei dati scaricati
    last_date = df['Date'].max()
    matches = df[df['Date'] == last_date]
    
    for _, m in matches.iterrows():
        h, a = m['HomeTeam'], m['AwayTeam']
        
        stat_h = calcola_stats(df, h)
        stat_a = calcola_stats(df, a)
        
        if not stat_h or not stat_a:
            continue
        
        # Calcolo Gol Attesi (Expected Goals)
        gol_attesi = (stat_h['mf'] + stat_a['ms'] + stat_a['mf'] + stat_h['ms']) / 2
        
        # Calcolo Probabilità con Distribuzione di Poisson
        # Over 1.5: Probabilità che i gol siano > 1.5
        p15 = (1 - sum(poisson.pmf(k, gol_attesi) for k in range(2))) * 100
        # Over 2.5: Probabilità che i gol siano > 2.5
        p25 = (1 - sum(poisson.pmf(k, gol_attesi) for k in range(3))) * 100
        
        merc, prob = None, 0
        
        # FILTRI DI AFFIDABILITÀ
        if p25 > 75:  # Se Over 2.5 ha più del 75% di probabilità
            merc, prob = "Over 2.5", p25
        elif p15 > 82: # Se Over 1.5 ha più dell'82% di probabilità
            merc, prob = "Over 1.5", p15
        
        if merc:
            segnali.append({
                'data': m['Date'].strftime('%Y-%m-%d'),
                'partita': f"{h} vs {a}",
                'lega': m['Lega'],
                'mercato': merc,
                'probabilita': f"{prob:.1f}%",
                'gol_attesi': f"{gol_attesi:.2f}"
            })
    
    # Ordina per probabilità decrescente e prendi solo la migliore (Top 1)
    segnali.sort(key=lambda x: float(x['probabilita'].replace('%', '')), reverse=True)
    return segnali[:1]

def aggiorna_risultati(vecchi_segnali, df_storico):
    """Controlla le partite 'IN_CORSO' e vede se sono finite"""
    nuovi_segnali = []
    aggiornamenti = []
    
    for s in vecchi_segnali:
        if s.get('stato') == 'IN_CORSO':
            # Cerca la partita nei dati storici aggiornati
            match = df_storico[df_storico['Partita'] == s['partita']]
            
            if not match.empty:
                row = match.iloc[0]
                gol_tot = row['FTHG'] + row['FTAG']
                
                vinta = False
                if s['mercato'] == 'Over 1.5' and gol_tot > 1.5:
                    vinta = True
                elif s['mercato'] == 'Over 2.5' and gol_tot > 2.5:
                    vinta = True
                
                s['stato'] = 'VINTA' if vinta else 'PERSA'
                s['risultato'] = f"{row['FTHG']}-{row['FTAG']}"
                aggiornamenti.append(f"{s['partita']}: {s['stato']} ({s['risultato']})")
        
        nuovi_segnali.append(s)
    
    return nuovi_segnali, aggiornamenti

def genera_report(segnali):
    """Crea le statistiche di rendimento"""
    chiusi = [s for s in segnali if s.get('stato') in ['VINTA', 'PERSA']]
    if not chiusi:
        return "📊 Nessun dato ancora chiuso."
    
    vinte = len([s for s in chiusi if s.get('stato') == 'VINTA'])
    perse = len([s for s in chiusi if s.get('stato') == 'PERSA'])
    tot = len(chiusi)
    wr = (vinte / tot) * 100
    roi = ((vinte - perse) / tot) * 100
    
    return f"📊 **REPORT BOT**\n✅ Vinte: {vinte}\n❌ Perse: {perse}\n🎯 WinRate: {wr:.1f}%\n💰 ROI: {roi:+.1f}%"

async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    
    # 1. Carica lo storico precedente
    segnali = carica_risultati()
    
    # 2. Scarica i dati più recenti dal web
    df = scarica_dati()
    if df is None:
        await bot.send_message(CHAT_ID, "❌ Errore download dati.")
        return
    
    # 3. Aggiorna i risultati delle partite passate
    segnali, aggiornamenti = aggiorna_risultati(segnali, df)
    
    if aggiornamenti:
        msg_agg = "🔄 **Risultati Aggiornati:**\n" + "\n".join(aggiornamenti)
        await bot.send_message(CHAT_ID, msg_agg)
        await bot.send_message(CHAT_ID, genera_report(segnali))
    
    # 4. Analizza le nuove partite
    nuovi = analizza_partite(df)
    
    if nuovi:
        p = nuovi[0]
        p['stato'] = 'IN_CORSO'
        p['risultato'] = '-'
        segnali.append(p)
        
        msg = f"🔥 **TOP PICK OGGI**\n⚽ {p['partita']}\n🏆 {p['lega']}\n🎯 {p['mercato']}\n📈 Prob: {p['probabilita']}\n⚡ Gol Att: {p['gol_attesi']}\n\n⚠️ *Gioca responsabilmente*"
        await bot.send_message(CHAT_ID, msg, parse_mode='Markdown')
    else:
        await bot.send_message(CHAT_ID, "ℹ️ Nessun segnale >80% oggi.")
    
    # 5. Salva tutto nel file JSON
    salva_risultati(segnali)

if __name__ == "__main__":
    asyncio.run(main())
