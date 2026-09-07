"""
Unit tests for fantasy football simulator
"""

import unittest
import numpy as np
from src.player import Player, PlayerPool
from src.injury_model import InjuryModel
from src.simulator import DraftSimulator, TeamRoster
from config import CONFIG


class TestPlayer(unittest.TestCase):
    """Test Player class"""
    
    def setUp(self):
        self.player = Player(
            player_id="rb_001",
            name="Test RB",
            position="RB",
            nfl_team="KC",
            age=26,
            adp=10.0,
            bye_week=10,
            projected_points=200,
            floor=150,
            ceiling=250,
            carry_share=0.25,
            snap_count_pct=0.65
        )
    
    def test_player_creation(self):
        """Test player object creation"""
        self.assertEqual(self.player.name, "Test RB")
        self.assertEqual(self.player.position, "RB")
        self.assertEqual(self.player.projected_points, 200)
    
    def test_player_points_per_game(self):
        """Test points per game calculation"""
        self.assertAlmostEqual(self.player.points_per_game, 200/17, places=1)


class TestPlayerPool(unittest.TestCase):
    """Test PlayerPool class"""
    
    def setUp(self):
        self.pool = PlayerPool()
        self.player1 = Player("rb_001", "RB1", "RB", "KC", 26, 5.0, 10, 200, 150, 250)
        self.player2 = Player("rb_002", "RB2", "RB", "LAC", 27, 10.0, 5, 180, 140, 230)
        self.pool.add_player(self.player1)
        self.pool.add_player(self.player2)
    
    def test_pool_length(self):
        """Test pool has correct number of players"""
        self.assertEqual(len(self.pool), 2)
    
    def test_get_by_position(self):
        """Test filtering by position"""
        rbs = self.pool.get_by_position("RB")
        self.assertEqual(len(rbs), 2)
    
    def test_get_by_adp(self):
        """Test ADP ordering"""
        rbs = self.pool.get_by_position("RB")
        self.assertLess(rbs[0].adp, rbs[1].adp)


class TestInjuryModel(unittest.TestCase):
    """Test injury risk modeling"""
    
    def setUp(self):
        self.injury_model = InjuryModel()
        self.rb_high_usage = Player(
            player_id="rb_001",
            name="Heavy Usage RB",
            position="RB",
            nfl_team="KC",
            age=28,
            adp=5.0,
            bye_week=10,
            projected_points=200,
            floor=150,
            ceiling=250,
            carry_share=0.35,
            snap_count_pct=0.75,
            injury_history=[{"year": 2023, "games_missed": 2}],
            injury_prone=True
        )
    
    def test_injury_probability_calculation(self):
        """Test injury probability is calculated"""
        prob = self.injury_model.calculate_injury_probability(self.rb_high_usage)
        self.assertGreater(prob, 0)
        self.assertLess(prob, 1)
    
    def test_high_usage_increases_injury_risk(self):
        """Test that high usage RBs have higher injury risk"""
        rb_low_usage = Player(
            player_id="rb_002",
            name="Low Usage RB",
            position="RB",
            nfl_team="LAC",
            age=26,
            adp=50.0,
            bye_week=5,
            projected_points=100,
            floor=80,
            ceiling=130,
            carry_share=0.15,
            snap_count_pct=0.40
        )
        
        high_risk = self.injury_model.calculate_injury_probability(self.rb_high_usage)
        low_risk = self.injury_model.calculate_injury_probability(rb_low_usage)
        
        self.assertGreater(high_risk, low_risk)


class TestTeamRoster(unittest.TestCase):
    """Test team roster management"""
    
    def setUp(self):
        self.roster = TeamRoster(team_id=1)
        self.player = Player("qb_001", "Test QB", "QB", "KC", 28, 2.0, 11, 320, 280, 380)
    
    def test_add_player(self):
        """Test adding players to roster"""
        self.roster.add_player(self.player)
        self.assertEqual(len(self.roster.players), 1)
    
    def test_position_breakdown(self):
        """Test position breakdown calculation"""
        self.roster.add_player(self.player)
        breakdown = self.roster.get_position_breakdown()
        self.assertEqual(breakdown['QB'], 320)


class TestDraftSimulator(unittest.TestCase):
    """Test draft simulator"""
    
    def setUp(self):
        self.simulator = DraftSimulator()
        self.player_pool = PlayerPool()
        
        # Add some test players
        for i in range(50):
            player = Player(
                player_id=f"p_{i}",
                name=f"Player {i}",
                position=["QB", "RB", "WR", "TE"][i % 4],
                nfl_team="KC",
                age=25 + (i % 10),
                adp=float(i + 1),
                bye_week=10,
                projected_points=200 - (i * 2),
                floor=150 - (i * 2),
                ceiling=250 - (i * 2)
            )
            self.player_pool.add_player(player)
    
    def test_simulator_initialization(self):
        """Test simulator initializes correctly"""
        self.assertIsNotNone(self.simulator)
        self.assertEqual(self.simulator.league_config.draft_position, 10)


if __name__ == '__main__':
    unittest.main()
