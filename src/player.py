"""
Player class and data loading utilities
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json

@dataclass
class Player:
    """Represents a fantasy football player"""
    player_id: str
    name: str
    position: str
    nfl_team: str
    age: int
    adp: float  # Average Draft Position
    bye_week: int
    projected_points: float  # Season total
    floor: float
    ceiling: float
    
    # Injury history
    injury_history: List[Dict] = field(default_factory=list)
    injury_prone: bool = False
    games_played_history: List[int] = field(default_factory=list)
    
    # Team workload metrics
    snap_count_pct: float = 0.0
    target_share: float = 0.0  # For WR/TE
    carry_share: float = 0.0   # For RB
    red_zone_touches_pct: float = 0.0
    
    # Derived metrics
    injury_risk: float = 0.0
    season_points: float = 0.0
    points_per_game: float = 0.0
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if len(self.games_played_history) > 0:
            avg_games_played = sum(self.games_played_history) / len(self.games_played_history)
            self.points_per_game = self.projected_points / max(avg_games_played, 1)
        else:
            self.points_per_game = self.projected_points / 17  # Assume full season
        
        self.season_points = self.projected_points
    
    def __repr__(self) -> str:
        return f"{self.name} ({self.position}, {self.nfl_team}) - ADP: {self.adp:.1f}"
    
    def __hash__(self) -> int:
        return hash(self.player_id)
    
    def __eq__(self, other) -> bool:
        return self.player_id == other.player_id
    
    def get_position_rank(self, all_players: List['Player']) -> int:
        """Get rank within position"""
        same_pos = [p for p in all_players if p.position == self.position]
        same_pos.sort(key=lambda p: p.adp)
        return next((i for i, p in enumerate(same_pos) if p.player_id == self.player_id), -1) + 1
    
    def get_tier(self, percentile: float = 0.75) -> str:
        """Classify player into tier (Tier 1, 2, 3, 4, 5)"""
        if self.adp <= 12:
            return "Tier 1"
        elif self.adp <= 36:
            return "Tier 2"
        elif self.adp <= 72:
            return "Tier 3"
        elif self.adp <= 108:
            return "Tier 4"
        else:
            return "Tier 5"


@dataclass
class PlayerPool:
    """Manages a collection of players"""
    players: Dict[str, Player] = field(default_factory=dict)
    
    def add_player(self, player: Player) -> None:
        """Add player to pool"""
        self.players[player.player_id] = player
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID"""
        return self.players.get(player_id)
    
    def get_by_position(self, position: str) -> List[Player]:
        """Get all players of a position"""
        return sorted(
            [p for p in self.players.values() if p.position == position],
            key=lambda p: p.adp
        )
    
    def get_by_team(self, nfl_team: str) -> List[Player]:
        """Get all players on an NFL team"""
        return [p for p in self.players.values() if p.nfl_team == nfl_team]
    
    def get_available(self, drafted_ids: set) -> List[Player]:
        """Get all available (undrafted) players"""
        return [p for p in self.players.values() if p.player_id not in drafted_ids]
    
    def get_top_n(self, n: int, position: Optional[str] = None) -> List[Player]:
        """Get top N players by ADP"""
        pool = self.get_by_position(position) if position else sorted(
            self.players.values(), key=lambda p: p.adp
        )
        return pool[:n]
    
    def __len__(self) -> int:
        return len(self.players)
    
    def __iter__(self):
        return iter(self.players.values())


class PlayerDataLoader:
    """Load player data from various sources"""
    
    @staticmethod
    def load_from_csv(filepath: str) -> PlayerPool:
        """Load players from CSV file"""
        import csv
        pool = PlayerPool()
        
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    player = Player(
                        player_id=row['player_id'],
                        name=row['name'],
                        position=row['position'],
                        nfl_team=row['nfl_team'],
                        age=int(row.get('age', 25)),
                        adp=float(row.get('adp', 300)),
                        bye_week=int(row.get('bye_week', 0)),
                        projected_points=float(row.get('projected_points', 0)),
                        floor=float(row.get('floor', 0)),
                        ceiling=float(row.get('ceiling', 0)),
                        snap_count_pct=float(row.get('snap_count_pct', 0)),
                        target_share=float(row.get('target_share', 0)),
                        carry_share=float(row.get('carry_share', 0)),
                        red_zone_touches_pct=float(row.get('red_zone_touches_pct', 0)),
                    )
                    pool.add_player(player)
        except FileNotFoundError:
            print(f"Warning: {filepath} not found. Creating empty pool.")
        
        return pool
    
    @staticmethod
    def load_from_json(filepath: str) -> PlayerPool:
        """Load players from JSON file"""
        pool = PlayerPool()
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                for player_data in data:
                    player = Player(**player_data)
                    pool.add_player(player)
        except FileNotFoundError:
            print(f"Warning: {filepath} not found. Creating empty pool.")
        
        return pool
    
    @staticmethod
    def create_sample_pool() -> PlayerPool:
        """Create a sample player pool for testing"""
        pool = PlayerPool()
        
        # Sample QB
        pool.add_player(Player(
            player_id="qb_001",
            name="Patrick Mahomes",
            position="QB",
            nfl_team="KC",
            age=28,
            adp=1.5,
            bye_week=11,
            projected_points=320,
            floor=280,
            ceiling=380,
            injury_history=[],
            injury_prone=False
        ))
        
        # Sample RBs
        pool.add_player(Player(
            player_id="rb_001",
            name="Christian McCaffrey",
            position="RB",
            nfl_team="SF",
            age=28,
            adp=2.1,
            bye_week=6,
            projected_points=290,
            floor=240,
            ceiling=350,
            injury_history=[{"year": 2024, "games_missed": 4}],
            injury_prone=True,
            carry_share=0.28,
            snap_count_pct=0.72
        ))
        
        pool.add_player(Player(
            player_id="rb_002",
            name="Josh Jacobs",
            position="RB",
            nfl_team="LV",
            age=26,
            adp=3.2,
            bye_week=10,
            projected_points=270,
            floor=220,
            ceiling=320,
            carry_share=0.24,
            snap_count_pct=0.65
        ))
        
        # Add more sample players as needed
        return pool
