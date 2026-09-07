"""
Core Monte Carlo simulation engine for fantasy football draft optimization
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json
from src.player import Player, PlayerPool
from src.injury_model import InjuryModel, WorkloadAnalyzer
from config import CONFIG

@dataclass
class TeamRoster:
    """Represents a drafted team roster"""
    team_id: int
    players: List[Player] = field(default_factory=list)
    season_points: float = 0.0
    points_list: List[float] = field(default_factory=list)  # Points for each simulation
    
    def add_player(self, player: Player) -> None:
        """Add player to roster"""
        self.players.append(player)
    
    def is_complete(self, league_config=None) -> bool:
        """Check if roster meets league requirements"""
        if league_config is None:
            league_config = CONFIG.league
        
        from config import ROSTER_REQUIREMENTS
        position_counts = {}
        
        for player in self.players:
            position_counts[player.position] = position_counts.get(player.position, 0) + 1
        
        for position, (min_req, max_req) in ROSTER_REQUIREMENTS.items():
            if position == 'FLEX':
                continue
            count = position_counts.get(position, 0)
            if count < min_req or count > max_req:
                return False
        
        return len(self.players) == league_config.num_rostered_players
    
    def calculate_season_points(self, injury_schedule: Dict, sim_index: int) -> float:
        """Calculate total season points accounting for injuries"""
        total_points = 0.0
        
        for player in self.players:
            if player.player_id in injury_schedule:
                is_injured, week_injured, weeks_missed = injury_schedule[player.player_id]
                
                if is_injured:
                    # Player misses games
                    games_played = 17 - weeks_missed
                    points = player.points_per_game * games_played
                else:
                    points = player.season_points
            else:
                points = player.season_points
            
            total_points += points
        
        return total_points
    
    def get_position_breakdown(self) -> Dict[str, float]:
        """Get total points by position"""
        breakdown = {}
        for player in self.players:
            breakdown[player.position] = breakdown.get(player.position, 0.0) + player.season_points
        return breakdown


@dataclass
class SimulationResult:
    """Results from a single simulation iteration"""
    sim_index: int
    lineup: List[Player]
    season_points: float
    points_by_position: Dict[str, float]
    injured_players: List[Tuple[str, int, int]]  # (player_name, week_injured, weeks_missed)
    team_ranking: int = -1


class DraftSimulator:
    """
    Monte Carlo simulator for fantasy football draft optimization
    
    Runs multiple simulations of:
    1. Draft (simulating other teams' picks)
    2. Season (accounting for injuries)
    3. Calculates optimal lineups
    """
    
    def __init__(self, league_config=None, sim_config=None):
        self.league_config = league_config or CONFIG.league
        self.sim_config = sim_config or CONFIG.simulation
        self.injury_model = InjuryModel(sim_config)
        self.workload_analyzer = WorkloadAnalyzer()
        self.rng = np.random.RandomState()
        
        self.simulation_results = []
        self.lineup_scores = []
        self.injury_log = []
    
    def run_simulations(self, player_pool: PlayerPool, num_simulations: int = None) -> Dict:
        """
        Run full Monte Carlo simulations
        
        Returns:
            Dict with results, statistics, and recommendations
        """
        num_sims = num_simulations or self.sim_config.num_simulations
        
        print(f"Running {num_sims:,} fantasy football simulations...")
        print(f"League: {self.league_config.num_teams} teams, PPR, snake draft, position {self.league_config.draft_position}")
        
        self.simulation_results = []
        self.lineup_scores = np.zeros(num_sims)
        
        for sim_idx in range(num_sims):
            if (sim_idx + 1) % 100000 == 0:
                print(f"  Completed {sim_idx + 1:,} simulations...")
            
            # Generate injury schedule for this simulation
            injury_schedule = self._generate_injury_schedule(player_pool)
            
            # Simulate draft picks (your team gets 10th pick)
            your_roster = self._simulate_draft(player_pool, injury_schedule)
            
            # Calculate season points with injuries factored in
            season_points = your_roster.calculate_season_points(injury_schedule, sim_idx)
            self.lineup_scores[sim_idx] = season_points
            
            # Store results
            result = SimulationResult(
                sim_index=sim_idx,
                lineup=your_roster.players,
                season_points=season_points,
                points_by_position=your_roster.get_position_breakdown(),
                injured_players=[]
            )
            self.simulation_results.append(result)
        
        print(f"✓ Completed all {num_sims:,} simulations")
        
        # Calculate statistics
        stats = self._calculate_statistics()
        
        return {
            'statistics': stats,
            'results': self.simulation_results,
            'lineup_scores': self.lineup_scores,
            'recommendations': self._generate_recommendations(player_pool),
            'injury_analysis': self._analyze_injuries()
        }
    
    def _generate_injury_schedule(self, player_pool: PlayerPool) -> Dict:
        """
        Generate injury schedule for all players in this simulation
        
        Returns:
            Dict of {player_id: (is_injured, week_injured, weeks_missed)}
        """
        injury_schedule = {}
        
        for player in player_pool:
            injury_prob = self.injury_model.calculate_injury_probability(player)
            is_injured, week_injured, weeks_missed = self.injury_model.simulate_injury_week(injury_prob)
            
            if is_injured:
                injury_schedule[player.player_id] = (is_injured, week_injured, weeks_missed)
        
        return injury_schedule
    
    def _simulate_draft(self, player_pool: PlayerPool, injury_schedule: Dict) -> TeamRoster:
        """
        Simulate an entire draft from position 10 (snake, 10-team league)
        
        Returns:
            Your team's roster
        """
        your_team_id = self.league_config.draft_position
        available_players = list(player_pool)
        drafted_ids = set()
        
        team_rosters = {i: TeamRoster(team_id=i) for i in range(1, self.league_config.num_teams + 1)}
        
        round_num = 1
        picks_made = 0
        total_picks_needed = self.league_config.num_teams * self.league_config.num_rostered_players
        
        while picks_made < total_picks_needed:
            # Determine pick order for this round (snake draft)
            if round_num % 2 == 1:
                # Odd rounds: 1-10
                pick_order = list(range(1, self.league_config.num_teams + 1))
            else:
                # Even rounds: 10-1 (reversed)
                pick_order = list(range(self.league_config.num_teams, 0, -1))
            
            for team_id in pick_order:
                if picks_made >= total_picks_needed:
                    break
                
                # Get available players
                available = [p for p in available_players if p.player_id not in drafted_ids]
                
                if not available:
                    break
                
                if team_id == your_team_id:
                    # YOUR PICK - use smart strategy
                    picked_player = self._pick_for_your_team(available, team_rosters[team_id], injury_schedule)
                else:
                    # Other teams pick (simulated with ADP bias)
                    picked_player = self._pick_for_cpu_team(available, team_rosters[team_id])
                
                if picked_player:
                    team_rosters[team_id].add_player(picked_player)
                    drafted_ids.add(picked_player.player_id)
                    picks_made += 1
            
            round_num += 1
        
        return team_rosters[your_team_id]
    
    def _pick_for_your_team(self, available: List[Player], your_roster: TeamRoster, injury_schedule: Dict) -> Optional[Player]:
        """
        Make optimal pick for your team using injury analysis and workload data
        """
        from config import ROSTER_REQUIREMENTS, POSITIONS_BY_SCARCITY
        
        # Get roster needs
        position_counts = {}
        for player in your_roster.players:
            position_counts[player.position] = position_counts.get(player.position, 0) + 1
        
        # Identify positions we need
        needed_positions = []
        for position, (min_req, max_req) in ROSTER_REQUIREMENTS.items():
            if position == 'FLEX':
                continue
            count = position_counts.get(position, 0)
            if count < min_req:
                needed_positions.append(position)
        
        # Score available players
        best_player = None
        best_score = -999
        
        for player in available[:50]:  # Only consider top 50 available
            # Filter by position need
            if len(needed_positions) > 0 and player.position not in needed_positions:
                if len(your_roster.players) < self.league_config.num_rostered_players * 0.7:
                    continue  # Early draft, stick to needs
            
            # Calculate value score
            value_score = self._calculate_player_value(player, injury_schedule, your_roster)
            
            if value_score > best_score:
                best_score = value_score
                best_player = player
        
        return best_player or available[0]
    
    def _pick_for_cpu_team(self, available: List[Player], cpu_roster: TeamRoster) -> Optional[Player]:
        """
        Simulate CPU team pick (biased towards ADP, fills roster needs)
        """
        # Filter by team needs
        from config import ROSTER_REQUIREMENTS
        
        position_counts = {}
        for player in cpu_roster.players:
            position_counts[player.position] = position_counts.get(player.position, 0) + 1
        
        # Calculate priority positions
        needed = []
        for position, (min_req, max_req) in ROSTER_REQUIREMENTS.items():
            if position == 'FLEX':
                continue
            count = position_counts.get(position, 0)
            if count < min_req:
                needed.append(position)
        
        # Filter to best available in needed positions (if any)
        candidates = available
        if needed:
            candidates = [p for p in available if p.position in needed][:10]
        else:
            candidates = available[:10]
        
        # Pick highest ADP from candidates
        return min(candidates, key=lambda p: p.adp) if candidates else None
    
    def _calculate_player_value(self, player: Player, injury_schedule: Dict, your_roster: TeamRoster) -> float:
        """
        Calculate value score for a player considering:
        - Injury risk
        - Projected points
        - Position scarcity
        - Workload stability
        """
        # Base value from projected points
        value = player.projected_points
        
        # Injury risk penalty
        injury_prob = self.injury_model.calculate_injury_probability(player)
        value -= injury_prob * 50  # Penalize high injury risk
        
        # Position scarcity bonus (RB and WR are scarce)
        if player.position == 'RB':
            value += 20
        elif player.position == 'WR':
            value += 15
        
        # Workload stability bonus
        if player.position == 'RB' and player.carry_share > 0.25:
            value += 10
        elif player.position == 'WR' and player.target_share > 0.20:
            value += 5
        
        # Bye week consideration (later bye is better)
        value -= (17 - player.bye_week) * 2
        
        # Diminishing returns if we already have that position
        position_count = sum(1 for p in your_roster.players if p.position == player.position)
        value -= position_count * 5
        
        return value
    
    def _calculate_statistics(self) -> Dict:
        """Calculate statistics from simulations"""
        scores = self.lineup_scores
        
        return {
            'mean_points': float(np.mean(scores)),
            'median_points': float(np.median(scores)),
            'std_dev': float(np.std(scores)),
            'min_points': float(np.min(scores)),
            'max_points': float(np.max(scores)),
            'percentile_1': float(np.percentile(scores, 1)),
            'percentile_25': float(np.percentile(scores, 25)),
            'percentile_50': float(np.percentile(scores, 50)),
            'percentile_75': float(np.percentile(scores, 75)),
            'percentile_99': float(np.percentile(scores, 99)),
            'win_probability': float(np.sum(scores > np.mean(scores)) / len(scores))
        }
    
    def _generate_recommendations(self, player_pool: PlayerPool) -> Dict:
        """Generate draft recommendations by round"""
        high_risk_rbs = self.injury_model.identify_high_risk_players(player_pool, position='RB', threshold=0.12)
        backup_opps = self.injury_model.identify_backup_opportunities(player_pool, position='RB')
        heavy_usage_teams = self.workload_analyzer.identify_heavy_usage_teams(player_pool, position='RB')
        
        return {
            'high_risk_rbs': high_risk_rbs[:10],
            'backup_opportunities': backup_opps[:10],
            'heavy_usage_teams': heavy_usage_teams,
            'strategy': self._generate_draft_strategy()
        }
    
    def _generate_draft_strategy(self) -> List[Dict]:
        """Generate round-by-round draft strategy"""
        return [
            {
                'round': 1,
                'pick': '10th overall',
                'strategy': 'Target elite RB or WR if available. Prioritize talent and floor.',
                'avoid': 'Injury-prone players with questionable backup value.'
            },
            {
                'round': 2,
                'pick': '11th overall',
                'strategy': 'Fill opposite position from Round 1. Target tier-break value.',
                'avoid': 'Reaching for backup RBs. Wait for opportunity.'
            },
            {
                'round': 3,
                'strategy': 'Target high-upside RB/WR stack. Look for secondary ball handlers.',
                'key_targets': 'Backup RBs on heavy-usage teams, target upside in WR corps'
            },
            {
                'round': 4,
                'strategy': 'Consider TE if elite options remain, or continue value WR/RB strategy.',
                'key_insight': 'RB scarcity means waiting on TE is often worth it'
            },
            {
                'round': 5,
                'strategy': 'Identify backup RBs with highest opportunity scores.',
                'key_insight': 'Stashing handcuff RBs on teams with injured starters is valuable'
            }
        ]
    
    def _analyze_injuries(self) -> Dict:
        """Analyze injury impact across simulations"""
        total_injuries = len(self.injury_log)
        avg_per_sim = total_injuries / len(self.simulation_results) if self.simulation_results else 0
        
        return {
            'total_injuries_across_sims': total_injuries,
            'avg_injuries_per_sim': avg_per_sim,
            'injury_impact_on_score': 'TBD',  # Calculate from results
        }
