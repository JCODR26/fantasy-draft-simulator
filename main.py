"""
Main entry point for fantasy football draft simulator
"""

import argparse
import json
import sys
from datetime import datetime
import numpy as np
from src.simulator import DraftSimulator
from src.player import PlayerDataLoader, PlayerPool
from src.injury_model import InjuryModel, WorkloadAnalyzer
from config import CONFIG, get_default_league_config, get_default_simulation_config


def setup_argparse():
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description='Fantasy Football Draft Simulator - Monte Carlo Optimization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --draft-position 10 --teams 10 --ppr --simulations 1000000
  python main.py --draft-position 5 --teams 12 --ppr --simulations 500000
        """
    )
    
    parser.add_argument(
        '--draft-position', '-p',
        type=int,
        default=10,
        help='Your draft position (1-10 for 10-team league) [default: 10]'
    )
    
    parser.add_argument(
        '--teams', '-t',
        type=int,
        default=10,
        help='Number of teams in league [default: 10]'
    )
    
    parser.add_argument(
        '--ppr',
        action='store_true',
        default=True,
        help='Use PPR scoring (default: true)'
    )
    
    parser.add_argument(
        '--simulations', '-s',
        type=int,
        default=1000000,
        help='Number of simulations to run [default: 1,000,000]'
    )
    
    parser.add_argument(
        '--player-data',
        type=str,
        default='data/players.csv',
        help='Path to player data CSV file [default: data/players.csv]'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='output',
        help='Output directory for results [default: output]'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Use sample player pool for testing'
    )
    
    return parser


def load_player_data(args):
    """Load player data from file or create sample"""
    if args.sample:
        print("Loading sample player pool...")
        return PlayerDataLoader.create_sample_pool()
    
    print(f"Loading player data from {args.player_data}...")
    pool = PlayerDataLoader.load_from_csv(args.player_data)
    
    if len(pool) == 0:
        print("⚠ No player data found. Using sample pool.")
        return PlayerDataLoader.create_sample_pool()
    
    print(f"✓ Loaded {len(pool)} players")
    return pool


def main():
    """Main entry point"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("FANTASY FOOTBALL DRAFT SIMULATOR - Monte Carlo Analysis")
    print("="*70 + "\n")
    
    # Configure league settings
    CONFIG.update_league(
        draft_position=args.draft_position,
        num_teams=args.teams,
        ppr_scoring=args.ppr
    )
    
    # Configure simulation settings
    CONFIG.update_simulation(
        num_simulations=args.simulations
    )
    
    CONFIG.update_output(
        output_dir=args.output,
        verbose=args.verbose
    )
    
    # Print configuration
    print(f"League Configuration:")
    print(f"  • Teams: {CONFIG.league.num_teams}")
    print(f"  • Your Draft Position: #{CONFIG.league.draft_position}")
    print(f"  • Scoring: {'PPR' if CONFIG.league.ppr_scoring else 'Standard'}")
    print(f"  • Snake Draft: {CONFIG.league.snake_draft}")
    print(f"\nSimulation Configuration:")
    print(f"  • Simulations: {CONFIG.simulation.num_simulations:,}")
    print(f"  • Weeks: {CONFIG.simulation.num_weeks}")
    print(f"\n")
    
    # Load player data
    player_pool = load_player_data(args)
    
    if len(player_pool) == 0:
        print("ERROR: Could not load player data. Exiting.")
        sys.exit(1)
    
    # Run simulations
    simulator = DraftSimulator(
        league_config=CONFIG.league,
        sim_config=CONFIG.simulation
    )
    
    print(f"Starting {CONFIG.simulation.num_simulations:,} simulations...\n")
    start_time = datetime.now()
    
    results = simulator.run_simulations(player_pool, CONFIG.simulation.num_simulations)
    
    elapsed_time = (datetime.now() - start_time).total_seconds()
    print(f"\n✓ Simulations completed in {elapsed_time:.2f} seconds")
    print(f"  ({CONFIG.simulation.num_simulations / elapsed_time:,.0f} simulations/sec)\n")
    
    # Print statistics
    stats = results['statistics']
    print("="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    print(f"\nExpected Season Points (PPR):")
    print(f"  • Mean:              {stats['mean_points']:>7.1f}")
    print(f"  • Median:            {stats['median_points']:>7.1f}")
    print(f"  • Std Dev:           {stats['std_dev']:>7.1f}")
    print(f"\nPercentile Outcomes:")
    print(f"  • 1st percentile:    {stats['percentile_1']:>7.1f} pts (floor)")
    print(f"  • 25th percentile:   {stats['percentile_25']:>7.1f} pts")
    print(f"  • 50th percentile:   {stats['percentile_50']:>7.1f} pts (median)")
    print(f"  • 75th percentile:   {stats['percentile_75']:>7.1f} pts")
    print(f"  • 99th percentile:   {stats['percentile_99']:>7.1f} pts (ceiling)")
    print(f"\nRange: {stats['min_points']:.1f} - {stats['max_points']:.1f} pts")
    print(f"Win Probability (beat median): {stats['win_probability']*100:.1f}%")
    
    # Print recommendations
    print("\n" + "="*70)
    print("DRAFT RECOMMENDATIONS")
    print("="*70)
    
    recs = results['recommendations']
    
    print("\n⚠ HIGH INJURY RISK RBs (Avoid or stack backup):")
    for i, (name, risk) in enumerate(recs['high_risk_rbs'][:5], 1):
        print(f"  {i}. {name:<25} Injury Risk: {risk*100:>5.1f}%")
    
    print("\n✓ BACKUP RB OPPORTUNITIES (High upside, low draft capital):")
    for i, opp in enumerate(recs['backup_opportunities'][:5], 1):
        print(f"  {i}. {opp['backup']:<25} ADP: {opp['backup_adp']:>6.1f}  " +
              f"Opp Score: {opp['opportunity_score']:>5.2f}  Upside: {opp['upside_points']:.0f}pts")
    
    print("\n🚨 HEAVY USAGE TEAMS (Monitor RB workload):")
    for i, team in enumerate(recs['heavy_usage_teams'][:5], 1):
        print(f"  {i}. {team['team']}: {team['primary_player']:<20} " +
              f"Usage: {team['usage_pct']*100:>5.1f}%")
    
    print("\n" + "="*70)
    print("ROUND-BY-ROUND STRATEGY")
    print("="*70)
    
    for strategy in recs['strategy'][:5]:
        round_num = strategy.get('round', 'N/A')
        print(f"\nRound {round_num}:")
        print(f"  Strategy: {strategy['strategy']}")
        if 'avoid' in strategy:
            print(f"  ⚠ Avoid: {strategy['avoid']}")
        if 'key_insight' in strategy:
            print(f"  💡 Insight: {strategy['key_insight']}")
    
    # Save detailed results to JSON
    output_file = f"{args.output}/simulation_results.json"
    save_results(results, output_file)
    print(f"\n✓ Detailed results saved to {output_file}")
    
    # Generate HTML report
    html_file = f"{args.output}/draft_report.html"
    generate_html_report(results, stats, recs, html_file, CONFIG)
    print(f"✓ HTML report saved to {html_file}")
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print(f"\n1. Review the HTML report: {html_file}")
    print(f"2. Check high-risk RBs and backup opportunities")
    print(f"3. Follow the round-by-round draft strategy")
    print(f"4. Monitor team workload changes during season")
    print("\nGood luck with your draft!\n")


def save_results(results, output_file):
    """Save detailed results to JSON"""
    import os
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    
    # Convert numpy arrays to lists for JSON serialization
    exportable_results = {
        'statistics': results['statistics'],
        'recommendations': results['recommendations'],
        'injury_analysis': results['injury_analysis'],
        'lineup_scores': results['lineup_scores'].tolist() if isinstance(results['lineup_scores'], np.ndarray) else results['lineup_scores']
    }
    
    with open(output_file, 'w') as f:
        json.dump(exportable_results, f, indent=2)


def generate_html_report(results, stats, recs, output_file, config):
    """Generate HTML report"""
    import os
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fantasy Football Draft Simulation Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
            .header {{ background-color: #1f4788; color: white; padding: 20px; border-radius: 5px; }}
            .section {{ background-color: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .stat-box {{ display: inline-block; background-color: #e8f4f8; padding: 15px; margin: 10px; border-radius: 5px; }}
            .stat-value {{ font-size: 24px; font-weight: bold; color: #1f4788; }}
            .stat-label {{ font-size: 12px; color: #666; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #1f4788; color: white; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .warning {{ color: #d9534f; font-weight: bold; }}
            .success {{ color: #5cb85c; font-weight: bold; }}
            .info {{ background-color: #d9edf7; padding: 10px; border-left: 4px solid #31708f; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Fantasy Football Draft Simulator Report</h1>
            <p>Monte Carlo Analysis with {config.simulation.num_simulations:,} Simulations</p>
        </div>
        
        <div class="section">
            <h2>League Configuration</h2>
            <p>
                <strong>Teams:</strong> {config.league.num_teams} | 
                <strong>Your Position:</strong> #{config.league.draft_position} (Snake) | 
                <strong>Scoring:</strong> {'PPR' if config.league.ppr_scoring else 'Standard'}
            </p>
        </div>
        
        <div class="section">
            <h2>Expected Season Performance</h2>
            <div class="stat-box">
                <div class="stat-value">{stats['mean_points']:.1f}</div>
                <div class="stat-label">Mean Points</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats['median_points']:.1f}</div>
                <div class="stat-label">Median Points</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">±{stats['std_dev']:.1f}</div>
                <div class="stat-label">Std Deviation</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats['percentile_99']:.1f}</div>
                <div class="stat-label">99th Percentile (Ceiling)</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats['percentile_1']:.1f}</div>
                <div class="stat-label">1st Percentile (Floor)</div>
            </div>
        </div>
        
        <div class="section">
            <h2>High-Risk Running Backs</h2>
            <div class="info">⚠ These RBs have high injury probability. Consider avoiding or stacking their backup.</div>
            <table>
                <tr><th>Rank</th><th>Player</th><th>Injury Risk</th></tr>
    """
    
    for i, (name, risk) in enumerate(recs['high_risk_rbs'][:10], 1):
        html_content += f"<tr><td>{i}</td><td>{name}</td><td><span class='warning'>{risk*100:.1f}%</span></td></tr>"
    
    html_content += """
            </table>
        </div>
        
        <div class="section">
            <h2>Backup RB Opportunities</h2>
            <div class="info">✓ These backup RBs have high opportunity upside if starter gets injured.</div>
            <table>
                <tr><th>Backup</th><th>Team</th><th>ADP</th><th>Opportunity Score</th><th>Ceiling Upside</th></tr>
    """
    
    for opp in recs['backup_opportunities'][:10]:
        html_content += f"<tr><td>{opp['backup']}</td><td>{opp['team']}</td><td>{opp['backup_adp']:.1f}</td><td>{opp['opportunity_score']:.2f}</td><td>{opp['upside_points']:.0f}</td></tr>"
    
    html_content += """
            </table>
        </div>
        
        <div class="section">
            <h2>Heavy Usage Teams</h2>
            <div class="info">🚨 Monitor these RBs closely - high usage increases injury risk.</div>
            <table>
                <tr><th>Team</th><th>Primary RB</th><th>Usage %</th><th>Risk Level</th></tr>
    """
    
    for team in recs['heavy_usage_teams'][:10]:
        risk_level = "🔴 HIGH" if team['is_concerning'] else "🟡 MODERATE"
        html_content += f"<tr><td>{team['team']}</td><td>{team['primary_player']}</td><td>{team['usage_pct']*100:.1f}%</td><td>{risk_level}</td></tr>"
    
    html_content += """
            </table>
        </div>
        
        <div class="section">
            <h2>Report Generated</h2>
            <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>
    </body>
    </html>
    """
    
    with open(output_file, 'w') as f:
        f.write(html_content)


if __name__ == '__main__':
    main()
