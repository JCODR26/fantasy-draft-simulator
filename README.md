# Fantasy Football Draft Simulator

A Monte Carlo simulation engine for optimizing fantasy football draft strategies with injury risk modeling, team workload analysis, and PPR scoring optimization.

## 🎯 Features

- **1M+ Monte Carlo Simulations** - Run comprehensive season-long projections
- **Injury Risk Modeling** - Historical injury data and probability calculations
- **Team Workload Analysis** - Detect heavy RB/WR usage and injury correlation
- **PPR Optimization** - Full PPR scoring with custom league settings
- **Draft Position Analysis** - Optimize for 10-team snake drafts (or any configuration)
- **Player Projections** - Consensus-based ADP and season-long point projections

## ⚡ Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with sample data (no CSV needed)
python main.py --sample

# Run for your league (10th pick, 10 teams, PPR, 1M simulations)
python main.py --draft-position 10 --teams 10 --simulations 1000000
```

## 📊 Results

Results are automatically saved to `output/`:
- `draft_report.html` - Visual report with statistics
- `simulation_results.json` - Complete simulation data

View the HTML report in your browser to see:
- Expected season points (mean, median, std dev)
- Percentile outcomes (1st, 25th, 50th, 75th, 99th)
- High-risk RBs to avoid or handcuff
- Backup RB opportunities with high upside
- Heavy usage teams to monitor
- Round-by-round draft strategy

## 🏗️ Project Structure

```
fantasy-draft-simulator/
├── src/
│   ├── simulator.py         # Core Monte Carlo engine
│   ├── injury_model.py      # Injury risk calculations
│   ├── player.py            # Player class and utilities
│   └── ppr_optimizer.py     # PPR scoring
├── data/
│   └── players.csv          # Player data
├── config.py                # Configuration
├── main.py                  # Entry point
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## 🔧 How It Works

1. **Load Players** - Reads player projections, ADP, and workload metrics
2. **Calculate Injury Risk** - Scores each player on injury probability
   - Base rates by position (RB: 12%, WR: 8%, etc.)
   - Age factor (+2% per year over 28)
   - Injury history (+5% per previous injury)
   - Heavy usage penalty (+10% if snap count >25%)
3. **Run 1M Simulations** - Each iteration:
   - Randomly injures players based on probabilities
   - Adjusts season projections for missed games
   - Calculates team score
4. **Analyze Results** - Generates statistics across all simulations
5. **Generate Recommendations** - High-risk players, backup opportunities, strategy

## 📈 Key Outputs

### Expected Points
- **Mean** - Average expected season points
- **Median** - Middle outcome (50th percentile)
- **Std Dev** - Consistency measure
- **Percentiles** - Range from worst (1st) to best (99th)

### High-Risk Players
RBs with >12% injury probability. Recommendations:
- Avoid them entirely, OR
- Draft them + their backup (handcuff strategy)

### Backup Opportunities
Backup RBs with high upside if starter gets injured. Ranked by "opportunity score":
- High opportunity score = more likely to get carries if starter injured
- Lower ADP = discount price for high upside

### Heavy Usage Teams
Teams where one RB has dominant workload (>25% snap usage). These are injury risks:
- Monitor all season
- Consider handcuffing the backup

## ⚙️ Configuration

Edit `config.py` to customize:
- League settings (teams, PPR, snake draft)
- Draft position (1-10)
- Number of simulations
- Injury risk thresholds
- PPR scoring settings

## 🎲 Command Line Options

```
Usage: python main.py [OPTIONS]

Options:
  -p, --draft-position INT      Your pick (1-10 for 10-team) [default: 10]
  -t, --teams INT               Number of teams [default: 10]
  --ppr                         Use PPR scoring [default: true]
  -s, --simulations INT         Number of sims [default: 1,000,000]
  --player-data FILE            Player CSV path [default: data/players.csv]
  -o, --output DIR              Output directory [default: output]
  -v, --verbose                 Verbose output
  --sample                      Use sample player pool
```

## 📋 Injury Risk Model

### Base Rates by Position
- QB: 3%
- RB: 12% (highest risk)
- WR: 8%
- TE: 5%
- K: 2%
- DST: 4%

### Risk Multipliers
- Age: +2% per year over 28
- Previous injury: +5% per prior injury
- Heavy RB usage (>25%): +10%
- Heavy WR usage (>20%): +8%

### Recovery Times
- QB: 4 weeks
- RB: 3 weeks
- WR: 2 weeks
- TE: 2 weeks

## 💡 Draft Strategy Tips

1. **Early Rounds (1-3)**
   - Target elite talent and position scarcity
   - Avoid high-risk players without backup value
   - Prioritize RB and WR (most scarce)

2. **Mid Rounds (4-7)**
   - Balance value with tier drops
   - Target backup RBs on high-risk teams
   - Consider stacking (QB + pass catchers)

3. **Late Rounds (8-10)**
   - High-ceiling upside plays
   - Handcuff high-risk starters
   - Target breakout candidates

## 🧪 Testing

```bash
pytest tests/
```

## 📝 Example Output

```
Expected Season Points (PPR):
  • Mean:              1450.5
  • Median:            1448.2
  • Std Dev:             125.3

Percentile Outcomes:
  • 1st percentile:    1150.2 pts (floor)
  • 99th percentile:   1750.8 pts (ceiling)
  • Win Probability:    52.3%

⚠ HIGH INJURY RISK RBs:
  1. Christian McCaffrey    18.2%
  2. Jonathan Taylor        16.5%
  3. Derrick Henry          15.8%

✓ BACKUP RB OPPORTUNITIES:
  1. Jeff Wilson Jr.        ADP: 45.1  Upside: 85pts
  2. D'Onta Foreman         ADP: 52.3  Upside: 72pts

🚨 HEAVY USAGE TEAMS:
  1. SF: Christian McCaffrey  72.0% usage
  2. IND: Jonathan Taylor     68.0% usage
```

## 📚 Further Reading

- [FantasyPros ADP Data](https://www.fantasypros.com/nfl/adp/)
- [NFL Official Stats](https://www.nfl.com/stats/)
- [PPR Scoring Guide](https://www.fantasypros.com/nfl/help/scoring.php)

## 📄 License

MIT License

## ⚖️ Disclaimer

For entertainment and educational purposes. Fantasy football involves luck and uncertainty. Use as one input in your decision-making process.

---

**Ready to draft?** Run `python main.py --sample` to get started!
